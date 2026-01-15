import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class GiteaClient:
    """Enhanced Gitea client with full operations"""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
    
    def authenticate(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/user",
                auth=(self.username, self.password),
                timeout=10
            )
            is_auth = response.status_code == 200
            if is_auth:
                logger.info(f"✓ Authenticated as {self.username}")
            return is_auth
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def create_repository(self, repo_name: str, description: str = "") -> Optional[Dict]:
        """Create a repository"""
        try:
            payload = {
                "name": repo_name,
                "description": description,
                "private": False,
                "auto_init": True
            }
            response = requests.post(
                f"{self.base_url}/api/v1/admin/users/{self.username}/repos",
                json=payload,
                auth=(self.username, self.password),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✓ Created repository: {repo_name}")
                return response.json()
            elif response.status_code == 422:
                logger.info(f"Repository already exists: {repo_name}")
                return self.get_repository(repo_name)
            else:
                logger.error(f"Failed to create repo: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return None
    
    def get_repository(self, repo_name: str) -> Optional[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}",
                auth=(self.username, self.password),
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            return None
    
    def get_commits(self, repo_name: str, limit: int = 50) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/commits",
                params={"limit": limit},
                auth=(self.username, self.password),
                timeout=10
            )
            if response.status_code == 200:
                commits = response.json()
                logger.info(f"Retrieved {len(commits)} commits from {repo_name}")
                return commits
            return []
        except Exception as e:
            logger.error(f"Error getting commits: {e}")
            return []
    
    def create_pull_request(self, repo_name: str, title: str, description: str, 
                          head_branch: str, base_branch: str = "main") -> Optional[Dict]:
        try:
            payload = {
                "title": title,
                "body": description,
                "head": head_branch,
                "base": base_branch
            }
            response = requests.post(
                f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls",
                json=payload,
                auth=(self.username, self.password),
                timeout=10
            )
            if response.status_code in [200, 201]:
                logger.info(f"✓ Created PR: {title}")
                return response.json()
            else:
                logger.error(f"Failed to create PR: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None
