import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from src.security.code_analyzer import CodeAnalyzer
from dataclasses import dataclass
from typing import List

@dataclass
class PeerReview:
    """Result of a peer review by a benign agent"""
    reviewer_name: str
    is_safe: bool
    trust_score: float      # 0.0 - 1.0
    confidence: float       # 0.0 - 1.0
    findings: List[str]
    reasoning: str
logger = logging.getLogger(__name__)

class AgentType(Enum):
    BENIGN = "benign"
    MALICIOUS = "malicious"

class AgentPhase(Enum):
    INFILTRATION = "infiltration"
    TRUST_BUILDING = "trust_building"
    EXPLOITATION = "exploitation"
    DETECTED = "detected"

class BaseAgent:
    def __init__(self, name: str, agent_type: AgentType, email: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.agent_type = agent_type
        self.email = email
        self.created_at = datetime.now()
        self.commits = []
        
        # FIX 1: Start at NEUTRAL (0.5) instead of MALICIOUS (0.0)
        self.reputation = 0.5 
        
        self.status = "active"
        self.tasks_completed = 0
        self.code_quality = 0.0
        self.is_malicious = agent_type == AgentType.MALICIOUS
        self.username = None
        self.password = None
        self.account_created = False
        
        logger.info(f"Agent created: {name} - Type: {agent_type.value} - Start Rep: 0.50")
    
    def update_reputation(self, round_score: float):
        """
        FIX 2: Asymmetric Reputation Update
        Success (Merging) builds trust faster than failure kills it (for benign devs).
        """
        alpha = 0.3  # Learning rate
        
        if round_score >= 0.7:
            # POSITIVE ACTION: Agent code was merged.
            # Use a weighted average to climb toward the new high score.
            self.reputation = (self.reputation * (1 - alpha)) + (round_score * alpha)
        else:
            # NEGATIVE/NEUTRAL ACTION: Code was rejected or suspicious.
            # Harsher drop — sybils caught attacking should lose trust quickly.
            penalty_alpha = 0.35
            self.reputation = (self.reputation * (1 - penalty_alpha)) + (round_score * penalty_alpha)
            
        # Keep between 0 and 1
        self.reputation = max(0.0, min(1.0, self.reputation))
        logger.info(f"  Agent {self.name}: Reputation updated to {self.reputation:.2f}")

    # ... (Keep log_commit, set_credentials, to_dict as they are) ...
    def log_commit(self, filename: str, commit_hash: str, message: str, quality_score: float = 0.5):
        self.commits.append({
            "filename": filename,
            "hash": commit_hash,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "quality": quality_score
        })
        self.tasks_completed += 1
        self.code_quality = sum(c["quality"] for c in self.commits) / len(self.commits)
    
    def set_credentials(self, username: str, password: str):
        self.username = username
        self.password = password
        self.account_created = True

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type.value,
            "email": self.email,
            "username": self.username,
            "reputation": self.reputation,
            "status": self.status,
            "commits": len(self.commits),
            "tasks_completed": self.tasks_completed,
            "code_quality": self.code_quality,
            "account_created": self.account_created,
            "created_at": self.created_at.isoformat()
        }


