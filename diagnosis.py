"""
Diagnose git push authentication issues
"""

import subprocess
import os
from pathlib import Path
from config import Config

# Colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
END = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{END}")
    print(f"{BLUE}{text}{END}")
    print(f"{BLUE}{'='*70}{END}\n")

def print_ok(text):
    print(f"{GREEN}✓ {text}{END}")

def print_error(text):
    print(f"{RED}✗ {text}{END}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{END}")

def print_info(text):
    print(f"{BLUE}ℹ {text}{END}")

def run_cmd(cmd, cwd=None):
    """Run command and return result"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

# Test 1: Check repo exists and is cloned
print_header("TEST 1: Repository Status")

repo_path = Path(Config.REPO_CLONE_PATH)

if not repo_path.exists():
    print_error(f"Repository not cloned: {repo_path}")
    print_info("Run: python main.py (to clone)")
else:
    print_ok(f"Repository exists: {repo_path}")
    
    # Check if it's a git repo
    git_dir = repo_path / ".git"
    if git_dir.exists():
        print_ok(f"Valid git repository")
    else:
        print_error(f"Not a valid git repository")

# Test 2: Check git remote
print_header("TEST 2: Git Remote Configuration")

code, stdout, stderr = run_cmd("git remote -v", cwd=repo_path)

if code == 0:
    print_ok("Git remotes:")
    for line in stdout.strip().split('\n'):
        if line:
            print_info(f"  {line}")
else:
    print_error(f"Cannot check remotes: {stderr}")

# Test 3: Check git config credentials
print_header("TEST 3: Git Credentials Configuration")

# Check global config
code, stdout, stderr = run_cmd("git config --global user.name")
if code == 0:
    print_info(f"Global user.name: {stdout.strip()}")
else:
    print_warning(f"No global user.name set")

code, stdout, stderr = run_cmd("git config --global user.email")
if code == 0:
    print_info(f"Global user.email: {stdout.strip()}")
else:
    print_warning(f"No global user.email set")

# Check repo-specific config
code, stdout, stderr = run_cmd("git config user.name", cwd=repo_path)
if code == 0:
    print_info(f"Repo user.name: {stdout.strip()}")

code, stdout, stderr = run_cmd("git config user.email", cwd=repo_path)
if code == 0:
    print_info(f"Repo user.email: {stdout.strip()}")

# Test 4: Test authentication directly
print_header("TEST 4: Test Gitea Authentication")

print_info(f"Testing credentials: {Config.GITEA_MAIN_USER}:{Config.GITEA_MAIN_PASSWORD}")

# Test with curl
cmd = f'curl -u {Config.GITEA_MAIN_USER}:{Config.GITEA_MAIN_PASSWORD} -s -o /dev/null -w "%{{http_code}}" {Config.GITEA_URL}/api/v1/user'
code, stdout, stderr = run_cmd(cmd)

if "200" in stdout:
    print_ok(f"Authentication successful (HTTP 200)")
elif "401" in stdout:
    print_error(f"Authentication failed (HTTP 401)")
    print_warning(f"Check credentials: {Config.GITEA_MAIN_USER}")
else:
    print_warning(f"HTTP Response: {stdout}")

# Test 5: Check if repo exists on Gitea
print_header("TEST 5: Check Repository on Gitea")

cmd = f'curl -u {Config.GITEA_MAIN_USER}:{Config.GITEA_MAIN_PASSWORD} -s {Config.GITEA_URL}/api/v1/repos/{Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}'
code, stdout, stderr = run_cmd(cmd)

if "full_name" in stdout:
    print_ok(f"Repository exists on Gitea")
    print_info(f"  Name: {Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}")
elif "404" in stdout or "not found" in stdout.lower():
    print_error(f"Repository not found on Gitea")
    print_warning(f"Need to create: {Config.GITEA_MAIN_USER}/{Config.GITEA_REPO_NAME}")
else:
    print_warning(f"Cannot determine repo status")

# Test 6: Test git push directly
print_header("TEST 6: Test Direct Git Push")

if repo_path.exists():
    print_info("Checking if there are unpushed commits...")
    
    code, stdout, stderr = run_cmd("git log origin/main..HEAD --oneline", cwd=repo_path)
    
    if code == 0:
        if stdout.strip():
            unpushed = len(stdout.strip().split('\n'))
            print_warning(f"Found {unpushed} unpushed commits")
            print_info(f"Attempting test push...")
            
            code, stdout, stderr = run_cmd(
                f"git push -u origin main",
                cwd=repo_path
            )
            
            if code == 0:
                print_ok(f"Push successful!")
            else:
                print_error(f"Push failed:")
                if stderr:
                    print_warning(f"  Error: {stderr}")
        else:
            print_ok(f"All commits already pushed")
    else:
        print_info(f"Cannot determine unpushed commits")

# Test 7: Check git credential helper
print_header("TEST 7: Git Credential Helper")

code, stdout, stderr = run_cmd("git config credential.helper")

if stdout.strip():
    print_info(f"Credential helper: {stdout.strip()}")
else:
    print_warning(f"No credential helper configured")
    print_info(f"Add one with: git config --global credential.helper store")

# Test 8: Check auth method
print_header("TEST 8: Authentication Method Analysis")

print_info("Your setup uses:")
print_info(f"  URL: {Config.GITEA_REPO_URL}")
print_info(f"  Auth Type: HTTP Basic Auth (username:password in URL)")

if "http://" in Config.GITEA_REPO_URL:
    print_warning(f"Using HTTP (not HTTPS)")
    print_info(f"  This is fine for local development")

# Summary & Solutions
print_header("SUMMARY & SOLUTIONS")

print_info("Common causes of 'Authentication failed':")
print_info("  1. Git credential helper not configured")
print_info("  2. Credentials cached from previous runs")
print_info("  3. User doesn't have push permission")
print_info("  4. Repository doesn't exist yet")
print_info("  5. Network/timeout issues during push")

print_info("\nQuick fixes:")
print_info("  1. Set git credentials:")
print_info(f"     git config --global user.name '{Config.GITEA_MAIN_USER}'")
print_info(f"     git config --global user.email 'user@local.local'")

print_info("\n  2. Store credentials:")
print_info("     git config --global credential.helper store")

print_info("\n  3. Manual test push:")
print_info(f"     cd {Config.REPO_CLONE_PATH}")
print_info(f"     git push origin main")

print_info("\n  4. If push still fails, check logs:")
print_info(f"     docker logs gitea | tail -20")

print("\n")
