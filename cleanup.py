"""
Delete local repo and remote repo, then restart fresh
"""

import subprocess
import os
import shutil
import time
import requests
from pathlib import Path
from config import Config

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_ok(msg): print(f"{GREEN}✓ {msg}{END}")
def print_err(msg): print(f"{RED}✗ {msg}{END}")
def print_warn(msg): print(f"{YELLOW}⚠ {msg}{END}")
def print_info(msg): print(f"{BLUE}ℹ {msg}{END}")

def cleanup_local_repo():
    """Delete local repo directory"""
    print_info("\n[1/3] Cleaning local repository...")
    
    repo_path = Path(Config.REPO_CLONE_PATH)
    
    if not repo_path.exists():
        print_ok("Local repo doesn't exist")
        return True
    
    try:
        # Try simple delete first
        shutil.rmtree(repo_path)
        print_ok(f"Deleted {repo_path}")
        return True
    except PermissionError:
        # Windows file locking - use chmod workaround
        print_warn("Files locked, using force delete...")
        
        import stat
        def handle_remove_readonly(func, path, exc):
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR | stat.S_IREAD)
                func(path)
            else:
                raise
        
        try:
            shutil.rmtree(repo_path, onerror=handle_remove_readonly)
            print_ok(f"Force deleted {repo_path}")
            return True
        except Exception as e:
            print_err(f"Failed to delete: {e}")
            return False
    except Exception as e:
        print_err(f"Error: {e}")
        return False

def cleanup_remote_repo():
    """Delete remote repo from Gitea"""
    print_info("\n[2/3] Cleaning remote repository...")
    
    try:
        # Authenticate as admin
        auth = (Config.GITEA_ADMIN_USER, Config.GITEA_ADMIN_PASSWORD)
        
        # Delete repo via API
        url = f"{Config.GITEA_URL}/api/v1/repos/{Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}"
        
        response = requests.delete(url, auth=auth, timeout=10)
        
        if response.status_code in (200, 204, 404):
            print_ok(f"Deleted remote repo: {Config.GITEA_REPO_NAME}")
            return True
        else:
            print_err(f"Failed to delete (HTTP {response.status_code})")
            print_warn(f"You may need to delete manually at:")
            print_warn(f"  {Config.GITEA_URL}/{Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}")
            return False
            
    except Exception as e:
        print_err(f"Error deleting remote: {e}")
        return False

def verify_cleanup():
    """Verify everything is cleaned"""
    print_info("\n[3/3] Verifying cleanup...")
    
    # Check local
    repo_path = Path(Config.REPO_CLONE_PATH)
    if repo_path.exists():
        print_err("Local repo still exists!")
        return False
    
    print_ok("Local repo deleted")
    
    # Check remote
    try:
        auth = (Config.GITEA_ADMIN_USER, Config.GITEA_ADMIN_PASSWORD)
        url = f"{Config.GITEA_URL}/api/v1/repos/{Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}"
        response = requests.get(url, auth=auth, timeout=5)
        
        if response.status_code == 404:
            print_ok("Remote repo deleted")
            return True
        else:
            print_warn(f"Remote repo still exists (HTTP {response.status_code})")
            return False
    except Exception as e:
        print_warn(f"Could not verify remote: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("CLEANUP & RESTART")
    print("="*70)
    
    print_info(f"Local path: {Config.REPO_CLONE_PATH}")
    print_info(f"Remote: {Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}")
    
    print("\nThis will delete:")
    print("  1. Local repository")
    print("  2. Remote repository on Gitea")
    print("\nYou can then run: python main.py")
    
    response = input("\nProceed? (yes/no): ").strip().lower()
    
    if response != "yes":
        print_warn("Cancelled")
        return 1
    
    # Do cleanup
    if not cleanup_local_repo():
        return 1
    
    if not cleanup_remote_repo():
        print_warn("Remote cleanup failed, but continuing...")
    
    # Verify
    if not verify_cleanup():
        print_warn("Cleanup incomplete")
    
    print("\n" + "="*70)
    print_ok("CLEANUP COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. python main.py  (will create fresh repo)")
    print("  2. Repos will be created from scratch")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
