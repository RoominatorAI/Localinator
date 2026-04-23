import json
import os
import time
import re
import sys
__VERSION__ = "1.1.0"

# Helper to parse version strings into comparable tuples of integers
def _parse_version(v: str):
    """Convert a version string like '1.2.3' into a tuple of ints (1, 2, 3).
    Missing components are treated as zeros, e.g., '1.2' -> (1, 2, 0).
    """
    parts = v.split('.')
    # Ensure at least three components for consistent comparison
    while len(parts) < 3:
        parts.append('0')
    return tuple(int(p) for p in parts)
print("Loading packaged content...")
startTime = time.time()
packaged = {}
has_embedded_client = False
try:
    if embedded == embedded: # type: ignore
        has_embedded_client = True
        # Embedded client datablob is available as a variable named 'embedded' in the global scope, so we can just use it directly without needing to read packaged.py at all!
        # Useful for incase the datablob fails to run.
except NameError:
    pass
if not os.path.exists("config.jsonc") and not os.path.exists("config.json"):
    with open("config.jsonc","w") as f:
        f.write("""{
  "verbose": true, // Log more?
  "env": "production", // "production" or "development", mostly useless, switches database.
  "ignorelogin": false, // If true, enable single user mode.
  "device": "gpu", // Where to run the model on.
  "disable_registration": false, // Set to true to disable user registration, allowing only existing users to log in.
  "model": "Llama-3.2-1B-Instruct-Q4_0.gguf" // The model file to use, located in the "models" directory. Must be a .gguf file, we use gpt4all.
}
""")
    print("No config.json found, wrote example one.")

if not os.path.exists("packaged.py") and not has_embedded_client:
    print("No datablob found! Please download one from Releases and then put it as packaged.py next to Localinator.")
    sys.exit(1)

if  os.path.exists("packaged.py"):
    with open("packaged.py","r") as f:
        try:
            exec(f.read(),packaged)
        except Exception as e:
            print("Warning: Datablob threw error, but embedded client is available so continuing anyway. Error was:",repr(e))
            packaged = embedded # type: ignore
elif has_embedded_client:
    print("No datablob found, but embedded client is available so continuing anyway.")
    packaged = embedded # type: ignore

# Read the minimal version requirement for the client from the datablob constraints, and check if it's compatible with this server version.
if "constraints" in packaged and "REQUIRES_SERVER" in packaged["constraints"]:
    for part in packaged["constraints"]["REQUIRES_SERVER"].split(","):
        part = part.strip()
        if part.startswith(">="):
            required_version = part[2:].strip()
            if _parse_version(__VERSION__) < _parse_version(required_version):
                print(f"Warning: This client requires server version {required_version} or higher. This server is version {__VERSION__}. The client may not work properly.")
        elif part.startswith(">"):
            required_version = part[1:].strip()
            if _parse_version(__VERSION__) <= _parse_version(required_version):
                print(f"Warning: This client requires server version {required_version} higher (exclusive). This server is version {__VERSION__}. The client may not work properly.")
        elif part.startswith("=="):
            required_version = part[2:].strip()
            if _parse_version(__VERSION__) != _parse_version(required_version):
                print(f"Warning: This client requires server version {required_version}. This server is version {__VERSION__}. The client may not work properly.")
        elif part.startswith("<="):
            required_version = part[2:].strip()
            if _parse_version(__VERSION__) > _parse_version(required_version):
                print(f"Warning: This client requires server version {required_version} or lower (inclusive). This server is version {__VERSION__}. The client may not work properly.")
        elif part.startswith("<"):
            required_version = part[1:].strip()
            if _parse_version(__VERSION__) >= _parse_version(required_version):
                print(f"Warning: This client requires server version {required_version} or lower (exclusive). This server is version {__VERSION__}. The client may not work properly.")
print(f"Finished in {time.time() - startTime}s.")
#import pyttsx3
#from openai import OpenAI
string_re = r'"(?:\\.|[^"\\])*"'
comment_re = r'//.*?$|/\*.*?\*/'

def strip_comments(text):
    def replacer(match):
        if match.group(0).startswith('"'):
            return match.group(0)  # keep strings
        return ''

    pattern = re.compile(f'{string_re}|{comment_re}', re.S | re.M)
    return re.sub(pattern, replacer, text)
config_path = "config.json"
if os.path.exists("config.jsonc"):
    config_path = "config.jsonc"
with open(config_path,"r") as f:
    config = json.loads(strip_comments(f.read()))



## INIT.PY

import sqlite3
# Define the database name
DATABASE = 'production.db' if config["env"] == "production" else "staging.db"  # Change to 'staging.db' if needed

