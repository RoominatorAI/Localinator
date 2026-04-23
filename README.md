# Localinator

Version v1.1.0

Fork of an old version of ChattedRooms' backend and frontend, neatly packed into one repository, for YOU to self-host your own little ChattedRooms.

[![Build Localinator](https://github.com/RoominatorAI/Localinator/actions/workflows/main.yml/badge.svg)](https://github.com/RoominatorAI/Localinator/actions/workflows/main.yml)

# USER WARNING
Do NOT use untrusted UIs, they are **Python** files that are executed. They may delete your database, or worse, destroy your computer.

Don't want to deal with the hassle? Use the embedded UI.
# config reference
This is a primitive version of JSON with Comments, the comments are stripped when loading, but they are there for you to understand what each setting does.
An example config is this:
```jsonc
{
  "verbose": true, // Log more?
  "env": "production", // "production" or "development", mostly useless, switches database.
  "ignorelogin": false, // If true, enable single user mode.
  "device": "gpu", // Where to run the model on.
  "disable_registration": false, // Set to true to disable user registration, allowing only existing users to log in.
  "model": "Llama-3.2-1B-Instruct-Q4_0.gguf" // The model file to use, located in the "models" directory. Must be a .gguf file, we use gpt4all.
}
```