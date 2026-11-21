# PIAZZA APP PROJECT

---

### Initial setup

[08-Nov-26] Started by setting up my development environmment
[08-Nov-26] Created and activated my python virtual environment
[08-Nov-26] Added a requirements.txt file
[08-Nov-26] Created a public repo on Github on my personal account
[08-Nov-26] Added a .gitignore file
[08-Nov-26] Created and starded to fill my README.md file
[08-Nov-26] Design project structure by defining the main folders and files
[08-Nov-26] Defined & Install requirements.txt
[08-Nov-26] First commit and push in GitHub

### Foundation and database configuration

[15-Nov-26] Decided to use a Bottom Up development approch
[15-Nov-26] Let's design the app ERD and configure the db
[15-Nov-26] The DB schema is now defined in the db_setup.sql file
[15-Nov-26] I created a config.py file to use pydantic-settings to read the app environment variables.
[15-Nov-26] Create a database.py to setup the db connection for the authentication API.
[15-Nov-26] added a listener in database.py that switches on SQLite foreign keys for every new connection
[15-Nov-26] Now the db model for table (User, Topic, Post, Comment, Reaction) creation is defined in the app/models.py file
[15-Nov-26] I created a lifespan function in main.py file to create the tables when the app starts
[15-Nov-26] I added a simple health route and set up pytest with an in-memory test database
[15-Nov-26] I wrote 4 tests (health route, creating a post, the foreign key rule and the expiry CHECK rule). all tests passed
[15-Nov-26] Now, my code is ready to be pushed to GitHub repo (first commit)

### Registration and authentication

[16-Nov-26] Now moving on to users registration and authentication module.
[16-Nov-26] I built POST /auth/register. It checks the input with Pydantic, hashes the password with argon2 and refuses duplicate emails and usernames.
[16-Nov-26] I built POST /auth/login. It accepts the email or the username and returns a JWT that expires after 60 minutes.
[16-Nov-25] I built the get_current_user dependency in deps.py. It reads the bearer token and returns 401 for a missing, invalid, expired or forged token.
[16-Nov-25] I added GET /auth/me so a token can be tested by hand.
[16-Nov-25] I moved settings into config.py, which reads SECRET_KEY and the token settings from the .env file.
[16-Nov-26] I Created a schema.py file to checks and cleans the data going into and out of the API using Pydantic
[16-Nov-26] Create a security.py file to hash password from plain text using pwdlib
[16-Nov-26] Challenge: They was a bug in in my db_setup.sql. The table is named users, but had maned three foreign keys referenced user(user_id). With foreign keys on, inserting a post failed with no such table: main.user. It took a considerable amount of time to figure that out.
[16-Nov-26] Challenge: Found out that SQLite ignores foreign keys by default. The PRAGMA foreign_keys = ON line in a setup file doesn’t carry over to the app, because the setting is per connection. The fix was an event listener in database.py that runs it on every new connection.
[16-Nov-26] Challenge: the app/ package layout caused ModuleNotFoundError: No module named 'app' in pytest. The fix was a pytest.ini with pythonpath = . in the project root, and app.-prefixed imports everywhere.
[16-Nov-26] Challenge: Login form fails, FastAPI needs python-multipart to read form data. to fix it I installed python-multipart
[16-Nov-26] I wrote 22 tests: 8 for registration and 14 for login and token protection.

### Posts and topics

[17-Nov-26] I added a post_topic table in model.py to satisfy requirement post has one or more topics
[17-Nov-26] I fixed the four topic names (Politics, Health, Sport, Tech) and seed them into the database at startup. In fact, seed_topics inserts any topic that are missing because API has no endpoint to create topics, so without this a new post would fail. While main.py runs it at startup, after create_all, so the topics always exist and nobody can create new ones.
[17-Nov-25] built POST /posts, GET /posts/{id}, GET /posts?topic= and GET /topics. All of them need a token through get_current_user.
[17-Nov-26] I wrote the validation code in schemas.py. PostCreate defines what a client may send.
[17-Nov-26] I also set up the derived fields. to_post_out works out status (Expired when expires_at has passed, otherwise Live). It counts likes and dislikes from the reactions. Authors, topics, reactions and comments now loaded up front, so a list doesn’t run a query per post.
[17-Nov-26] I added a small helper in utils.py. utcnow() returns the current UTC time without timezone info, the same form SQLite gives back. Mixing aware and naive datetimes raises an error, so all comparisons use this one function.
[17-Nov-26] I updated the tests. conftest.py seeds the topics in the test database, because the startup code doesn’t run in tests, and adds a second logged-in user.
[17-Nov-26] I wrote 25 tests in test_posts.py and rewrote the 3 model tests to use topics.

### Reactions and Comments

[21-Nov-26] Read the requirements and conceptualize the design 
[21-Nov-26] I added ReactionType in constants.py. It allows only like and dislike. 
[21-Nov-26] I added ReactionIn and CommentCreate in schemas.py. Neither has a user id field, so the author always comes from the token.
[21-Nov-26] I created services.py with one function, ensure_post_open. It returns 409 when a post has expired. Reactions and comments both call it.
[21-Nov-26] I built PUT /posts/{id}/reaction. It creates the reaction, switches it, or does nothing if the user repeats the same one. it uses PUT, because sending the same request twice gives the same result.
[21-Nov-26] I built POST /posts/{id}/comments. It records the author from the token, the trimmed text and a server timestamp.
[21-Nov-26] I wrote 31 tests in test_interactions.py and ran the whole suite: 82 passed with warnings treated as errors.

### Expiry and history

[21-Nov-26] Read the requirements, but most of the expiry rule already worked from previous step.
[21-Nov-26] I checked the expiry rule. A post is expired when the current time is equal to or later than its expiry time. The code already did this in is_expired, and we added a test for the exact boundary
[21-Nov-26] I made expiry times strict. A time without a timezone, such as 2030-01-01T00:00:00 or a date alone, now returns 422. A time with Z or an offset such as +02:00 is converted to UTC.
[21-Nov-26] I configuredt so that every time the API returns end with Z, for example 2030-01-01T00:00:00Z. Inside the app and the database, times stay as plain UTC.
[21-Nov-26] I added the status filter to topic browsing: GET /posts?topic=Tech&status=Live or status=Expired. With no status filter, both are returned. The filter also works without a topic.
[21-Nov-26] I wrote the filter as one shared rule in services.py (status_clause) so the filter and the status shown on each post cannot disagree.
[21-Nov-26] I checked the clarification about repeated reactions. A repeated like on an expired post already returned 409, because the expiry check runs before anything is saved. Then I added a test to lock that in.
[21-Nov-26] One old test had to change. test_post_with_naive_expiry expected a time without a timezone to be accepted. The new requirement says reject it, so I replaced it with a test that expects 422.
[21-Nov-26] I wrote 22 new tests in test_expiry.py. The full suite passed: 104 tests with warnings treated as errors.
[21-Nov-26] I ran a real server with a real clock. A post set to expire in 3 seconds showed Live, then Expired by itself. The Live and Expired filters split it correctly, and a repeat like and a new comment both returned 409.
[21-Nov-26] 