class BenignAgent(BaseAgent):
    """Honest developer agent - WITH PEER REVIEW CAPABILITY"""
    
    def __init__(self, name: str, email: str):
        super().__init__(name, AgentType.BENIGN, email)
        self.helpfulness = 0.8
        self.code_quality_baseline = 0.85
        
        # NEW: Add code analyzer for peer reviews
        self.code_analyzer = CodeAnalyzer()
        self.reviews_performed = 0
        self.reviews_correct = 0
        
        logger.info(f"✓ BenignAgent {name} initialized with peer review capability")
    
    # NEW METHOD: Peer review capability
    def review_peer_commit(self, code_content: str, commit_message: str = "") -> PeerReview:
        """
        Review another agent's code commit for Byzantine consensus
        
        Args:
            code_content: Source code to review
            commit_message: Commit message for context
            
        Returns:
            PeerReview with this agent's independent assessment
        """
        self.reviews_performed += 1
        
        # Run static analysis
        static_result = self.code_analyzer.analyze(code_content)
        
        # Calculate trust score (inverse of risk)
        base_trust = 1.0 - (static_result['risk_score'] / 100.0)
        
        # Benign agents are naturally cautious
        adjusted_trust = self._apply_review_bias(base_trust, static_result)
        
        # Calculate confidence
        confidence = self._calculate_review_confidence(static_result, code_content)
        
        # Determine if safe (conservative threshold)
        is_safe = adjusted_trust >= 0.6 and static_result['risk_level'] not in ['HIGH', 'CRITICAL']
        
        # Generate reasoning
        reasoning = (
            f"Risk: {static_result['risk_level']} ({static_result['risk_score']}/100) | "
            f"Trust: {adjusted_trust:.2f} | Findings: {len(static_result['findings'])}"
        )
        
        logger.debug(
            f"[{self.name}] Peer review: trust={adjusted_trust:.2f}, "
            f"safe={is_safe}, confidence={confidence:.2f}"
        )
        
        return PeerReview(
            reviewer_name=self.name,
            is_safe=is_safe,
            trust_score=adjusted_trust,
            confidence=confidence,
            findings=static_result['findings'],
            reasoning=reasoning
        )
    
    def _apply_review_bias(self, base_trust: float, static_result: dict) -> float:
        """Apply benign agent's natural caution"""
        adjusted = base_trust
        
        # Benign agents are more cautious with risky code
        if static_result['risk_level'] in ['HIGH', 'CRITICAL']:
            adjusted *= 0.8
        elif static_result['risk_level'] == 'MEDIUM':
            adjusted *= 0.9
        
        # Small variance (agents have slightly different thresholds)
        import random
        variance = random.uniform(-0.05, 0.05)
        adjusted += variance
        
        return max(0.0, min(1.0, adjusted))
    
    def _calculate_review_confidence(self, static_result: dict, code: str) -> float:
        """Calculate confidence in the review"""
        confidence = 0.7  # Base confidence
        
        # More findings = higher confidence
        finding_count = len(static_result['findings'])
        if finding_count > 0:
            confidence += min(0.2, finding_count * 0.05)
        
        # Clear risk levels increase confidence
        if static_result['risk_level'] in ['CRITICAL', 'LOW']:
            confidence += 0.1
        
        # Very short or very long code reduces confidence
        line_count = len(code.split('\n'))
        if line_count < 5 or line_count > 200:
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def update_review_accuracy(self, was_correct: bool):
        """Update review accuracy statistics"""
        if was_correct:
            self.reviews_correct += 1
    
    def get_review_accuracy(self) -> float:
        """Get peer review accuracy rate"""
        if self.reviews_performed == 0:
            return 0.0
        return self.reviews_correct / self.reviews_performed
    
    def get_review_stats(self) -> dict:
        """Get detailed review statistics"""
        return {
            'reviews_performed': self.reviews_performed,
            'reviews_correct': self.reviews_correct,
            'accuracy': self.get_review_accuracy()
        }

class MaliciousAgent(BaseAgent):
    """Attacker agent with phases"""

    def __init__(self, name: str, email: str):
        super().__init__(name, AgentType.MALICIOUS, email)
        self.phase = AgentPhase.INFILTRATION
        self.attack_payload = None
        logger.info(f"✓ MaliciousAgent {name} initialized (Phase: {self.phase.value})")

    def set_phase(self, phase: AgentPhase):
        """Update attack phase"""
        self.phase = phase
        logger.info(f"  Agent {self.name}: Phase changed to {phase.value}")

    def set_payload(self, payload: str):
        """Set malicious payload"""
        self.attack_payload = payload
        logger.info(f"  Agent {self.name}: Payload set")


class SybilAgent(MaliciousAgent):
    """
    Advanced Sybil attacker operating inside a coordinated ring.

    Attack lifecycle:
      1. TRUST_BUILDING_ROUNDS rounds: submits clean, benign code to build reputation.
      2. After threshold: flips to EXPLOITATION — injects malicious code in own PRs
         and auto-approves every group member's attack PR (collusion vote).

    Group members share a group_id so they can recognise each other.
    """

    TRUST_BUILDING_ROUNDS = 3

    def __init__(self, name: str, email: str, group_id: str):
        super().__init__(name, email)
        self.group_id = group_id          # Shared ring identifier
        self.rounds_participated = 0      # Increments each time this agent submits a PR
        self.in_attack_mode = False       # Flips after TRUST_BUILDING_ROUNDS
        logger.info(
            f"[SYBIL] {name} initialised — group='{group_id}', "
            f"trust-building for {self.TRUST_BUILDING_ROUNDS} rounds before striking."
        )

    def record_round_participation(self):
        """
        Call after each round this agent submits a PR.
        Flips the agent to EXPLOITATION mode once the trust-building
        threshold is reached.
        """
        self.rounds_participated += 1
        if self.rounds_participated > self.TRUST_BUILDING_ROUNDS and not self.in_attack_mode:
            self.in_attack_mode = True
            self.set_phase(AgentPhase.EXPLOITATION)
            logger.warning(
                f"[SYBIL] *** {self.name} SWITCHING TO ATTACK MODE *** "
                f"(rep={self.reputation:.2f} after {self.rounds_participated} clean rounds)"
            )

    def should_inject_malicious_code(self) -> bool:
        """True only once the trust-building phase is complete."""
        return self.in_attack_mode

    def would_approve_sybil_peer(self, pr_author) -> bool:
        """
        Returns True when this agent should collude and blindly APPROVE
        a group member's malicious PR.
        Only activates when the PR author is also a SybilAgent in the same ring
        who is currently in attack mode.
        """
        if not isinstance(pr_author, SybilAgent):
            return False
        return pr_author.group_id == self.group_id and pr_author.name != self.name
