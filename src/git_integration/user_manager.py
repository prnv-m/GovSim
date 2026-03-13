import requests
import logging
from typing import Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class UserManager:
    """Manage Gitea user accounts for agents"""
    
    def __init__(self, gitea_url: str, admin_user: str, admin_password: str):
        self.gitea_url = gitea_url.rstrip('/')
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.created_users = {}
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists"""
        try:
            response = requests.get(
                f"{self.gitea_url}/api/v1/users/{username}",
                auth=(self.admin_user, self.admin_password),
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error checking user: {e}")
            return False
    def _force_password_reset_off(self, username: str):
        """Helper: Explicitly tell Gitea to disable password change requirement"""
        try:
            url = f"{self.gitea_url}/api/v1/admin/users/{username}"
            payload = {
                "must_change_password": False,
                "active": True,
                "login_name": username
            }
            response = requests.patch(
                url,
                json=payload,
                auth=(self.admin_user, self.admin_password),
                timeout=10
            )
            if response.status_code == 200:
                logger.info(f"  ✓ Fixed password policy for {username}")
            else:
                logger.warning(f"Could not fix password policy: {response.text}")
        except Exception as e:
            logger.error(f"Error forcing password policy: {e}")
    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create a Gitea user account"""
        try:
            # 1. If user exists, just ensure settings are correct and return
            if self.user_exists(username):
                logger.info(f"User already exists: {username}")
                # FORCE FIX even for existing users
                self._force_password_reset_off(username) 
                
                self.created_users[username] = {
                    "username": username,
                    "email": email,
                    "password": password
                }
                return True
            
            # 2. Create new user
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "full_name": username,
                "login_name": username,
                "must_change_password": False
            }
            
            response = requests.post(
                f"{self.gitea_url}/api/v1/admin/users",
                json=payload,
                auth=(self.admin_user, self.admin_password),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✓ Created user: {username}")
                # FORCE FIX (Double check)
                self._force_password_reset_off(username)
                
                self.created_users[username] = {
                    "username": username,
                    "email": email,
                    "password": password
                }
                return True
            else:
                logger.error(f"Failed to create user: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def create_agent_user(self, agent_name: str, agent_email: str) -> Optional[Dict]:
        """Create user account for an agent"""
        username = agent_name.lower().replace(" ", "_")
        password = f"{username}_secure_2026"
        
        if self.create_user(username, agent_email, password):
            return {
                "username": username,
                "email": agent_email,
                "password": password
            }
        return None
    
    def get_user_credentials(self, username: str) -> Optional[Dict]:
        """Get credentials for a user"""
        return self.created_users.get(username)
    
    def list_created_users(self) -> Dict:
        """List all created users"""
        return self.created_users