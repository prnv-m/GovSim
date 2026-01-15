"""
Test Gitea admin credentials
"""
import requests

GITEA_URL = "http://localhost:3001"

# Common Gitea admin credentials to try
credentials_to_try = [
    ("gitea_admin", "gitea_admin"),
    ("admin", "admin"),
    ("root", "root"),
    ("root", "password"),
    ("gitea", "gitea"),
]

print("Testing Gitea admin credentials...\n")

for username, password in credentials_to_try:
    try:
        response = requests.get(
            f"{GITEA_URL}/api/v1/user",
            auth=(username, password),
            timeout=5
        )
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✓ SUCCESS: {username}:{password}")
            print(f"  User: {user_data.get('login')}")
            print(f"  Email: {user_data.get('email')}")
            print(f"  IS_ADMIN: {user_data.get('is_admin')}\n")
        elif response.status_code == 401:
            print(f"✗ {username}:{password} - 401 Unauthorized")
        else:
            print(f"✗ {username}:{password} - Status {response.status_code}")
            
    except Exception as e:
        print(f"✗ {username}:{password} - Error: {e}")

print("\n" + "="*70)
print("If you found working credentials, update config.py:")
print("  GITEA_ADMIN_USER = 'your_username'")
print("  GITEA_ADMIN_PASSWORD = 'your_password'")
print("="*70)
