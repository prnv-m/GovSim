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
        self.current_user = None  # NEW: Track current user
    
    def clone(self, repo_url: str, force: bool = True, agent_username: str = None) -> bool:
        """Clone a repository
        
        Args:
            repo_url: Repository URL
            force: Force re-clone if exists
            agent_username: Username to embed in URL (for multi-account)
        """
        try:
            if self.repo_path.exists() and force:
                import shutil
                shutil.rmtree(self.repo_path)
            
            # If agent username provided, modify URL to include credentials
            if agent_username:
                # Extract domain and path from URL
                # http://localhost:3000/demo/govim-main.git
                # -> http://agent1:password@localhost:3000/demo/govim-main.git
                logger.info(f"Clone will use credentials for: {agent_username}")
            
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
            
            # NEW: Also set as current user for tracking
            self.current_user = user_name
            
            logger.info(f"✓ Git configured for {user_name}")
            return True
        except Exception as e:
            logger.error(f"Error configuring git: {e}")
            return False
    
    def push(self, branch: str = "main", username: str = None, password: str = None) -> bool:
        """Push to remote with agent credentials using URL injection"""
        try:
            os.chdir(self.repo_path)
            
            # Default push command
            push_cmd = ["git", "push", "origin", branch]
            
            # If credentials provided, inject them securely into the URL
            if username and password:
                # 1. Get the current remote URL
                remote_url_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if remote_url_result.returncode == 0:
                    base_url = remote_url_result.stdout.strip()
                    
                    # 2. Inject credentials: http://user:pass@host/repo.git
                    if "://" in base_url:
                        scheme, rest = base_url.split("://", 1)
                        # Remove existing auth if present in the remote config
                        if "@" in rest:
                            rest = rest.split("@", 1)[1]
                        
                        # Construct URL with credentials
                        authenticated_url = f"{scheme}://{username}:{password}@{rest}"
                        
                        # Use this specific URL for this specific push command
                        push_cmd = ["git", "push", authenticated_url, branch]

            # 3. Execute push
            result = subprocess.run(
                push_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                user_label = username if username else self.current_user
                logger.info(f"✓ Pushed to origin/{branch} by {user_label}")
                return True
            else:
                # Mask password in logs if it failed
                error_msg = result.stderr
                if password:
                    error_msg = error_msg.replace(password, "*****")
                logger.warning(f"Push had issues: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error pushing: {e}")
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
    def commit(self, file_path: str, message: str, author: dict = None) -> Optional[str]:
        """
        Make a commit with optional author attribution
        
        Args:
            file_path: Path to file to commit
            message: Commit message
            author: Dict with 'name' and 'email' keys (optional)
        
        Returns:
            Commit hash (first 8 chars) or None if failed
        """
        try:
            os.chdir(self.repo_path)
            
            # Stage the file
            subprocess.run(
                ["git", "add", file_path], 
                capture_output=True, 
                timeout=10
            )
            
            # Build commit command
            git_cmd = ["git", "commit", "-m", message]
            
            # Add author if provided
            if author:
                author_name = author.get('name', 'Unknown Agent')
                author_email = author.get('email', f'{author_name}@govim.local')
                git_cmd.extend([
                    "--author",
                    f"{author_name} <{author_email}>"
                ])
            
            # Make the commit
            result = subprocess.run(
                git_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commit_hash = hash_result.stdout.strip()[:8]
                
                # Log with author info
                author_str = f" by {author.get('name', 'Unknown')}" if author else ""
                logger.info(f"✓ Committed: {message}{author_str} ({commit_hash})")
                return commit_hash
            else:
                logger.error(f"Commit failed: {result.stderr}")
                return None
                
        except Exception as e:  
            logger.error(f"Error committing: {e}")
            return None

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
