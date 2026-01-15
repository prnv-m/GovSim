import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    PROJECT_ROOT = Path(__file__).parent
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = DATA_DIR / "logs"
    RESULTS_DIR = DATA_DIR / "results"
    REPO_CLONE_PATH = "/tmp/govim-repo"
    
    # Gitea
    GITEA_URL = os.getenv("GITEA_URL", "http://localhost:3001")
    GITEA_USER = os.getenv("GITEA_USER", "demo")
    GITEA_PASSWORD = os.getenv("GITEA_PASSWORD", "demo1234")
    GITEA_REPO_NAME = "govim-main"
    GITEA_REPO_URL = f"{GITEA_URL}/{GITEA_USER}/{GITEA_REPO_NAME}.git"
    
    # Agents
    BENIGN_AGENT_COUNT = 2
    MALICIOUS_AGENT_COUNT = 1
    MAX_ROUNDS = 25
    
    # Logging
    LOG_LEVEL = "INFO"
    
    @classmethod
    def init_directories(cls):
        for path in [cls.DATA_DIR, cls.LOGS_DIR, cls.RESULTS_DIR]:
            path.mkdir(exist_ok=True, parents=True)

Config.init_directories()
