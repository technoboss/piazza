# Piazza discussion app

---

### 1. Short description

Piazza is a discussion platform where registered users publish posts by topic, react and comment. Expired posts remain readable but accept no further interactions.

### 2. Technologies used

- Python and FastAPI.
- Pydantic for validation.
- SQLAlchemy and SQLite for data storage.
- JWT bearer authentication.
- pytest and FastAPI `TestClient`.
- Docker and Docker Hub.
- Google Cloud and Kubernetes.

### 3. Prerequisites

#### To develop and test locally

- Python 3.12 or newer (check with `python --version`)
- pip and `venv` (included with Python)
- Git, and a GitHub account to host the repository
- A code editor, such as VS Code
- Python packages, installed with `pip install -r requirements.txt`:
  - fastapi, uvicorn
  - sqlalchemy
  - pydantic-settings
  - pyjwt, pwdlib (password hashing)
  - pytest, httpx, pytest-cov
- SQLite is ships with Python or can be install globally on the host.

#### Configuration

- A `.env` file created from `.env.example`, with your a `SECRET_KEY`

#### To containerise

- Docker Desktop (check with `docker --version`)
- A Docker Hub account, to push the image

#### To deploy on Google Kubernetes Engine

- A Google Cloud account with billing enabled, and a project
- Google Cloud CLI (`gcloud`), signed in with `gcloud auth login`
- `kubectl` and the GKE auth plugin (`gcloud components install kubectl gke-gcloud-auth-plugin`)
- The Kubernetes Engine API enabled on the project

#### Background knowledge

- Basic Python, REST APIs and SQL
- The command line

### 4. Project File Structure

```text
piazza/
├── app/
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── posts.py
│   ├── config.py
│   ├── database.py
│   ├── piazza.db
│   ├── main.py
│   ├── models.py
│   ├── profile.py
│   ├── schemas.py
│   ├── security.py
│   └── services.py
|
├── tests/
│   └── conftest.py
├── Dockerfile
├── development-log.md
├── .env.example
├── README.md
├── requirements.txt
└── setup.sql
```

### 5. Commands to install dependencies.

- python -m pip install -r requirements.txt

### 6. Commands to create the DB tables

- SQLAlchemy reads models.py and builds the tables the async def lifespan(app: FastAPI) function at start-up in the main.py file
- db_setup.sql file is not involve in the table creation it serves as db schema documentation

### 7. Run all the tests

- pytest -v

### 8. Required configuration variables

- Find them in the .env.example files

### 9. SQLite database location

- app/piazza.db

### 10. Commands to run the application locally

- uvicorn app.main:app --reload

### 11. API documentation access.

- http://127.0.0.1:8000/docs

### 13. Docker build/run instructions

[the versioned Docker Hub image reference]

### 14. Kubernetes deployment and cleanup instructions.
