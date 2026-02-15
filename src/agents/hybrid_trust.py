"""
Hybrid Trust System - Combines Peer Consensus + Maintainer Decision
Simplified version: Peers vote, Maintainer decides
"""

import logging
from typing import Dict, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FinalDecision(Enum):
    """Final decision by maintainer"""
    APPROVE = "approve"
    NEEDS_CHANGES = "needs_changes"
    SUSPICIOUS = "suspicious"
    REJECT = "reject"
    BLOCK_AGENT = "block_agent"


@dataclass
class HybridTrustResult:
    """Complete trust evaluation result"""
    final_decision: FinalDecision
    final_trust: float
    peer_consensus: object      # PeerConsensusResult
    maintainer_review: object   # MaintainerAgent review
    reasoning: str
    should_block: bool


class SimplifiedHybridTrust:
    """
    Simplified hybrid trust combining:
    1. Peer consensus (benign agents vote)
    2. Maintainer authority (final decision)
    
    No separate Bayesian tracking - maintainer already tracks reputation
    """
    
    def __init__(self, peer_consensus_engine, maintainer_agent):
        """
        Initialize hybrid trust system
        
        Args:
            peer_consensus_engine: PeerConsensusEngine instance
            maintainer_agent: MaintainerAgent instance
        """
        self.peer_consensus = peer_consensus_engine
        self.maintainer = maintainer_agent
        
        # Weights for combining scores
        self.weight_peers = 0.40        # Peer consensus
        self.weight_maintainer = 0.60   # Maintainer has more weight (final authority)
        
        logger.info(
            f"[HybridTrust] Initialized with weights: "
            f"Peers={self.weight_peers}, Maintainer={self.weight_maintainer}"
        )
    
    def evaluate_commit(
        self,
        committer_agent,
        all_benign_agents: list,
        code_content: str,
        commit_hash: str,
        commit_message: str,
        filename: str = ""
    ) -> HybridTrustResult:
        """
        Complete evaluation: peers vote, maintainer decides
        
        Args:
            committer_agent: Agent who made the commit
            all_benign_agents: All benign agents (for peer review)
            code_content: Source code
            commit_hash: Git commit hash
            commit_message: Commit message
            filename: File name
            
        Returns:
            HybridTrustResult with final decision
        """
        logger.info(f"[HybridTrust] Evaluating commit by {committer_agent.name}")
        
        # Step 1: Peer Consensus
        peer_result = self.peer_consensus.get_peer_consensus(
            committer_agent=committer_agent,
            all_benign_agents=all_benign_agents,
            code_content=code_content,
            commit_message=commit_message
        )
        
        # Step 2: Maintainer Review
        maintainer_review = self.maintainer.review_commit(
            agent_name=committer_agent.name,
            filename=filename or "unknown.py",
            content=code_content,
            commit_hash=commit_hash,
            commit_message=commit_message
        )
        
        # Step 3: Combine scores
        final_trust = self._combine_scores(
            peer_trust=peer_result.median_trust,
            peer_confidence=peer_result.confidence,
            maintainer_trust=maintainer_review.trust_score
        )
        
        # Step 4: Make final decision (maintainer-weighted)
        final_decision = self._make_final_decision(
            final_trust=final_trust,
            peer_result=peer_result,
            maintainer_review=maintainer_review
        )
        
        # Step 5: Generate reasoning
        reasoning = self._generate_reasoning(
            committer_agent.name,
            final_trust,
            peer_result,
            maintainer_review,
            final_decision
        )
        
        # Step 6: Determine if should block
        should_block = self._should_block(
            final_trust, 
            final_decision,
            committer_agent.name
        )
        
        return HybridTrustResult(
            final_decision=final_decision,
            final_trust=final_trust,
            peer_consensus=peer_result,
            maintainer_review=maintainer_review,
            reasoning=reasoning,
            should_block=should_block
        )
    
    def _combine_scores(
        self,
        peer_trust: float,
        peer_confidence: float,
        maintainer_trust: float
    ) -> float:
        """
        Combine peer and maintainer trust scores
        
        Maintainer gets more weight (60%) as final authority
        Peer consensus weighted by their confidence
        """
        # Adjust peer weight by their confidence
        effective_peer_weight = self.weight_peers * peer_confidence
        effective_maintainer_weight = self.weight_maintainer
        
        # Normalize
        total = effective_peer_weight + effective_maintainer_weight
        w_peer = effective_peer_weight / total
        w_maintainer = effective_maintainer_weight / total
        
        # Combine
        final_trust = (
            w_peer * peer_trust +
            w_maintainer * maintainer_trust
        )
        
        return final_trust
    
    def _make_final_decision(
        self,
        final_trust: float,
        peer_result,
        maintainer_review
    ) -> FinalDecision:
        """
        Make final decision - maintainer has authority but considers peers
        
        Decision priority:
        1. CRITICAL issues → REJECT
        2. Peer + Maintainer strong agreement → Follow consensus
        3. Disagreement → Maintainer decides
        """
        # Critical issues = immediate rejection
        critical_issues = [
            i for i in maintainer_review.issues
            if i.severity == 'CRITICAL'
        ]
        if critical_issues:
            return FinalDecision.REJECT
        
        # Strong peer + maintainer agreement on MALICIOUS
        if (peer_result.decision.value == 'malicious' and 
            maintainer_review.trust_score < 0.4 and
            peer_result.confidence > 0.7):
            if final_trust < 0.3:
                return FinalDecision.BLOCK_AGENT
            else:
                return FinalDecision.REJECT
        
        # Trust-based thresholds (maintainer-weighted)
        if final_trust < 0.3:
            return FinalDecision.BLOCK_AGENT
        elif final_trust < 0.5:
            return FinalDecision.REJECT
        elif final_trust < 0.65:
            return FinalDecision.SUSPICIOUS
        elif final_trust < 0.8:
            return FinalDecision.NEEDS_CHANGES
        else:
            return FinalDecision.APPROVE
    
    def _should_block(
        self,
        final_trust: float,
        decision: FinalDecision,
        agent_name: str
    ) -> bool:
        """Determine if agent should be blocked"""
        if decision == FinalDecision.BLOCK_AGENT:
            return True
        
        # Also check historical reputation from maintainer
        if agent_name in self.maintainer.agent_reputation:
            historical_trust = self.maintainer.agent_reputation[agent_name]['trust']
            if historical_trust < 0.25 and final_trust < 0.3:
                return True
        
        return False
    
    def _generate_reasoning(
        self,
        agent_name: str,
        final_trust: float,
        peer_result,
        maintainer_review,
        final_decision: FinalDecision
    ) -> str:
        """Generate comprehensive reasoning"""
        lines = []
        
        lines.append(f"HYBRID TRUST EVALUATION for {agent_name}")
        lines.append(f"  Final Trust: {final_trust:.2f}/1.0")
        lines.append(f"  Final Decision: {final_decision.value.upper()}")
        lines.append("")
        
        lines.append("Peer Consensus:")
        lines.append(f"  Decision: {peer_result.decision.value.upper()}")
        lines.append(f"  Median Trust: {peer_result.median_trust:.2f}")
        lines.append(f"  Confidence: {peer_result.confidence:.2f}")
        lines.append(f"  Votes: {peer_result.vote_distribution}")
        lines.append(f"  Peers: {peer_result.participating_peers}")
        lines.append("")
        
        lines.append("Maintainer Review:")
        lines.append(f"  Status: {maintainer_review.status.value.upper()}")
        lines.append(f"  Trust: {maintainer_review.trust_score:.2f}")
        lines.append(f"  Issues: {len(maintainer_review.issues)}")
        
        return "\n".join(lines)