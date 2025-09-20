import os

CHATTERFLOW_SERVER_HOST = os.getenv("CHATTERFLOW_SERVER_HOST", "127.0.0.1")
CHATTERFLOW_SERVER_PORT = int(os.getenv("CHATTERFLOW_SERVER_PORT", "9009"))

CHATTERFLOW_HOME = os.getenv("CHATTERFLOW_HOME", os.path.expanduser("~/.chatterflow"))
os.makedirs(CHATTERFLOW_HOME, exist_ok=True)
CHATTERFLOW_USERS_FILE_PATH = os.path.join(CHATTERFLOW_HOME, "users.json")
