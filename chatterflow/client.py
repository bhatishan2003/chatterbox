#!/usr/bin/env python3
"""
client.py

Run: python client.py

Terminal chat client. Supports login/register and commands:
 - /msg <user> <text>   private message
 - /list                list users
 - /help                show help
 - /quit                quit
"""

import chatterflow
import socket
import struct
import json
import threading
import getpass
import sys
from typing import Any


# ---------------- Socket helpers ----------------
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


# ---------------- Receiver thread ----------------
def receiver_thread(conn: socket.socket):
    """
    Listens for incoming messages from the server and prints them to the console.

    This function runs in a dedicated thread, continuously calling `recv_json`
    to wait for new messages. It handles different message types (system,
    broadcast, private, user list) and formats them for display. The thread
    terminates if the connection is lost.

    Args:
        conn (socket.socket): The client's socket connection to the server.
    """
    try:
        while True:
            msg = recv_json(conn)
            if msg is None:
                print("\n[Disconnected]")
                break
            typ = msg.get("type")
            if typ == "system":
                print(f"[SYSTEM] {msg.get('text')}")
            elif typ == "broadcast":
                print(f"[{msg.get('from')}] {msg.get('text')}")
            elif typ == "private":
                print(f"[PRIVATE from {msg.get('from')}] {msg.get('text')}")
            elif typ == "list":
                print("[USERS] " + ", ".join(msg.get("users", [])))
            else:
                print("[UNKNOWN]", msg)
    finally:
        conn.close()
        sys.exit(0)


# ---------------- Helpers ----------------
def print_help():
    """Prints a list of available client-side commands to the console."""
    print("Commands:")
    print("  /msg <user> <text>   private message")
    print("  /list                list users")
    print("  /help                show help")
    print("  /quit                quit")


# ---------------- Client main ----------------
def main():
    """
    The main entry point for the chat client.

    This function establishes a connection to the server, handles the user
    authentication (login or register) process, and then starts the receiver
    thread. It then enters a loop to read user input for sending messages
    or executing commands.
    """
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((chatterflow.env.CHATTERFLOW_SERVER_HOST, chatterflow.env.CHATTERFLOW_SERVER_PORT))

    welcome = recv_json(conn)
    if welcome and welcome.get("type") == "system":
        print("[SERVER]", welcome.get("text"))

    while True:
        choice = input("Do you want to (l)ogin or (r)egister? [l/r]: ").strip().lower()
        if choice in ("l", "r"):
            break
    action = "login" if choice == "l" else "register"
    username = input("username: ").strip()
    password = getpass.getpass("password: ")

    send_json(conn, {"action": action, "username": username, "password": password})
    resp = recv_json(conn)
    if not resp or resp.get("status") != "ok":
        print("Auth failed:", resp)
        conn.close()
        return
    print("[AUTH]", resp.get("message"))

    t = threading.Thread(target=receiver_thread, args=(conn,), daemon=True)
    t.start()

    print("Type /help for commands. Start chatting!")
    try:
        while True:
            line = input()
            if not line:
                continue
            if line.startswith("/"):
                parts = line.split(" ", 2)
                cmd = parts[0].lower()
                if cmd == "/msg" and len(parts) == 3:
                    send_json(conn, {"type": "private", "to": parts[1], "text": parts[2]})
                elif cmd == "/list":
                    send_json(conn, {"type": "list"})
                elif cmd == "/help":
                    print_help()
                elif cmd == "/quit":
                    send_json(conn, {"type": "quit"})
                    print("Quitting...")
                    break
                else:
                    print("Unknown command. Use /help")
            else:
                send_json(conn, {"type": "message", "text": line})
    except KeyboardInterrupt:
        send_json(conn, {"type": "quit"})
    finally:
        conn.close()


if __name__ == "__main__":
    main()
