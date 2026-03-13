"""
Task manager for defining projects and assigning features to agents
"""

import logging

logger = logging.getLogger(__name__)

class Task:
    """Represents a project task"""
    
    def __init__(self, name: str, description: str, features: list,difficulty: str):
        """
        Args:
            name: Project name (e.g., "E-Voting System")
            description: What the project does
            features: List of feature dicts
        """
        self.name = name
        self.description = description
        self.difficulty = difficulty
        self.features = features  # List of {'name': '...', 'description': '...'}
    
    def __repr__(self):
        return f"Task({self.name}, {len(self.features)} features)"

class FeatureAssignment:
    """Manages assigning features to agents"""
    
    def __init__(self):
        self.assignments = {}  # agent_name -> [features]
    
    def assign_feature(self, agent_name: str, feature: dict):
        """Assign a feature to an agent"""
        if agent_name not in self.assignments:
            self.assignments[agent_name] = []
        
        self.assignments[agent_name].append(feature)
        logger.info(f"Assigned {feature['name']} to {agent_name}")
    
    def get_agent_features(self, agent_name: str) -> list:
        """Get all features assigned to agent"""
        return self.assignments.get(agent_name, [])
    
    def get_next_feature(self, agent_name: str) -> dict:
        """Get next unworked feature for agent"""
        features = self.get_agent_features(agent_name)
        
        for feature in features:
            if not feature.get('completed', False):
                return feature
        
        return None  # All features done

# Pre-defined tasks
TASKS = {
    "e-voting": Task(
        name="E-Voting System",
        description="Secure electronic voting platform",
        difficulty="HARD",
        features=[
            {"name": "user_auth", "description": "User registration & authentication"},
            {"name": "ballot_encryption", "description": "Encrypt ballots"},
            {"name": "vote_counting", "description": "Count votes securely"},
            {"name": "audit_logging", "description": "Log all actions"},
            {"name": "admin_dashboard", "description": "Admin interface"},
        ]
    ),
    
    "banking": Task(
        name="Banking System",
        description="Secure payment processing",
        difficulty="HARD",
        features=[
            {"name": "account_mgmt", "description": "Account creation and management"},
            {"name": "fund_transfer", "description": "Transfer funds between accounts"},
            {"name": "fraud_detection", "description": "Detect suspicious transactions"},
            {"name": "transaction_log", "description": "Log all transactions"},
            {"name": "reconciliation", "description": "Reconcile accounts"},
        ]
    ),
    
    "medical": Task(
        name="Medical Records System",
        description="Secure patient data management",
        difficulty="MEDIUM",
        features=[
            {"name": "patient_auth", "description": "Patient login system"},
            {"name": "record_storage", "description": "Store encrypted records"},
            {"name": "doctor_access", "description": "Doctor access control"},
            {"name": "prescriptions", "description": "Prescription management"},
            {"name": "audit_log", "description": "Medical audit logging"},
        ]
    ),
    
    "supply_chain": Task(
        name="Supply Chain Tracking",
        description="Track products through supply chain",
        difficulty="EASY",
        features=[
            {"name": "product_tracking", "description": "Track product location"},
            {"name": "blockchain_ledger", "description": "Immutable ledger"},
            {"name": "vendor_verify", "description": "Verify vendors"},
            {"name": "chain_custody", "description": "Chain of custody"},
            {"name": "anomaly_detect", "description": "Detect anomalies"},
        ]
    ),
}

def create_assignment(task_name: str, agents: list) -> FeatureAssignment:
    """
    Create feature assignment for a task
    
    Args:
        task_name: Name of task (from TASKS)
        agents: List of agent objects
    
    Returns:
        FeatureAssignment object
    """
    
    if task_name not in TASKS:
        raise ValueError(f"Unknown task: {task_name}")
    
    task = TASKS[task_name]
    assignment = FeatureAssignment()
    
    # Round-robin assignment
    for i, feature in enumerate(task.features):
        agent = agents[i % len(agents)]
        assignment.assign_feature(agent.name, feature)
    
    return assignment

def print_assignment(task_name: str, assignment: FeatureAssignment):
    """Print assignment for visualization"""
    print(f"\nTask: {task_name}")
    print("-" * 50)
    
    for agent_name, features in assignment.assignments.items():
        print(f"\n{agent_name}:")
        for feature in features:
            print(f"  • {feature['name']}: {feature['description']}")
