import sqlite3
import json
import os
with open("config.json","r") as f:
    config = json.load(f)
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

