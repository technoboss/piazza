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
[15-Nov-26] 4 tests files have been created to test the config, health and the db model. all tests passed
[15-Nov-26] Now, my code is ready to be pushed to GitHub repo (first commit)

### Registration and authentication

[16-Nov-26] Tackling users registration and authentication
[16-Nov-26] API endpoints creation in Routers folder
[16-Nov-26] Create a schema.py file to checks and cleans the data going into and out of the API using Pydantic
[16-Nov-26] Dates are not validated by SQLite. Therefore a DATE column could accept 'not a date' and an empty string. I added CHECK (datetime(...) IS NOT NULL) constraints. SQLite now also returns datetimes without a timezone, so the code has to compare against naive UTC time, or Python raises an error.
[16-Nov-26] Create a security.py file to hash password from plain text using pwdlib
[16-Nov-26] They was a bug in in my db_setup.sql. The table is named users, but had maned three foreign keys referenced user(user_id). With foreign keys on, inserting a post failed with no such table: main.user. It took a considerable amount of time to figure that out.
[16-Nov-26] Found out that SQLite ignores foreign keys by default. The PRAGMA foreign_keys = ON line in a setup file doesn’t carry over to the app, because the setting is per connection. The fix was an event listener in database.py that runs it on every new connection.
[16-Nov-26] the app/ package layout caused ModuleNotFoundError: No module named 'app' in pytest. The fix was a pytest.ini with pythonpath = . in the project root, and app.-prefixed imports everywhere.
[16-Nov-26] 24 tests carried and all passed

### Posts and topics

[17-Nov-26] I added a post_topic table in model.py to satisfy requirement post has one or more topics
[17-Nov-26] I've made the topic names fixed using constants.py & seed.py files. seed_topics inserts any topic that are missing because API has no endpoint to create topics, so without this a new post would fail. While main.py runs it at startup, after create_all, so the topics always exist and nobody can create new ones.
[17-Nov-26] I wrote the validation code in schemas.py. PostCreate defines what a client may send.
[17-Nov-26] I Built the endpoints routers/posts.py & routers/topics.py. All of these endpoint require a token through get_current_user.
[17-Nov-26] I set up the derived fields. to_post_out works out status (Expired when expires_at has passed, otherwise Live). It counts likes and dislikes from the reactions. Authors, topics, reactions and comments now loaded up front, so a list doesn’t run a query per post.
[17-Nov-26] I added a small helper in utils.py. utcnow() returns the current UTC time without timezone info, the same form SQLite gives back. Mixing aware and naive datetimes raises an error, so all comparisons use this one function.
[17-Nov-26] I updated the tests. conftest.py seeds the topics in the test database, because the startup code doesn’t run in tests, and adds a second logged-in user.
[17-Nov-26] 25 test carried and all passed
