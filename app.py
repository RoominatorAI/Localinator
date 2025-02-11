import json
import os
import time
print("Loading packaged content...")
startTime = time.time()
import packaged
print(f"Finished in {time.time() - startTime}s.")
import subprocess
#import pyttsx3
#from openai import OpenAI

with open("config.json","r") as f:
    config = json.load(f)
AIdevice = config["device"]
verbose = config["verbose"]
from flask import Flask, request, send_file, make_response, Response, jsonify, abort, session, redirect
import sqlite3
from sys import maxsize as inf
import bcrypt
import random
import uuid
#import fandom as wiki
import threading
from waitress import serve
import datetime
from gpt4all import GPT4All
import init
import compiled_settings
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
model = None
if compiled_settings.include_ai_model:
    with packaged.open("/packaged/metadata/Llama-3.2-1B-Instruct-Q4_0.gguf") as tmpfile_location:
        if not os.path.isfile("./metadata/Llama-3.2-1B-Instruct-Q4_0.gguf"):
            Path(tmpfile_location).rename("./metadata/Llama-3.2-1B-Instruct-Q4_0.gguf")
        model = GPT4All("Llama-3.2-1B-Instruct-Q4_0.gguf",model_path="./metadata",device=AIdevice,n_ctx=int(1024*20))
else:
    model = GPT4All("Llama-3.2-1B-Instruct-Q4_0.gguf",model_path="./metadata",device=AIdevice,n_ctx=int(1024*20))

@app.route("/")
def hello_world():
    # allow without auth validation OR main site won't work
    with packaged.open("/packaged/root.html") as tmpfile_location:
        with open(tmpfile_location, "r", encoding="utf-8") as f:
            return f.read().replace("%s","Healthy")


@app.route("/client/<path:path>")
@app.route("/client/",defaults={"path":"index.html"})
def clientsender(path):
    if ".." in path:
        abort(400)  # Bad request
    # only a static file sender, so allow without auth validation OR main site won't work
    with packaged.open("/packaged/client/" + path) as tmpfile_location:
        response = send_file(tmpfile_location, as_attachment=False)
        response.headers['X-Frame-Options'] = "SAMEORIGIN"

        return response

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
                    mimetype='text/plain')  # Sure i can let this route be used without the frigging auth validation, its minimal cpu usage anyways


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
            return redirect("/client/login.html?error=Username or password is incorrect.")
        stored_hash = user["passhash"]
        if bcrypt.hashpw(password.encode('utf-8'), stored_hash) == stored_hash:
            session['authkey'] = bcrypt.gensalt()  # We use random salts for authkey, code smell i know
            session['username'] = username
            session['id'] = user["id"]
            session['user'] = user
            session.permanent = False
            return redirect("/client/index.html")
        else:
            return redirect("/client/login.html?error=Username or password is incorrect.")


@app.route('/register', methods=['POST'])
def register():
    if config["ignorelogin"]:
        return redirect("/client/index.html?error=Account management is not allowed in Single User Mode")
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

        return redirect("/client/login.html")


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
    serve(app, host='0.0.0.0', port=8080)
    close_connection()
