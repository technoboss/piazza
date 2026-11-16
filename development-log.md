# PIAZZA APP PROJECT

---

### Initial setup

[08-Nov-26] Started by setting up my development environmment
[08-Nov-26] Created and activated my python virtual environment
[08-Nov-26] Added a requirements.txt file to list all my python package
[08-Nov-26] Created a public repo on Github on my personal account
[08-Nov-26] Added a .gitignore file
[08-Nov-26] Created and starded to fill my README.md file
[08-Nov-26] Design project structure by defining the main folders and files
[15-Nov-26] First will define & Install requirements.txt
[08-Nov-26] The Package installed in my .venv:

    - fastapi: Python web framework used for building APIs
    - uvicorn: Python Asynchronous Server Gateway Interface web server
    - sqlalchemy: Python SQL toolkit and Object Relational Mapper
    - pwdlib: a python library for hashing and verification.
    - pyJWT: Python library used to encode and decode JSON Web Tokens (JWT)

[08-Nov-26] First commit and push in GitHub

### Foundation and database configuration

[15-Nov-26] Decided to use a Bottom Up development approch
[15-Nov-26] Let's design the app ERD and configure the db
[15-Nov-26] The DB schema is now defined in the db_setup.sql file
[15-Nov-26] I need to create a config.py file to use pydantic-settings to read the app environment variables.
[15-Nov-26] A database.py setup will be used to prepare the db connection for the authentication API.
[15-Nov-26] Now the db model for table (User, Topic, Post, Comment, Reaction) creation is defined in the app/models.py file
[15-Nov-26] Let's create a skeleton main.py file to see the tables creation at start-up in action
[15-Nov-26] 4 tests files have been created to test the config, health and the db model.
[15-Nov-26] Now, my code is ready to be pushed to GitHub repo

### Registration and authentication

[16-Nov-26] Tackling users registration and authentication
[16-Nov-26] API endpoints creation in Routers folder
[16-Nov-26] Create a schema.py file to checks and cleans the data going into and out of the API using Pydantic
[16-Nov-26] Create a security.py file to hash password from plain text using pwdlib
[16-Nov-26] Requirements satisfied:

- - Unique email address
- - Email and password required, valid
- - Store password hashes, never plaintext
- - Don’t expose hashes or secrets in responses
- - Login returning an expiring JWT, and rejecting a wrong password.
- - A bearer token required on the business endpoints.
- - Rejecting missing, invalid and expired tokens.
