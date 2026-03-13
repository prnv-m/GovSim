"""
Dynamic Task Manager for GOVIM
Generates projects using LLM and manages feature assignments
"""

import logging
import random
from src.llm_client import CodeGenerator

logger = logging.getLogger("govim")

class Task:
    """Represents a project task with a list of technical features"""
    def __init__(self, name: str, description: str, features: list, difficulty: str):
        self.name = name
        self.description = description
        self.difficulty = difficulty
        self.features = features  # List of {'name': '...', 'description': '...'}

class FeatureAssignment:
    """Manages the mapping of which agent is assigned to which feature"""
    def __init__(self):
        self.assignments = {}  # agent_name -> list of feature dicts
    
    def assign_feature(self, agent_name: str, feature: dict):
        if agent_name not in self.assignments:
            self.assignments[agent_name] = []
        
        # Ensure the feature has a 'completed' flag for the orchestrator loop
        if 'completed' not in feature:
            feature['completed'] = False
            
        self.assignments[agent_name].append(feature)

    def get_agent_features(self, agent_name: str) -> list:
        return self.assignments.get(agent_name, [])
    
    def get_next_feature(self, agent_name: str) -> dict:
        """Finds the first feature for an agent that hasn't been finished yet"""
        for feature in self.get_agent_features(agent_name):
            if not feature.get('completed', False):
                return feature
        return None

class DynamicTaskManager:
    """Uses LLM to generate realistic project backlogs on the fly"""
    
    def __init__(self):
        self.generator = CodeGenerator()
        self.themes = [
            "Decentralized Finance (DeFi) Exchange",
            "Medical Patient Monitoring IoT System",
            "Autonomous Logistics Drone Fleet",
            "Secure Government E-Voting Portal",
            "Smart Grid Energy Management",
            "Supply Chain Provenance Tracker"
        ]

    def generate_project(self, theme: str = "random") -> Task:
        """Query LLM to create a project name, description, and 10+ features"""
        if theme == "random":
            theme = random.choice(self.themes)

        logger.info(f"PM Agent: Designing new project based on theme: {theme}...")
        
        prompt = (
            f"Generate a technical software project plan for a '{theme}'.\n"
            "Provide 10-12 specific, granular technical features.\n"
            "Return ONLY a JSON object with this structure:\n"
            "{\n"
            '  "project_name": "string",\n'
            '  "description": "string",\n'
            '  "features": [\n'
            '    {"name": "short_snake_case_name", "description": "detailed technical requirement"}\n'
            '  ]\n'
            "}"
        )
        
        # Use our existing Fallback Router
        data = self.generator.analyze_code(prompt, analysis_type="project_design")
        
        if not data or 'features' not in data:
            logger.error("Failed to generate dynamic project. Using Fallback E-Voting.")
            return self._get_fallback_project()

        return Task(
            name=data.get('project_name', theme),
            description=data.get('description', ''),
            features=data.get('features', []),
            difficulty="HARD"
        )

    def _get_fallback_project(self) -> Task:
        """Hardcoded safety net in case of API failure"""
        return Task(
            name="E-Voting System",
            description="Secure electronic voting platform",
            difficulty="HARD",
            features=[
                {"name": "user_auth", "description": "User registration & authentication"},
                {"name": "ballot_encryption", "description": "Encrypt ballots"},
                {"name": "vote_counting", "description": "Count votes securely"},
                {"name": "audit_logging", "description": "Log all actions"},
                {"name": "admin_dashboard", "description": "Admin interface"}
            ]
        )

def create_assignment(task: Task, agents: list) -> FeatureAssignment:
    """
    Distributes features from a Task object across a list of Agent objects.
    """
    assignment = FeatureAssignment()
    
    # Simple round-robin distribution
    for i, feature in enumerate(task.features):
        agent = agents[i % len(agents)]
        assignment.assign_feature(agent.name, feature)
        
    return assignment

def print_assignment(task: Task, assignment: FeatureAssignment):
    """Prints the project plan to the console"""
    print(f"\n[PROJECT PLAN] {task.name}")
    print(f"Description: {task.description}")
    print("-" * 60)
    
    for agent_name, features in assignment.assignments.items():
        print(f"\n{agent_name}:")
        for f in features:
            print(f"  • {f['name']}: {f['description']}")