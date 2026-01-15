import subprocess
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class RepositoryManager:
    """Manage local repository operations"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def clone(self, repo_url: str, force: bool = True) -> bool:
        """Clone a repository"""
        try:
            if self.repo_path.exists() and force:
                import shutil
                shutil.rmtree(self.repo_path)
            
            result = subprocess.run(
                ["git", "clone", repo_url, str(self.repo_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Cloned repository to {self.repo_path}")
                return True
            else:
                logger.error(f"Clone failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error cloning: {e}")
            return False
    
    def configure(self, user_name: str, user_email: str) -> bool:
        """Configure git user"""
        try:
            os.chdir(self.repo_path)
            
            subprocess.run(["git", "config", "user.name", user_name], 
                         capture_output=True, timeout=10)
            subprocess.run(["git", "config", "user.email", user_email], 
                         capture_output=True, timeout=10)
            
            logger.info(f"✓ Git configured for {user_name}")
            return True
        except Exception as e:
            logger.error(f"Error configuring git: {e}")
            return False
    
    def create_file(self, filename: str, content: str) -> bool:
        """Create a file in repo"""
        try:
            file_path = self.repo_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            logger.info(f"✓ Created file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error creating file: {e}")
            return False
    
    def commit(self, file_path: str, message: str) -> Optional[str]:
        """Make a commit"""
        try:
            os.chdir(self.repo_path)
            
            subprocess.run(["git", "add", file_path], 
                         capture_output=True, timeout=10)
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commit_hash = hash_result.stdout.strip()[:8]
                logger.info(f"✓ Committed: {message} ({commit_hash})")
                return commit_hash
            else:
                logger.error(f"Commit failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error committing: {e}")
            return None
    
    def push(self, branch: str = "main") -> bool:
        """Push to remote"""
        try:
            os.chdir(self.repo_path)
            
            result = subprocess.run(
                ["git", "push", "origin", branch],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Pushed to origin/{branch}")
                return True
            else:
                logger.warning(f"Push had issues: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error pushing: {e}")
            return False
    
    def get_commits(self) -> list:
        """Get recent commits"""
        try:
            os.chdir(self.repo_path)
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
            return []
        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []
