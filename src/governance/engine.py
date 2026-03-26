import logging
from src.governance.enums import GovernanceModel, Decision

logger = logging.getLogger(__name__)

class GovernanceEngine:
    """
    Decides PR outcomes based on the selected Governance Model.
    """
    def __init__(self, model: GovernanceModel = GovernanceModel.CENTRALIZED):
        self.model = model

        # Configuration Parameters
        self.min_quorum = 3           # Minimum votes required (Decentralized)
        self.vote_threshold = 0.67    # Supermajority required (Decentralized)
        self.trust_threshold = 0.55   # Minimum trust score to merge (Hybrid)

        # Per-agent rejection tracker for escalating scrutiny
        # {agent_name: consecutive_rejections}
        self._agent_rejections: dict = {}
        # Pair-wise vote agreement tracker for colluder detection
        # {(agent_a, agent_b): [agree_count, total_count]}
        self._voter_pair_agreement: dict = {}

    def evaluate(self, peer_result, maintainer_review, author_reputation: float,
                 agent_name: str = "") -> Decision:
        """
        Evaluate a Pull Request based on the active model.
        Tracks per-agent rejection history for escalating scrutiny.
        """
        # Update pair-wise vote agreement for colluder detection
        self._track_voter_pairs(peer_result)

        # Escalating scrutiny: raise threshold if agent has prior rejections
        prior_rejections = self._agent_rejections.get(agent_name, 0)

        if self.model == GovernanceModel.CENTRALIZED:
            decision = self._evaluate_centralized(maintainer_review, prior_rejections)
        elif self.model == GovernanceModel.DECENTRALIZED:
            decision = self._evaluate_decentralized(peer_result, maintainer_review, prior_rejections)
        elif self.model == GovernanceModel.HYBRID:
            decision = self._evaluate_hybrid(peer_result, maintainer_review, author_reputation, prior_rejections)
        else:
            decision = Decision.PENDING

        # Update rejection counter
        if agent_name:
            if decision in (Decision.REJECT, Decision.BLOCK_AGENT):
                self._agent_rejections[agent_name] = prior_rejections + 1
                logger.info(f"  [Scrutiny] {agent_name} now has "
                            f"{self._agent_rejections[agent_name]} rejection(s) on record")
            elif decision == Decision.APPROVE:
                # Reset on successful approval (agent proving themselves)
                self._agent_rejections[agent_name] = max(0, prior_rejections - 1)

        return decision

    def _track_voter_pairs(self, peer_result):
        """
        Track whether pairs of reviewers always vote together.
        Flags potential colluders if agreement rate exceeds 95% over 3+ shared reviews.
        """
        reviews = [r for r in peer_result.peer_reviews if r.confidence > 0.0]
        for i in range(len(reviews)):
            for j in range(i + 1, len(reviews)):
                a, b = reviews[i].reviewer_name, reviews[j].reviewer_name
                pair = tuple(sorted([a, b]))
                if pair not in self._voter_pair_agreement:
                    self._voter_pair_agreement[pair] = [0, 0]
                agreed = reviews[i].is_safe == reviews[j].is_safe
                self._voter_pair_agreement[pair][1] += 1
                if agreed:
                    self._voter_pair_agreement[pair][0] += 1
                total = self._voter_pair_agreement[pair][1]
                agree_rate = self._voter_pair_agreement[pair][0] / total
                # Only alert when at least one reviewer is a known sybil voter
                # (benign pairs naturally agree on legitimate PRs — not collusion)
                pair_involves_sybil = any("[SYBIL]" in p for p in pair)
                if total >= 3 and agree_rate >= 0.95 and pair_involves_sybil:
                    logger.warning(
                        f"  [COLLUDER ALERT] {pair[0]} & {pair[1]} agree on "
                        f"{agree_rate:.0%} of {total} shared reviews — possible ring collusion"
                    )

    def _evaluate_centralized(self, maintainer_review, prior_rejections: int = 0) -> Decision:
        """
        Centralized: The Maintainer's word is law. Peer votes are ignored.
        """
        # Veto: static analysis found a CRITICAL pattern regardless of LLM state
        critical_issues = [i for i in maintainer_review.issues if i.severity == 'CRITICAL']
        if critical_issues:
            return Decision.BLOCK_AGENT

        # LLM unavailable — fall back to static analysis result
        if not maintainer_review.llm_available:
            logger.info("  [Centralized] Maintainer LLM unavailable — deciding on static analysis only")
            high_issues = [i for i in maintainer_review.issues if i.severity == 'HIGH']
            if high_issues:
                return Decision.REJECT
            return Decision.APPROVE

        # Escalating scrutiny: raise approval threshold for agents with prior rejections
        approve_threshold = 0.65 + min(prior_rejections * 0.05, 0.15)
        reject_threshold  = 0.45 - min(prior_rejections * 0.03, 0.10)

        if maintainer_review.trust_score >= approve_threshold:
            return Decision.APPROVE
        elif maintainer_review.trust_score < reject_threshold:
            return Decision.REJECT
        else:
            return Decision.PENDING

    def _evaluate_decentralized(self, peer_result, maintainer_review=None,
                                prior_rejections: int = 0) -> Decision:
        """
        Decentralized: Reputation-weighted supermajority vote rules.
        Also applies CRITICAL static-analysis veto and escalating scrutiny.
        """
        # Veto: CRITICAL static finding overrides community vote
        if maintainer_review is not None:
            if any(i.severity == 'CRITICAL' for i in maintainer_review.issues):
                return Decision.BLOCK_AGENT

        raw_votes = peer_result.vote_count

        # 1. Dynamic quorum: never require more votes than there were available reviewers
        effective_quorum = min(self.min_quorum, max(1, peer_result.max_possible_voters))
        if raw_votes < effective_quorum:
            return Decision.PENDING

        # 2. Reputation-weighted approval ratio
        w_approve = peer_result.weighted_approval_score
        w_reject  = peer_result.weighted_rejection_score
        w_total   = w_approve + w_reject

        weighted_ratio = w_approve / w_total if w_total > 0 else 0

        # 3. Escalating scrutiny: stricter threshold for agents with prior rejections
        effective_threshold = self.vote_threshold + min(prior_rejections * 0.05, 0.15)

        if weighted_ratio >= effective_threshold:
            return Decision.APPROVE
        elif w_reject >= w_approve:
            # BLOCK when ≥2 votes cast AND overwhelming rejection (weighted ratio < 0.3)
            if raw_votes >= 2 and weighted_ratio < 0.3:
                return Decision.BLOCK_AGENT
            return Decision.REJECT

        return Decision.PENDING

    def _evaluate_hybrid(self, peer_result, maintainer_review, author_rep,
                         prior_rejections: int = 0) -> Decision:
        """
        Hybrid: Weighted Score = (PeerConsensus * Weight) + (Maintainer * Weight)
        Dynamic weighting based on Author's historical reputation.

        Fallback: if the maintainer LLM was unavailable (rate-limited), defer
        entirely to peer consensus so legitimate PRs are not stuck in PENDING.
        CRITICAL vetoes from static analysis still apply even without LLM.
        """
        # Veto: Maintainer finds CRITICAL issue (static analysis, no LLM needed)
        if any(i.severity == 'CRITICAL' for i in maintainer_review.issues):
            return Decision.BLOCK_AGENT

        # LLM unavailable fallback — use peer consensus alone to avoid deadlock
        if not maintainer_review.llm_available:
            logger.info("  [Hybrid] Maintainer LLM unavailable — deferring to peer consensus")
            return self._evaluate_decentralized(peer_result)

        peer_score = peer_result.median_trust
        maint_score = maintainer_review.trust_score

        # Dynamic Weighting:
        # If author is highly trusted (>0.8), peer review matters less (Fast Track).
        # If author is new/untrusted, peer review matters more.
        if author_rep > 0.8:
            w_peer, w_maint = 0.3, 0.7
        else:
            w_peer, w_maint = 0.5, 0.5

        final_score = (peer_score * w_peer) + (maint_score * w_maint)

        # Escalating scrutiny: agents with prior rejections need a higher score to merge
        effective_threshold = self.trust_threshold + min(prior_rejections * 0.05, 0.15)

        if final_score >= effective_threshold:
            return Decision.APPROVE
        elif final_score < 0.3:
            return Decision.BLOCK_AGENT
        elif final_score < 0.5:
            return Decision.REJECT

        return Decision.PENDING