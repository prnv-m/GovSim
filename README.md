## 1. Start Gitea (Docker)

```
docker run -d \
  --name gitea \
  -p 3001:3000 \
  -p 222:22 \
  -e GITEA_ADMIN_USER=gitea_admin \
  -e GITEA_ADMIN_PASSWORD=gitea_admin \
  -e GITEA_ADMIN_EMAIL=admin@govsim.local \
  -v gitea_data:/data \
  gitea/gitea:latest
```

Gitea UI:
[http://localhost:3001](http://localhost:3001)
Login: `gitea_admin / gitea_admin`

---

## 2. Environment Variables

```
GITEA_URL=http://localhost:3001
GITEA_ADMIN_USER=gitea_admin
GITEA_ADMIN_PASSWORD=gitea_admin
GITEA_MAIN_USER=demo
GITEA_MAIN_PASSWORD=demo
```

---

## 3. Run the Project

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 4. Run Tests

```
pytest tests/test_agent.py
```

---

That is it.
