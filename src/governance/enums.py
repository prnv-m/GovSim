from enum import Enum

class GovernanceModel(Enum):
    CENTRALIZED = "centralized"       # Maintainer Authority (Dictator)
    DECENTRALIZED = "decentralized"   # Majority Vote (DAO)
    HYBRID = "hybrid"                 # Weighted Reputation System

class Decision(Enum):
    APPROVE = "approve"
    NEEDS_CHANGES = "needs_changes"
    SUSPICIOUS = "suspicious"
    REJECT = "reject"
    BLOCK_AGENT = "block_agent"
    PENDING = "pending"               # Specific for Decentralized (waiting for quorum)