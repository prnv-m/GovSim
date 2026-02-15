"""
Peer Consensus Engine - Byzantine consensus using BENIGN AGENTS
Benign agents review each other's commits, maintainer makes final decision
"""

import logging
import statistics
from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConsensusDecision(Enum):
    """Peer consensus outcomes"""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    NO_CONSENSUS = "no_consensus"


@dataclass
class PeerConsensusResult:
    """Result of peer consensus voting among benign agents"""
    consensus_reached: bool
    decision: ConsensusDecision
    median_trust: float         # Byzantine-resistant aggregation
    confidence: float           # Based on agreement level
    vote_distribution: Dict     # How peers voted
    participating_peers: int
    required_votes: int
    peer_reviews: List          # Individual peer reviews
    reasoning: str


class PeerConsensusEngine:
    """
    Byzantine consensus using BENIGN AGENTS as peer reviewers
    
    Architecture:
    1. When agent X makes a commit
    2. Other benign agents (peers) review the commit
    3. Use Byzantine consensus (median, supermajority) to aggregate
    4. Maintainer makes final decision based on peer consensus
    
    Key features:
    - Uses existing benign agents (not separate blue team)
    - Automatically excludes malicious agents from review pool
    - Tolerates up to f wrong/compromised peer reviews
    - Requires 2f+1 peers for consensus
    """
    
    def __init__(self, f: int = 1):
        """
        Initialize peer consensus engine
        
        Args:
            f: Byzantine fault tolerance
               f=1 tolerates 1 wrong reviewer, needs 3 peers minimum
               f=2 tolerates 2 wrong reviewers, needs 5 peers minimum
        """
        self.f = f
        self.quorum = 2 * f + 1
        
        self.total_votes = 0
        self.consensus_reached_count = 0
        
        logger.info(f"[PeerConsensus] Initialized: f={f}, quorum={self.quorum}")
    
    def get_peer_consensus(
        self,
        committer_agent,
        all_benign_agents: List,
        code_content: str,
        commit_message: str = ""
    ) -> PeerConsensusResult:
        """
        Get consensus from peer benign agents
        
        Args:
            committer_agent: Agent who made the commit
            all_benign_agents: List of ALL benign agents
            code_content: Code to review
            commit_message: Commit message
            
        Returns:
            PeerConsensusResult with aggregated peer opinion
        """
        self.total_votes += 1
        
        # Get peers (exclude the committer and malicious agents)
        peer_reviewers = [
            agent for agent in all_benign_agents
            if agent.name != committer_agent.name and not agent.is_malicious
        ]
        
        logger.info(
            f"[PeerConsensus] Getting reviews from {len(peer_reviewers)} peers "
            f"for {committer_agent.name}'s commit"
        )
        
        # Collect peer reviews
        peer_reviews = []
        for peer in peer_reviewers:
            try:
                review = peer.review_peer_commit(code_content, commit_message)
                peer_reviews.append(review)
                logger.debug(
                    f"  [{peer.name}] Vote: {'SAFE' if review.is_safe else 'UNSAFE'} "
                    f"(trust={review.trust_score:.2f})"
                )
            except Exception as e:
                logger.error(f"  [{peer.name}] Review failed: {e}")
                continue
        
        # Check if we have enough peers
        if len(peer_reviews) < self.quorum:
            logger.warning(
                f"[PeerConsensus] Insufficient peers: {len(peer_reviews)}/{self.quorum}"
            )
            return PeerConsensusResult(
                consensus_reached=False,
                decision=ConsensusDecision.NO_CONSENSUS,
                median_trust=0.5,
                confidence=0.0,
                vote_distribution={'insufficient_peers': True},
                participating_peers=len(peer_reviews),
                required_votes=self.quorum,
                peer_reviews=peer_reviews,
                reasoning=f"Need {self.quorum} peers, only {len(peer_reviews)} available"
            )
        
        # Aggregate with Byzantine-resistant methods
        return self._aggregate_peer_reviews(peer_reviews)
    
    def _aggregate_peer_reviews(self, peer_reviews: List) -> PeerConsensusResult:
        """
        Aggregate peer reviews using Byzantine-resistant methods
        
        Uses:
        - MEDIAN (not mean) for trust scores - resistant to outliers
        - Supermajority voting for safe/unsafe decisions
        - Standard deviation to detect disagreement
        """
        # Extract data
        trust_scores = [r.trust_score for r in peer_reviews]
        safe_votes = sum(1 for r in peer_reviews if r.is_safe)
        unsafe_votes = len(peer_reviews) - safe_votes
        
        # Byzantine-resistant: MEDIAN (not mean)
        median_trust = statistics.median(trust_scores)
        
        # Standard deviation (low = agreement, high = disagreement)
        std_dev = statistics.stdev(trust_scores) if len(trust_scores) > 1 else 0.0
        
        # Confidence based on agreement
        base_confidence = 1.0 - min(1.0, std_dev * 2)
        
        # Weight by individual confidences
        avg_confidence = statistics.mean([r.confidence for r in peer_reviews])
        final_confidence = (base_confidence + avg_confidence) / 2
        
        # Vote distribution
        vote_dist = {
            'safe': safe_votes,
            'unsafe': unsafe_votes,
            'total': len(peer_reviews)
        }
        
        # Check for consensus (supermajority)
        consensus_reached = max(safe_votes, unsafe_votes) >= self.quorum
        
        # Determine decision
        if not consensus_reached:
            decision = ConsensusDecision.NO_CONSENSUS
            reasoning = f"No supermajority: {safe_votes} safe vs {unsafe_votes} unsafe (need {self.quorum})"
        
        elif safe_votes >= self.quorum:
            # Peers say SAFE
            if median_trust >= 0.75:
                decision = ConsensusDecision.SAFE
                reasoning = f"Strong consensus: {safe_votes}/{len(peer_reviews)} peers say SAFE"
            else:
                decision = ConsensusDecision.SUSPICIOUS
                reasoning = f"Weak consensus: {safe_votes}/{len(peer_reviews)} say safe, but median trust={median_trust:.2f}"
        
        else:
            # Peers say UNSAFE
            if median_trust < 0.5:
                decision = ConsensusDecision.MALICIOUS
                reasoning = f"Strong consensus: {unsafe_votes}/{len(peer_reviews)} peers say MALICIOUS"
            else:
                decision = ConsensusDecision.SUSPICIOUS
                reasoning = f"Mixed signals: {unsafe_votes}/{len(peer_reviews)} say unsafe, median trust={median_trust:.2f}"
        
        # Force SUSPICIOUS if high disagreement
        if std_dev > 0.3 and decision != ConsensusDecision.NO_CONSENSUS:
            original = decision
            decision = ConsensusDecision.SUSPICIOUS
            reasoning += f" [High disagreement: std={std_dev:.2f}, changed from {original.value}]"
        
        if consensus_reached:
            self.consensus_reached_count += 1
        
        return PeerConsensusResult(
            consensus_reached=consensus_reached,
            decision=decision,
            median_trust=median_trust,
            confidence=final_confidence,
            vote_distribution=vote_dist,
            participating_peers=len(peer_reviews),
            required_votes=self.quorum,
            peer_reviews=peer_reviews,
            reasoning=reasoning
        )
    
    def get_statistics(self) -> Dict:
        """Get consensus statistics"""
        consensus_rate = (
            self.consensus_reached_count / self.total_votes
            if self.total_votes > 0 else 0.0
        )
        
        return {
            'total_votes': self.total_votes,
            'consensus_reached': self.consensus_reached_count,
            'consensus_rate': consensus_rate,
            'byzantine_tolerance': self.f,
            'quorum_required': self.quorum
        }
    
    def print_statistics(self):
        """Print consensus statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*70)
        print("PEER CONSENSUS STATISTICS")
        print("="*70)
        print(f"Total Reviews: {stats['total_votes']}")
        print(f"Consensus Reached: {stats['consensus_reached']} ({stats['consensus_rate']:.1%})")
        print(f"Byzantine Tolerance: f={stats['byzantine_tolerance']} (tolerates {stats['byzantine_tolerance']} wrong peers)")
        print(f"Quorum Required: {stats['quorum_required']} peer reviews")