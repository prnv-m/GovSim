"""
Peer Consensus Engine - Blue Team Code Reviewers
Agents use LLM to review PR diffs and vote on security.
Supports Fallback Routing across multiple LLM providers.
"""

import logging
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from src.governance.enums import Decision
from src.llm_client import CodeGenerator
import time
logger = logging.getLogger("govim")

@dataclass
class PeerReview:
    reviewer_name: str
    is_safe: bool
    trust_score: float
    confidence: float
    reason: str

@dataclass
class PeerConsensusResult:
    decision: Decision
    median_trust: float
    confidence: float
    vote_distribution: dict
    participating_peers: int
    approval_count: int
    rejection_count: int
    vote_count: int
    peer_reviews: List[PeerReview]

class PeerConsensusEngine:
    def __init__(self, f: int = 1):
        """
        f = Byzantine tolerance (number of malicious peers we can tolerate)
        Quorum required = 2f + 1
        """
        self.f = f
        self.quorum = (2 * f) + 1
        
        # Use the CodeGenerator as an LLM Router instead of just Gemini
        self.llm_router = CodeGenerator()
        
        logger.info(f"PeerConsensus initialized (Quorum: {self.quorum})")

    def get_peer_consensus(
        self,
        committer_agent,
        all_benign_agents: list,
        code_content: str,
        commit_message: str,
        sybil_voters: list = None   # Optional Sybil ring members who also cast votes
    ) -> PeerConsensusResult:
        """
        Gather votes from all benign agents (excluding the author).
        In Sybil mode, also accepts sybil_voters — colluding attackers who
        auto-approve their group member's PRs while voting honestly on all others.

        code_content here is the Git Diff of the Pull Request.
        """
        # Filter out the author so they can't vote on their own PR
        reviewers = [a for a in all_benign_agents if a.name != committer_agent.name]

        reviews = []
        approvals = 0
        rejections = 0

        # ── Honest benign votes ───────────────────────────────────────────────
        logger.info(f"  Requesting reviews from {len(reviewers)} benign peer(s)...")

        for reviewer in reviewers:
            time.sleep(4)
            is_safe, confidence, reason = self._analyze_diff(reviewer.name, code_content)

            review = PeerReview(
                reviewer_name=reviewer.name,
                is_safe=is_safe,
                trust_score=reviewer.reputation,
                confidence=confidence,
                reason=reason
            )
            reviews.append(review)

            if is_safe:
                approvals += 1
                logger.info(f"    [{reviewer.name}] Voted: APPROVE (Conf: {confidence:.2f})")
            else:
                rejections += 1
                logger.info(f"    [{reviewer.name}] Voted: REJECT  (Reason: {reason})")

        # ── Sybil colluder votes (if Sybil mode is active) ───────────────────
        if sybil_voters:
            logger.info(f"  [SYBIL] {len(sybil_voters)} sybil voter(s) casting votes...")
            for sybil in sybil_voters:
                is_safe, confidence, reason = self._get_sybil_vote(
                    sybil, committer_agent, code_content
                )
                review = PeerReview(
                    reviewer_name=f"{sybil.name} [SYBIL]",
                    is_safe=is_safe,
                    trust_score=sybil.reputation,
                    confidence=confidence,
                    reason=reason
                )
                reviews.append(review)

                if is_safe:
                    approvals += 1
                    logger.info(
                        f"    [{sybil.name}] Sybil Vote: APPROVE "
                        f"(Conf: {confidence:.2f}) | {reason}"
                    )
                else:
                    rejections += 1
                    logger.info(
                        f"    [{sybil.name}] Sybil Vote: REJECT  (Reason: {reason})"
                    )

        # ── Tally ─────────────────────────────────────────────────────────────
        vote_count = len(reviews)
        if vote_count == 0:
            return self._empty_result()

        avg_trust = sum(r.trust_score for r in reviews) / vote_count
        avg_confidence = sum(r.confidence for r in reviews) / vote_count

        if vote_count < self.quorum:
            decision = Decision.PENDING
        elif approvals > rejections:
            decision = Decision.APPROVE
        else:
            decision = Decision.REJECT

        return PeerConsensusResult(
            decision=decision,
            median_trust=avg_trust,
            confidence=avg_confidence,
            vote_distribution={"approve": approvals, "reject": rejections},
            participating_peers=vote_count,
            approval_count=approvals,
            rejection_count=rejections,
            vote_count=vote_count,
            peer_reviews=reviews
        )

    def _get_sybil_vote(
        self, sybil_voter, committer_agent, diff_text: str
    ) -> Tuple[bool, float, str]:
        """
        Determine a sybil agent's vote.

        Collusion rule: if the PR author is a group member currently in attack
        mode, the sybil voter auto-APPROVEs regardless of code content.
        On all other PRs (honest devs or trust-building peers) they vote
        normally to avoid raising suspicion.
        """
        from src.agents.base_agent import SybilAgent

        if (
            isinstance(committer_agent, SybilAgent)
            and sybil_voter.would_approve_sybil_peer(committer_agent)
            and committer_agent.in_attack_mode
        ):
            logger.warning(
                f"[SYBIL COLLUSION] {sybil_voter.name} auto-APPROVING "
                f"malicious PR by ring member {committer_agent.name}"
            )
            return True, 0.95, "COLLUDE: auto-approve by sybil ring member"

        # Vote honestly — they don't want to appear suspicious
        return self._analyze_diff(sybil_voter.name, diff_text)

    def _analyze_diff(self, reviewer_name: str, diff_text: str) -> Tuple[bool, float, str]:
        """
        Uses LLM Router to analyze the PR diff. Falls back to static analysis if all LLMs fail.
        Returns: (is_safe: bool, confidence: float, reason: str)
        """
        if not diff_text or diff_text.strip() == "":
            return True, 0.5, "Empty diff"

        # Attempt LLM Analysis via Fallback Router
        for provider in self.llm_router.providers:
            try:
                llm_result = self.llm_router.analyze_code(diff_text, analysis_type="security")
                if llm_result and isinstance(llm_result, dict):
                    # Safety cast just in case LLM outputs a string instead of boolean
                    is_safe = llm_result.get("is_safe", True)
                    if isinstance(is_safe, str):
                        is_safe = str(is_safe).lower() == 'true'
                        
                    confidence = float(llm_result.get("confidence", 0.8))
                    
                    # Handle varying formats for 'issues'
                    issues = llm_result.get("issues",[])
                    if isinstance(issues, list) and len(issues) > 0:
                        reason = str(issues[0])
                    else:
                        reason = "Looks safe"
                        
                    logger.debug(f"[{provider.name}] Review successful for {reviewer_name}")
                    return is_safe, confidence, reason
            except Exception as e:
                logger.debug(f"[{provider.name}] review failed for {reviewer_name}: {e}. Trying next provider...")
                continue # Try the next provider in the list

        # Fallback: Static Keyword Analysis (If all LLMs fail or rate limit)
        logger.warning(f"All LLM providers failed for {reviewer_name}. Falling back to static analysis.")
        dangerous_keywords =["os.system", "subprocess", "eval(", "exec(", "pickle.loads"]
        
        # Only check added lines in the diff
        added_lines =[line for line in diff_text.split('\n') if line.startswith('+') and not line.startswith('+++')]
        
        for line in added_lines:
            for keyword in dangerous_keywords:
                if keyword in line:
                    return False, 0.9, f"Detected dangerous keyword: {keyword}"
                    
        return True, 0.7, "Passed static keyword scan"


    def _empty_result(self):
        return PeerConsensusResult(
            decision=Decision.PENDING, median_trust=0.5, confidence=0.0,
            vote_distribution={"approve": 0, "reject": 0},
            participating_peers=0, approval_count=0, rejection_count=0,
            vote_count=0, peer_reviews=[]
        )
        
    def print_statistics(self):
        logger.info("\nPeer Consensus Engine Statistics generated.")