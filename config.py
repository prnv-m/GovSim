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

    #==== GEMINI ====
    GEMINI_ENABLED = True
    GEMINI_API_KEYS = os.environ.get("GEMINI_API_KEYS").split(',')
    GEMINI_MODEL_NAME =  "gemini-3.1-flash-lite-preview" #"gemini-3-flash-preview" 
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent"
    GROQ_ENABLED = True
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"   # large: code gen + deep review
    GROQ_SMALL_MODEL_NAME = "moonshotai/kimi-k2-instruct"             # small: task gen + peer review (60 RPM, 10K TPM)
    CODE_GENERATION_TIMEOUT = 60   # code gen — large output, allow longer
    ANALYSIS_TIMEOUT = 15          # peer review / security analysis — small JSON, fail fast
    PEER_REVIEW_DELAY = 2          # seconds between peer review calls (rate-limit guard)
    CODE_STYLE_DIVERSITY = True
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
    BENIGN_AGENT_COUNT = 3
    SYBIL_AGENT_COUNT = 2
    MALICIOUS_AGENT_COUNT = 1
    MAX_ROUNDS = 25
    PR_MAX_PENDING_ROUNDS = 2   # Auto-close PENDING PRs after this many rounds
    PR_DIFF_MAX_CHARS = 8000    # Truncate diffs before sending to LLM peer review
    
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
