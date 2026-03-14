"""
Hybrid Trust System - Bridge to Governance Engine
"""

import logging
from dataclasses import dataclass
from src.governance.engine import GovernanceEngine
from src.governance.enums import Decision

logger = logging.getLogger("govim")


# Alias for backward compatibility if other modules import FinalDecision
FinalDecision = Decision

@dataclass
class HybridTrustResult:
    """Complete trust evaluation result"""
    final_decision: Decision
    final_trust: float
    peer_consensus: object      
    maintainer_review: object   
    reasoning: str
    should_block: bool


class SimplifiedHybridTrust:
    """
    Bridge class that gathers data from Peers and Maintainer,
    then delegates the decision to the GovernanceEngine.
    """
    
    def __init__(self, peer_consensus_engine, maintainer_agent, governance_engine: GovernanceEngine):
        """
        Initialize hybrid trust system with a specific Governance Engine
        """
        self.peer_consensus = peer_consensus_engine
        self.maintainer = maintainer_agent
        self.engine = governance_engine
        
        logger.info(f"[HybridTrust] Initialized using Governance Model: {self.engine.model.name}")
    
    def evaluate_commit(
        self,
        committer_agent,
        all_benign_agents: list,
        code_content: str,
        commit_hash: str,
        commit_message: str,
        filename: str = "",
        sybil_voters: list = None   # Forwarded from SybilOrchestrator when active
    ) -> HybridTrustResult:
        """
        Gather reviews and ask Governance Engine for a decision.
        sybil_voters (optional): list of SybilAgent instances that also cast
        votes in the peer consensus phase — they may collude on group-member PRs.
        """
        # Step 1: Peer Review Phase
        peer_result = self.peer_consensus.get_peer_consensus(
            committer_agent=committer_agent,
            all_benign_agents=all_benign_agents,
            code_content=code_content,
            commit_message=commit_message,
            sybil_voters=sybil_voters
        )
        
        # Step 2: Maintainer Phase
        maintainer_review = self.maintainer.review_commit(
            agent_name=committer_agent.name,
            filename=filename or "unknown.py",
            content=code_content,
            commit_hash=commit_hash,
            commit_message=commit_message
        )
        
        # Step 3: Governance Engine Decision
        # This determines Approve/Reject based on Centralized/Decentralized/Hybrid rules
        decision = self.engine.evaluate(
            peer_result=peer_result,
            maintainer_review=maintainer_review,
            author_reputation=committer_agent.reputation
        )
        if self.engine.model.name == "DECENTRALIZED":
            # In DAO mode, trust is purely what peers think
            final_trust = peer_result.median_trust
        else:
            # In Hybrid/Centralized, average them
            final_trust = (peer_result.median_trust + maintainer_review.trust_score) / 2
        
        should_block = (decision == Decision.BLOCK_AGENT)
        # Generate reasoning string
        reasoning = self._generate_reasoning(
            committer_agent.name, final_trust, peer_result, maintainer_review, decision
        )
        
        return HybridTrustResult(
            final_decision=decision,
            final_trust=final_trust,
            peer_consensus=peer_result,
            maintainer_review=maintainer_review,
            reasoning=reasoning,
            should_block=should_block
        )
    
    def _generate_reasoning(self, agent, trust, peer, maint, decision):
        return f"Model: {self.engine.model.name}, Decision: {decision.name}, PeerVotes: {peer.vote_count}"