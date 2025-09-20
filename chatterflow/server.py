#!/usr/bin/env python3
"""
server.py

Run: python server.py

Multi-client chat server with user authentication.
Users stored in users.json with PBKDF2 password hashing.
"""

import asciigenator
import chatterflow
import socket
import threading
import json
import os
import hashlib
import secrets
import struct
from typing import Dict, Any
from .env import CHATTERFLOW_SERVER_HOST, CHATTERFLOW_SERVER_PORT


lock = threading.Lock()
clients: Dict[str, socket.socket] = {}
addresses: Dict[socket.socket, str] = {}


# ---------------- User store helpers ----------------
def load_users() -> Dict:
    """
    Loads the user database from a JSON file.

    If the user file does not exist, it returns an empty dictionary.

    Returns:
        dict: A dictionary containing user data, with usernames as keys.
    """
    if not os.path.exists(chatterflow.env.CHATTERFLOW_USERS_FILE_PATH):
        return {}
    with open(chatterflow.env.CHATTERFLOW_USERS_FILE_PATH, "r") as f:
        return json.load(f)


def save_users(users: Dict):
    """
    Saves the user database to a JSON file.

    Args:
        users (dict): A dictionary containing user data to be saved.
    """
    with open(chatterflow.env.CHATTERFLOW_USERS_FILE_PATH, "w") as f:
        json.dump(users, f, indent=2)


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """
    Hashes a password using PBKDF2-HMAC-SHA256.

    If a salt is not provided, a new 16-byte salt is generated. The function
    uses 200,000 iterations.

    Args:
        password (str): The password to hash.
        salt (str, optional): The salt to use, as a hex string. Defaults to None.

    Returns:
        tuple[str, str]: A tuple containing the salt (hex) and the derived key (hex).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return salt, dk.hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """
    Verifies a password against a stored salt and hash.

    Args:
        password (str): The password to verify.
        salt (str): The salt used during hashing (hex).
        stored_hash (str): The stored password hash to compare against (hex).

    Returns:
        bool: True if the password is correct, False otherwise.
    """
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return dk.hex() == stored_hash


# ---------------- Socket JSON helpers ----------------
def send_json(conn: socket.socket, obj: Any):
    """
    Serialize and send a JSON object over a socket with a length-prefixed header.

    This function first encodes the given Python object as a compact JSON string,
    then prefixes it with a 4-byte unsigned integer (big-endian) indicating the
    length of the serialized data. Both the header and JSON payload are sent
    using `socket.sendall` to ensure all bytes are transmitted.

    Args:
        conn (socket.socket): An active, connected socket object.
        obj (Any): A JSON-serializable Python object (e.g., dict, list, str, int).

    Raises:
        TypeError: If `obj` cannot be serialized to JSON.
        OSError: If the socket connection is broken during transmission.
    """
    data = json.dumps(obj, separators=(",", ":")).encode()
    header = struct.pack(">I", len(data))
    conn.sendall(header + data)


def recv_json(conn: socket.socket) -> Any:
    """
    Receive and deserialize a length-prefixed JSON object from a socket.

    This function reads a 4-byte header to determine the incoming payload size,
    then reads that many bytes from the socket. The received bytes are decoded
    and parsed as a JSON object.

    Args:
        conn (socket.socket): An active, connected socket object.

    Returns:
        Any: The deserialized Python object, or None if the connection is
             closed or an incomplete header is received.

    Raises:
        json.JSONDecodeError: If the received data is not valid JSON.
        OSError: If the socket connection is broken during transmission.
    """
    header = conn.recv(4)
    if not header or len(header) < 4:
        return None
    total = struct.unpack(">I", header)[0]
    chunks, bytes_recd = [], 0
    while bytes_recd < total:
        chunk = conn.recv(min(total - bytes_recd, 4096))
        if not chunk:
            return None
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return json.loads(b"".join(chunks).decode())


# ---------------- Broadcast / Private send ----------------
def broadcast(sender: str, message: str):
    """
    Broadcasts a message to all connected and authenticated clients.

    If sending to a client fails, that client is removed from the pool.

    Args:
        sender (str): The username of the message sender (or 'SYS' for system).
        message (str): The message text to broadcast.
    """
    payload = {"type": "broadcast", "from": sender, "text": message}
    with lock:
        for user, sock in list(clients.items()):
            try:
                send_json(sock, payload)
            except Exception:
                remove_client(user)


def send_private(sender: str, target: str, message: str) -> bool:
    """
    Sends a private message to a single specified client.

    Args:
        sender (str): The username of the message sender.
        target (str): The username of the recipient.
        message (str): The message text to send.

    Returns:
        bool: True if the message was sent successfully, False if the target
              user was not found or the connection failed.
    """
    payload = {"type": "private", "from": sender, "text": message}
    with lock:
        sock = clients.get(target)
        if sock:
            try:
                send_json(sock, payload)
                return True
            except Exception:
                remove_client(target)
    return False


def send_system(conn: socket.socket, text: str):
    """
    Sends a system message to a single client.

    Args:
        conn (socket.socket): The socket of the client to send the message to.
        text (str): The system message text.
    """
    send_json(conn, {"type": "system", "text": text})


def remove_client(username: str):
    """
    Removes a client from the global client and address dictionaries and closes the socket.

    This function is thread-safe.

    Args:
        username (str): The username of the client to remove.
    """
    with lock:
        sock = clients.pop(username, None)
        if sock:
            addresses.pop(sock, None)
            try:
                sock.close()
            except Exception:
                pass


# ---------------- Per-client handler ----------------
def handle_client(conn: socket.socket, addr: tuple):
    """
    Handles a single client connection from inception to termination.

    This function manages the authentication process (register/login), then enters
    a loop to receive and process messages and commands from the client. It
    dispatches actions like broadcasting, private messaging, and user listing.

    Args:
        conn (socket.socket): The client's socket object.
        addr (tuple): The client's address tuple (host, port).
    """
    username = None
    try:
        users = load_users()
        send_system(conn, "WELCOME: send login/register request")
        auth = recv_json(conn)
        if not auth:
            conn.close()
            return
        action = auth.get("action")
        username = auth.get("username")
        password = auth.get("password")
        if not action or not username or not password:
            send_system(conn, "Invalid auth payload")
            conn.close()
            return

        if action == "register":
            if username in users:
                send_json(conn, {"status": "error", "message": "username_taken"})
                conn.close()
                return
            salt, phash = hash_password(password)
            users[username] = {"salt": salt, "hash": phash}
            save_users(users)
            send_json(conn, {"status": "ok", "message": "registered"})
        elif action == "login":
            info = users.get(username)
            if not info or not verify_password(password, info["salt"], info["hash"]):
                send_json(conn, {"status": "error", "message": "invalid_credentials"})
                conn.close()
                return
            send_json(conn, {"status": "ok", "message": "welcome"})
        else:
            send_system(conn, "Unknown action")
            conn.close()
            return

        with lock:
            if username in clients:
                send_json(conn, {"status": "error", "message": "already_logged_in"})
                conn.close()
                return
            clients[username] = conn
            addresses[conn] = f"{addr[0]}:{addr[1]}"

        broadcast("SYS", f"--- {username} has joined the chat ---")

        while True:
            payload = recv_json(conn)
            if payload is None:
                break
            typ = payload.get("type")
            if typ == "message":
                text = payload.get("text", "")
                broadcast(username, text)
            elif typ == "private":
                target = payload.get("to")
                text = payload.get("text", "")
                ok = send_private(username, target, text)
                if not ok:
                    send_system(conn, f"user {target} not found")
            elif typ == "list":
                with lock:
                    send_json(conn, {"type": "list", "users": list(clients.keys())})
            elif typ == "quit":
                break
            else:
                send_system(conn, "unknown_type")

    except Exception as e:
        print("Client error:", e)
    finally:
        if username:
            remove_client(username)
            broadcast("SYS", f"--- {username} has left the chat ---")
        try:
            conn.close()
        except Exception:
            pass


# ---------------- Server main ----------------
def start_server(host: str = CHATTERFLOW_SERVER_HOST, port: int = CHATTERFLOW_SERVER_PORT):
    """
    Starts the main chat server and listens for incoming connections.

    The server binds to a host and port, and for each new connection, it spawns
    a new daemon thread running `handle_client` to manage that client
    independently.

    Args:
        host (str, optional): The host address to bind to. Defaults to HOST.
        port (int, optional): The port to listen on. Defaults to PORT.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(100)
    print(asciigenator.generate("CHATTERFLOW", font="block"))
    print(f"Server listening on {host}:{port}")
    try:
        while True:
            conn, addr = sock.accept()
            print("Connection from", addr)
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        sock.close()


if __name__ == "__main__":
    start_server()
