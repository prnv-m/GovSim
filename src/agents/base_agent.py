import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

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
    """Base class for all agents"""
    
    def __init__(self, name: str, agent_type: AgentType, email: str):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.agent_type = agent_type
        self.email = email
        self.created_at = datetime.now()
        self.commits = []
        self.reputation = 0.0
        self.status = "active"
        self.tasks_completed = 0
        self.code_quality = 0.0
        self.is_malicious = agent_type == AgentType.MALICIOUS
        self.username = None
        self.password = None
        self.account_created = False
        
        logger.info(f"Agent created: {name} ({self.id}) - Type: {agent_type.value}")
    
    def log_commit(self, filename: str, commit_hash: str, message: str, quality_score: float = 0.5):
        """Log a commit made by this agent"""
        self.commits.append({
            "filename": filename,
            "hash": commit_hash,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "quality": quality_score
        })
        self.tasks_completed += 1
        self.code_quality = sum(c["quality"] for c in self.commits) / len(self.commits)
        
        logger.info(f"  Agent {self.name}: Committed {filename} ({commit_hash})")
    
    def update_reputation(self, score: float):
        """Update agent reputation"""
        self.reputation = score
        logger.info(f"  Agent {self.name}: Reputation updated to {score:.2f}")

    def set_credentials(self, username: str, password: str):
        """Set account credentials for this agent"""
        self.username = username
        self.password = password
        self.account_created = True
        logger.info(f"  Agent {self.name}: Account set ({username})")
    
    def to_dict(self) -> Dict:
        """Convert agent to dictionary"""
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
    """Honest developer agent"""
    
    def __init__(self, name: str, email: str):
        super().__init__(name, AgentType.BENIGN, email)
        self.helpfulness = 0.8
        self.code_quality_baseline = 0.85
        logger.info(f"✓ BenignAgent {name} initialized")

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
