import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ===== PATHS =====
    PROJECT_ROOT = Path(__file__).parent
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = DATA_DIR / "logs"
    RESULTS_DIR = DATA_DIR / "results"
    
    # Windows-friendly repo path
    REPO_CLONE_PATH = str(PROJECT_ROOT / "local_repo")
    
    # ===== GITEA CONFIGURATION =====
    GITEA_URL = os.getenv("GITEA_URL", "http://localhost:3001")
    GITEA_ADMIN_USER = os.getenv("GITEA_ADMIN_USER", "gitea_admin")
    GITEA_ADMIN_PASSWORD = os.getenv("GITEA_ADMIN_PASSWORD", "gitea_admin")
    GITEA_MAIN_USER = os.getenv("GITEA_MAIN_USER", "demo")
    GITEA_MAIN_PASSWORD = os.getenv("GITEA_MAIN_PASSWORD", "demo")
    
    # Repository configuration
    GITEA_REPO_NAME = "govim-main"
    GITEA_REPO_URL = f"{GITEA_URL}/{GITEA_MAIN_USER}/{GITEA_REPO_NAME}.git"
    
    # ===== AGENT CONFIGURATION =====
    BENIGN_AGENT_COUNT = 2
    MALICIOUS_AGENT_COUNT = 1
    MAX_ROUNDS = 25
    
    # ===== LOGGING =====
    LOG_LEVEL = "INFO"
    
    # ===== INITIALIZATION =====
    @classmethod
    def init_directories(cls):
        """Create necessary directories"""
        for path in [cls.DATA_DIR, cls.LOGS_DIR, cls.RESULTS_DIR]:
            path.mkdir(exist_ok=True, parents=True)

# Initialize on import
Config.init_directories()
