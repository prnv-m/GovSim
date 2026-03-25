import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class GiteaClient:
    """Enhanced Gitea client with full PR support"""
    
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
            elif response.status_code in [409, 422] or "already exists" in response.text:
                logger.info(f"Repository '{repo_name}' already exists — reusing.")
                return self.get_repository(repo_name)
            else:
                logger.error(f"Failed to create repo: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            return None
    
    def delete_repository(self, repo_name: str) -> bool:
        """Delete a repository (used to reset state between simulation runs)."""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}",
                auth=(self.username, self.password),
                timeout=10
            )
            if response.status_code in [204, 404]:
                logger.info(f"✓ Deleted (or absent) repository: {repo_name}")
                return True
            logger.warning(f"Could not delete repo (HTTP {response.status_code}): {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error deleting repository: {e}")
            return False

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

    def add_collaborator(self, repo_name: str, username: str, permission: str = "write") -> bool:
        """Add a user as a collaborator with specific permissions"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/collaborators/{username}"
            data = {"permission": permission}
            
            response = requests.put(
                url, 
                json=data,
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # 204 means success (No Content)
            if response.status_code == 204:
                return True
            else:
                logger.warning(f"Failed to add collaborator {username}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error adding collaborator: {e}")
            return False

    # ================= NEW METHODS FOR PR WORKFLOW =================

    def create_branch(self, repo_name: str, branch_name: str, base_branch: str = "main") -> bool:
        """Create a branch via API"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/branches"
            payload = {
                "new_branch_name": branch_name,
                "old_branch_name": base_branch
            }
            response = requests.post(
                url, json=payload, auth=(self.username, self.password)
            )
            return response.status_code in [201, 409] # 409 = exists
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return False

    def create_pull_request(self, repo_name: str, title: str, body: str, head: str, base: str = "main") -> Optional[Dict]:
        """
        Create a Pull Request
        Note: Arguments match Orchestrator call (body, head, base)
        """
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls"
            payload = {
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
            response = requests.post(
                url, json=payload, auth=(self.username, self.password)
            )
            if response.status_code == 201:
                logger.info(f"✓ Created PR: {title}")
                return response.json()
            else:
                logger.error(f"Failed to create PR: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None

    def get_pull_requests(self, repo_name: str, state: str = 'open') -> List[Dict]:
        """List pull requests"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls"
            params = {"state": state}
            response = requests.get(
                url, params=params, auth=(self.username, self.password)
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting PRs: {e}")
            return []

    def get_pull_request_diff(self, repo_name: str, pr_index: int) -> str:
        """Get the diff content of a PR"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls/{pr_index}.diff"
            response = requests.get(url, auth=(self.username, self.password))
            if response.status_code == 200:
                return response.text
            return ""
        except Exception as e:
            logger.error(f"Error getting diff: {e}")
            return ""
    def create_issue_comment(self, repo_name: str, issue_index: int, body: str) -> bool:
            """Add a comment to an issue or pull request"""
            try:
                url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/issues/{issue_index}/comments"
                payload = {"body": body}
                response = requests.post(
                    url, json=payload, auth=(self.username, self.password), timeout=10
                )
                if response.status_code == 201:
                    return True
                else:
                    logger.warning(f"Failed to add comment to PR #{issue_index}: {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error adding comment: {e}")
                return False
    def merge_pull_request(self, repo_name: str, pr_index: int) -> bool:
        """Merge a PR"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls/{pr_index}/merge"
            payload = {
                "Do": "merge",
                "MergeMessageField": "Merged by Governance System",
                "delete_branch_after_merge": True
            }
            response = requests.post(
                url, json=payload, auth=(self.username, self.password)
            )
            if response.status_code == 200:
                logger.info(f"✓ Merged PR #{pr_index}")
                return True
            else:
                logger.error(f"Failed to merge PR #{pr_index}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error merging PR: {e}")
            return False

    def close_pull_request(self, repo_name: str, pr_index: int) -> bool:
        """Close a PR without merging"""
        try:
            url = f"{self.base_url}/api/v1/repos/{self.username}/{repo_name}/pulls/{pr_index}"
            payload = {"state": "closed"}
            response = requests.patch(
                url, json=payload, auth=(self.username, self.password)
            )
            if response.status_code == 200:
                logger.info(f"✓ Closed PR #{pr_index}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error closing PR: {e}")
            return False