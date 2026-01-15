import pytest
from src.agents.registry import AgentRegistry
from src.agents.base_agent import AgentType, AgentPhase

def test_benign_agent_creation():
    registry = AgentRegistry()
    agent = registry.create_benign_agent("TestAgent", "test@local")
    
    assert agent.name == "TestAgent"
    assert agent.agent_type == AgentType.BENIGN
    assert not agent.is_malicious

def test_malicious_agent_creation():
    registry = AgentRegistry()
    agent = registry.create_malicious_agent("AttackerAgent", "attacker@local")
    
    assert agent.name == "AttackerAgent"
    assert agent.agent_type == AgentType.MALICIOUS
    assert agent.is_malicious
    assert agent.phase == AgentPhase.INFILTRATION

def test_agent_registry():
    registry = AgentRegistry()
    
    # Create agents
    benign = registry.create_benign_agent("Benign1", "benign@local")
    malicious = registry.create_malicious_agent("Malicious1", "mal@local")
    
    # Test registry
    assert len(registry.agents) == 2
    assert registry.get_agent(benign.id) == benign
    
    # Test filtering
    benign_list = registry.get_agents_by_type(AgentType.BENIGN)
    assert len(benign_list) == 1
    
    # Test stats
    stats = registry.get_stats()
    assert stats['benign_agents'] == 1
    assert stats['malicious_agents'] == 1

def test_agent_commit_logging():
    registry = AgentRegistry()
    agent = registry.create_benign_agent("Dev1", "dev@local")
    
    # Log commit
    agent.log_commit("file.py", "abc1234", "feat: test", quality_score=0.8)
    
    assert len(agent.commits) == 1
    assert agent.tasks_completed == 1
    assert agent.code_quality == 0.8

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
