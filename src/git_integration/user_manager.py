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
    
    def create_user(self, username: str, email: str, password: str) -> bool:
        """Create a Gitea user account"""
        try:
            # Check if already exists
            if self.user_exists(username):
                logger.info(f"User already exists: {username}")
                self.created_users[username] = {
                    "username": username,
                    "email": email,
                    "password": password
                }
                return True
            
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