def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create the users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        passhash TEXT NOT NULL,
        metadata TEXT DEFAULT '{}',
        username TEXT UNIQUE NOT NULL,
        created_at INTEGER NOT NULL
    );
    ''')

    # Create the CharJSON_store table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS CharJSON_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        json_content TEXT NOT NULL,
        creatorId INTEGER NOT NULL,
        visibilityType INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (creatorId) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')

    # Create the chat_sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_history TEXT NOT NULL,
        creatorId INTEGER NOT NULL,
        botId INTEGER NOT NULL,
        FOREIGN KEY (creatorId) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (botId) REFERENCES CharJSON_store(id) ON DELETE CASCADE
    );
    ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    print(f"Database '{DATABASE}' initialized successfully.")

if not os.path.isfile(DATABASE):
    create_database()

####



AIdevice = config["device"]
verbose = config["verbose"]
from flask import Flask, request, send_file, make_response, Response, jsonify, abort, session, redirect
from sys import maxsize as inf
import bcrypt
import random
import uuid
#import fandom as wiki
import threading
from waitress import serve
import datetime
from gpt4all import GPT4All
from pathlib import Path
environment = config["env"]


dblock = threading.Lock()
ttslock = threading.Lock()
app = Flask(__name__)
tts_namespace = uuid.UUID('b1d13232-8eca-11ef-b06f-325096b39f47')

#with open('apikey.secret', 'r') as f:
#    client = OpenAI(api_key=f.read().strip())
app.secret_key = bcrypt.gensalt()
if not os.path.isdir("./metadata"):
    os.makedirs("./metadata")
model = GPT4All(config["model"],model_path="./metadata",device=AIdevice,n_ctx=int(1024*20))

@app.route("/")
def hello_world():
    # allow without auth validation OR main site won't work
    with packaged["open"]("/packaged/root.html") as tmpfile_location:
        with open(tmpfile_location, "r", encoding="utf-8") as f:
            return f.read().replace("%s","Healthy")


@app.route("/client/<path:path>")
@app.route("/client/",defaults={"path":"index.html"})
def clientsender(path):
    if ".." in path:
        abort(400)  # Bad request
    # only a static file sender, so allow without auth validation OR main site won't work
    try:
        with packaged["open"]("/packaged/client/" + path) as tmpfile_location:
                response = send_file(tmpfile_location, as_attachment=False)
                response.headers['X-Frame-Options'] = "SAMEORIGIN"

                return response
    except FileNotFoundError:
        abort(404)  # Not found

@app.route("/generateCensor", methods=['POST'])
def fgkljc():
    if not ("authkey" in session):
        abort(401)  # Nuh uh uh!
    startTime = time.time()
    data = request.get_json()
    cat = data["chat"]
    cat[-1] = {"role": "user", "content": data["togenerate"]}
    response = client.chat.completions.create(
        messages=cat,
        model="gpt-4o-mini",
    ).choices[0].message.content
    if True:
        moderate = client.moderations.create(
            model="omni-moderation-latest",
            input=response
        )
        if moderate.results[0].flagged:
            response="<|CENSOR_DIALOG|>"
    cat[-1] = {"role": "assistant", "content": response}
    return {"result": cat, "finishTime": time.time() - startTime}, 200


@app.route("/generate", methods=['POST'])
def fgklj():
    if not ("authkey" in session):
        abort(401)  # Nuh uh uh!
    startTime = time.time()
    data = request.get_json()
    cat = data["chat"]
    with model.chat_session(system_prompt=f"Chat context: {cat}"):
        response =model.generate(data["togenerate"],temp=float(1),max_tokens=int(200))
    cat[-1] = {"role": "user", "content": data["togenerate"]}
    cat[-1] = {"role": "assistant", "content": response}
    return {"result": cat, "finishTime": time.time() - startTime}, 200


@app.route('/isalive', methods=['GET'])
def is_alive():
    return Response('Yes, I am alive.',
                    mimetype='text/plain')


@app.route("/getFandomPage", methods=['GET'])
def getFandom():
    abort(410)
    if not ("authkey" in session):
        abort(401)  # Nuh uh uh!
    if request.args.get('wiki') is None:
        abort(400)
    if request.args.get('title') is None:
        abort(400)
    page = wiki.page(request.args.get('title'), wiki=request.args.get('wiki'))
    print("Got")
    with model.chat_session(system_prompt="""Convert the following Fandom page information into a Chardef format that encapsulates the character. Fill in the placeholdrs. Try to make the chardef in 512 characters or less. Otherwise the Roleplaying AI will be confused and halfway forget about it.
Respond with this json but with the placeholders replaced (use no Markdown, only respond with the JSON, since i use this as an API with your response sent directly):
{
  "char_name": "[Character name]",
  "char_persona": "[Description about the character, in a few paragraphs]",
  "char_greeting": "[First message sent by character]",
  "world_scenario": "[Describe the setting/world the character is in]",
  "example_dialogue": "[Provide an example dialogue from the character]",
  "name": "[Duplicate this from char_name]",
  "description": "[Duplicate from char_persona]",
  "first_mes": "[Duplicate from char_greeting]",
  "scenario": "[Duplicate from world_scenario]",
  "mes_example": "[Duplicate from example_dialogue]",
  "personality": "[Short description of character's personality, one sentence.]",
  "multichar": [true if page depicts multiple characters, false if only 1 character depicted],
  "metadata": {
    "version": 1,
    "created": "[Use %s to replace with the current timestamp]",
    "modified": "[Use %s to replace with the current timestamp]",
    "source": "Sourced from [replace me with URL]",
    "tool": {
      "name": "Fandom Page to Chardef Converter [Roominator Import Page Character Tool]",
      "version": "0.2.0"
    }
  }
}
    """):
        message = ""
        for tok in model.generate(f"""Fandom URL:
    {page.url}
    Page Title:
    {page.title}
    Page Contents:
    {page.plain_text}
""",max_tokens=int(6192),streaming=True):
            message += tok
            if verbose:
                print(tok,end="")
    return message.replace("%s", str(round(time.time())))

@app.route('/env', methods=['get'])
def getcurenv():
    return jsonify({"environment": environment})

### DATABASE!
if environment == 'production':
    DATABASE = 'production.db'
else:
    DATABASE = 'staging.db'

print(f"Current environment: {environment}")
print(f"Verbosity: {verbose}")
print(f"Device running AI: {AIdevice}")
print(f"Single user mode: {config['ignorelogin'] and 'on' or 'off'}")
sqlite3.threadsafety = 3
g = globals()
_database = None


def get_db():
    global _database
    if _database is None:
        _database = sqlite3.connect(DATABASE, check_same_thread=False)
    return _database


def close_connection():
    global _database
    db = _database
    if db is not None:
        db.commit()
        db.close()


@app.route('/getchardef/<int:id>', methods=['GET'])
def get_json_data(id):
    char = get_char_by_id(id)

    # Handle case where character is not found
    if char is None:
        abort(404, description="Character not found")

    # Visibility check
    if char["visibilityType"] == 0 and char["creatorId"] != session["id"]:
        abort(403, description="Forbidden access")

    return jsonify(char)


# login stuff

def get_user_by_username(username):
    # Connect to the SQLite database
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Prepare the SQL query to fetch the user
        query = "SELECT * FROM users WHERE username = ?"
        cursor.execute(query, (username,))

        # Fetch the user record
        user = cursor.fetchone()

        # Check if a user was found and return the result
        if user:
            # user is a tuple containing the record
            return {
                "id": user[0],
                "passhash": user[1],
                "metadata": user[2],
                "username": user[3],
                "created_at": user[4],
            }
        else:
            return None  # No user found with the given username

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


def get_username_by_id(user_id):
    # Connect to the SQLite database
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Prepare the SQL query to fetch the user by ID
        query = "SELECT username FROM users WHERE id = ?"
        cursor.execute(query, (user_id,))

        # Fetch the user record
        user = cursor.fetchone()

        # Check if a user was found and return the result
        if user:
            # user is a tuple containing the username
            return user[0]  # Return the username
        else:
            return None  # No user found with the given ID

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None


@app.route('/login', methods=['POST'])
def login():
    if config["ignorelogin"]:
        return redirect("/client/index.html?error=Account management is not allowed in Single User Mode")
    password = request.form.get('password')
    username = request.form.get('username')
    with dblock:
        try:
            user = get_user_by_username(username)
        except Exception as e:
            return redirect("/client/index.html?error=Server failure. Please try again later.")
        if user is None:
            return redirect("/client/users/login.html?error=Username or password is incorrect.")
        stored_hash = user["passhash"]
        if bcrypt.hashpw(password.encode('utf-8'), stored_hash) == stored_hash:
            session['authkey'] = bcrypt.gensalt()  # We use random salts for authkey, code smell i know
            session['username'] = username
            session['id'] = user["id"]
            session['user'] = user
            session.permanent = False
            return redirect("/client/index.html")
        else:
            return redirect("/client/users/login.html?error=Username or password is incorrect.")


@app.route('/register', methods=['POST'])
def register():
    if config["ignorelogin"]:
        return redirect("/client/users/register.html?error=Account management is not allowed in Single User Mode")
    if config.get("disable_registration", False):
        return redirect("/client/users/register.html?error=Registration is currently disabled.")
    with dblock:
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "Username and password are required!", 400

        # Check if the username already exists
        existing_user = get_user_by_username(username)
        if existing_user is not None:
            return "Username already exists!", 400

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert the new user into the database
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (passhash, metadata, username, created_at) VALUES (?, ?, ?, ?)",
                (hashed_password, '{}', username, int(time.time()))
            )
            conn.commit()
        except sqlite3.Error as e:
            return f"An error occurred while registering: {e}", 500

        return redirect("/client/users/login.html")

@app.route("/isRegOpen")
def is_reg_open():
    if config["ignorelogin"]:
        return jsonify({"open": False})
    return jsonify({"open": not config.get("disable_registration", False)})


@app.route('/whoami', methods=['get'])
def whoami():
    if not ("authkey" in session):
        return jsonify({"username": "Guest", "id": -2})
    return jsonify({"username": session["username"], "id": session["id"]})

#engine = pyttsx3.init()

@app.route("/voice")
def tts():
    abort(410)
    inValue = str(request.args.get("in")).strip()

    if not inValue:
        return jsonify({"OK":False,"error":"Input text is required."}), 400

    id = uuid.uuid5(tts_namespace, inValue)
    file_path = os.path.join('out', f'speech{id}.mp3')

    if os.path.exists(file_path):
        return send_file(file_path)

    # Use a lock to prevent multiple threads from generating the same file
    with ttslock:
        if os.path.exists(file_path):
            return send_file(file_path)  # Another thread may have generated the file

        if not ("authkey" in session):
            abort(401)  # Unauthorized access

        try:
            engine.save_to_file(inValue, file_path)
            engine.runAndWait()
        except Exception as e:
            return jsonify({"OK":False,"error":str(e)}),500

    return send_file(file_path)

# char stuff

def search(name):
    with dblock:
        conn = get_db()
        cursor = conn.cursor()

        # Define the char_name you're searching for
        char_name_to_search = name

        # SQL query to search for the specific char_name in json_content
        query = '''
