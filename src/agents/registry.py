import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from config import Config
from src.agents.base_agent import BaseAgent, BenignAgent, MaliciousAgent, AgentType

logger = logging.getLogger(__name__)

class AgentRegistry:
    """Registry for all agents"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.registry_file = Config.DATA_DIR / "agent_registry.json"
    
    def register_agent(self, agent: BaseAgent) -> bool:
        """Register an agent"""
        try:
            self.agents[agent.id] = agent
            logger.info(f"✓ Registered agent: {agent.name} ({agent.id})")
            self.save()
            return True
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False
    
    def create_benign_agent(self, name: str, email: str) -> BenignAgent:
        """Create and register a benign agent"""
        agent = BenignAgent(name, email)
        self.register_agent(agent)
        return agent
    
    def create_malicious_agent(self, name: str, email: str) -> MaliciousAgent:
        """Create and register a malicious agent"""
        agent = MaliciousAgent(name, email)
        self.register_agent(agent)
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """Get all agents of a type"""
        return [a for a in self.agents.values() if a.agent_type == agent_type]
    
    def list_all_agents(self) -> List[Dict]:
        """List all agents"""
        return [agent.to_dict() for agent in self.agents.values()]
    
    def save(self):
        """Save registry to file"""
        try:
            registry_data = {
                agent_id: agent.to_dict() 
                for agent_id, agent in self.agents.items()
            }
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
            logger.info(f"Registry saved with {len(self.agents)} agents")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def load(self):
        """Load registry from file"""
        try:
            if self.registry_file.exists():
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)
                logger.info(f"Loaded {len(registry_data)} agents from file")
                return registry_data
            return {}
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {}
    
    def get_stats(self) -> Dict:
        """Get registry statistics"""
        benign_agents = self.get_agents_by_type(AgentType.BENIGN)
        malicious_agents = self.get_agents_by_type(AgentType.MALICIOUS)
        
        return {
            "total_agents": len(self.agents),
            "benign_agents": len(benign_agents),
            "malicious_agents": len(malicious_agents),
            "total_commits": sum(len(a.commits) for a in self.agents.values()),
            "avg_reputation": sum(a.reputation for a in self.agents.values()) / max(len(self.agents), 1)
        }
