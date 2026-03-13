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
        self.min_quorum = 2           # Minimum votes required (Decentralized)
        self.vote_threshold = 0.51    # 51% majority required (Decentralized)
        self.trust_threshold = 0.6    # Minimum trust score to merge (Hybrid)

    def evaluate(self, peer_result, maintainer_review, author_reputation: float) -> Decision:
        """
        Evaluate a Pull Request based on the active model.
        """
        # logger.debug(f"[Governance] Evaluating using {self.model.value.upper()} model")

        if self.model == GovernanceModel.CENTRALIZED:
            return self._evaluate_centralized(maintainer_review)
            
        elif self.model == GovernanceModel.DECENTRALIZED:
            return self._evaluate_decentralized(peer_result)
            
        elif self.model == GovernanceModel.HYBRID:
            return self._evaluate_hybrid(peer_result, maintainer_review, author_reputation)
            
        return Decision.PENDING

    def _evaluate_centralized(self, maintainer_review) -> Decision:
        """
        Centralized: The Maintainer's word is law. Peer votes are ignored.
        """
        # Critical security issues = BLOCK
        critical_issues = [i for i in maintainer_review.issues if i.severity == 'CRITICAL']
        if critical_issues:
            return Decision.BLOCK

        # Maintainer trust thresholds
        if maintainer_review.trust_score >= 0.7:
            return Decision.APPROVE
        elif maintainer_review.trust_score < 0.4:
            return Decision.REJECT
        else:
            return Decision.PENDING # Maintainer unsure (needs changes)

    def _evaluate_decentralized(self, peer_result) -> Decision:
        """
        Decentralized: Majority vote rules. Maintainer review is ignored.
        """
        total_votes = peer_result.vote_count
        
        # 1. Check Quorum
        if total_votes < self.min_quorum:
            # logger.info(f"  Quorum not met ({total_votes}/{self.min_quorum})")
            return Decision.PENDING

        # 2. Count Votes
        approvals = peer_result.approval_count
        rejections = peer_result.rejection_count
        
        # 3. Decision Logic (Simple Majority)
        approval_ratio = approvals / total_votes if total_votes > 0 else 0
        
        if approval_ratio > self.vote_threshold:
            return Decision.APPROVE
        elif rejections >= approvals:
            return Decision.REJECT
        
        return Decision.PENDING

    def _evaluate_hybrid(self, peer_result, maintainer_review, author_rep) -> Decision:
        """
        Hybrid: Weighted Score = (PeerConsensus * Weight) + (Maintainer * Weight)
        Dynamic weighting based on Author's historical reputation.
        """
        # Veto: Maintainer finds CRITICAL issue
        if any(i.severity == 'CRITICAL' for i in maintainer_review.issues):
            return Decision.BLOCK

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
        
        # logger.info(f"  Hybrid Score: {final_score:.2f} (AuthorRep: {author_rep:.2f})")

        if final_score >= self.trust_threshold:
            return Decision.APPROVE
        elif final_score < 0.3:
            return Decision.BLOCK
        elif final_score < 0.5:
            return Decision.REJECT
            
        return Decision.PENDING