SELECT * FROM CharJSON_store
WHERE json_extract(json_content, '$.char_name') LIKE '%' || ? || '%'
LIMIT ?

        '''

        # Execute the query
        cursor.execute(query, (char_name_to_search,100))

        # Fetch and print the results
        results = cursor.fetchall()
        returned = []
        for result in results:
            returned.append({
                "id": result[0],
                "json_content": result[1],
                "creatorId": result[2],
                "visibilityType": result[3],
            })
        return returned


@app.route("/search/<name>")
def searchendpoint(name):
    return jsonify(search(name))


def char_roulette(number):
    with dblock:
        conn = get_db()
        cursor = conn.cursor()


        # SQL query to search for the specific char_name in json_content
        query = '''SELECT * FROM CharJSON_store ORDER BY RANDOM() LIMIT ?'''

        # Execute the query
        cursor.execute(query, (number,))

        # Fetch and print the results
        results = cursor.fetchall()
        returned = []
        for result in results:
            returned.append(result[0])
        return returned

@app.route("/roulette/<num>")
def roulette_endpoint(num):
    if num.isdigit():
        return jsonify(char_roulette(int(num)))
    else:
        abort(400)

def get_char_by_id(char_id):
    # Connect to the SQLite database
    conn = get_db()  # Assuming you have a function to get the database connection
    cursor = conn.cursor()

    try:
        # Prepare the SQL query to fetch the character JSON by ID
        query = "SELECT * FROM CharJSON_store WHERE id = ?"
        cursor.execute(query, (char_id,))

        # Fetch the character record
        char_record = cursor.fetchone()

        # Check if a character was found and return the result
        if char_record:
            # char_record is a tuple containing the record
            return {
                "id": char_record[0],
                "json_content": char_record[1],
                "creatorId": char_record[2],
                "visibilityType": char_record[3],
            }
        else:
            return None  # No character found with the given ID

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None

def get_chat_by_id(char_id,chat_id):
    # Connect to the SQLite database
    conn = get_db()  # Assuming you have a function to get the database connection
    cursor = conn.cursor()

    try:
        # Prepare the SQL query to fetch the chat JSON by ID
        query = "SELECT * FROM chat_sessions WHERE id = ? AND botId = ?"
        cursor.execute(query, (chat_id,char_id))

        # Fetch the chat record
        char_record = cursor.fetchone()

        # Check if a chat was found and return the result
        if char_record:
            # chat_record is a tuple containing the record
            return {
                "id": char_record[0],
                "chat_history": char_record[1],
                "creatorId": char_record[2]
            }
        else:
            return None  # No chat found with the given ID

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        return None




@app.route('/delchar/<id>', methods=['get'])
def delchar(id):
    with dblock:
        char = get_char_by_id(id)
        if char is None:
            abort(404)
        creator = get_user_by_username(get_username_by_id(char["creatorId"]))
        if creator["id"] != session["id"]:
            abort(403)  # No, stop trying to delete someone else's stuff
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CharJSON_store WHERE id = ?", (id,))
        return "Successful."


@app.route('/createchar', methods=['post'])
def crchar():
    with dblock:
        # Check if the user is logged in (assuming session contains user ID)
        if "authkey" not in session:
            abort(401)  # Unauthorized if not logged in

        # Get the data from the request
        data = request.json

        # Validate the required fields

        # Extract the necessary fields from the request data
        json_content = json.dumps(data)
        visibility_type = 1
        creator_id = session["id"]  # Get the creator ID from the session

        # Connect to the SQLite database
        conn = get_db()
        cursor = conn.cursor()

        try:
            # Prepare the SQL query to insert the new character
            query = """
            INSERT INTO CharJSON_store (json_content, creatorId, visibilityType)
            VALUES (?, ?, ?)
            """
            cursor.execute(query, (json_content, creator_id, visibility_type))
            conn.commit()  # Commit the changes

            # Get the ID of the newly created character
            new_char_id = cursor.lastrowid

            # Optionally return the new character's data
            return jsonify({"id": new_char_id, "json_content": json_content, "creatorId": creator_id,
                            "visibilityType": visibility_type}), 201

        except sqlite3.Error as e:
            conn.rollback()  # Rollback in case of an error
            print(f"An error occurred: {e}")
            abort(500)  # Internal Server Error




@app.route("/getChat/<int:char_id>/<chat_id>", methods=['GET'])
def get_chat(char_id,chat_id):
    with dblock:
        chat = get_chat_by_id(char_id,chat_id)
        if chat is None:
            return jsonify({"error": "Chat session not found"}), 404
        if chat["creatorId"] != session["id"]:
            abort(403, description=f'Cannot access another user\'s chat! Your userid: {session["id"]} Chat creator id: {chat["creatorId"]}')
        return jsonify({"id": chat["id"], "chat_history": json.loads(chat["chat_history"])}), 200

@app.route('/delchat/<int:char_id>/<id>', methods=['get'])
def delchat(char_id,id):
    with dblock:
        chat = get_chat_by_id(char_id,id)
        if chat is None:
            abort(404)
        if chat["creatorId"] != session["id"]:
            abort(403)  # No, stop trying to delete someone else's stuff
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE id = ? AND botId = ?", (id,char_id))
        return "Successful."



@app.route("/crChat/<int:char_id>", methods=['GET'])
def create_chat(char_id):
    with dblock:
        conn = get_db()
        cursor = conn.cursor()
        creator_id = int(session["id"])
        cursor.execute("INSERT INTO chat_sessions (chat_history,creatorId,botId) VALUES (?,?,?)", (json.dumps([]),creator_id,char_id))

        new_chat_id = cursor.lastrowid
        return jsonify({"chat_id": new_chat_id}), 201


@app.route("/setChat/<int:char_id>/<int:chat_id>", methods=['POST'])
def set_chat(char_id,chat_id):
    with dblock:
        chat = get_chat_by_id(char_id,chat_id)
        if chat is None:
            abort(404)
        if chat["creatorId"] != session["id"]:
            abort(403)  # No, stop trying to delete someone else's stuff

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("UPDATE chat_sessions SET chat_history = ? WHERE id = ? AND botId = ?", (request.get_data(), chat_id,char_id))
        conn.commit()

        return jsonify({"message": "Chat session updated"}), 200





# logging, ahh
@app.after_request
def after_request(response):
    now = datetime.datetime.now().strftime("%d/%b/%Y %H:%M:%S")

    # Get request details
    ip = request.remote_addr
    method = request.method
    path = request.path
    protocol = request.environ.get('SERVER_PROTOCOL', '[Unknown]')

    # Log the request in the desired format
    if verbose:
        print(f'{ip} - - [{now}] "{method} {path} {protocol}" {response.status_code} -')
    return response

# exp
@app.before_request
def before_request():
    if config["ignorelogin"]:
        session["authkey"] = "yes"
        session['username'] = "SingleUserMode"
        session["id"] = 0
if __name__ == "__main__":
    print("Serving.")
    print("URL: http://localhost:8080")
    serve(app, host='0.0.0.0', port=8080)
    close_connection()
