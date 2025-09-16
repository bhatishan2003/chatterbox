#!/usr/bin/env python3
"""
server.py

Run: python server.py

Multi-client chat server with user authentication.
Users stored in users.json with PBKDF2 password hashing.
"""

import socket
import threading
import json
import os
import hashlib
import secrets
import struct
from typing import Dict

HOST = '127.0.0.1'
PORT = 9009
USERS_FILE = 'users.json'

lock = threading.Lock()
clients: Dict[str, socket.socket] = {}
addresses: Dict[socket.socket, str] = {}

# ---------------- User store helpers ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_password(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200_000)
    return salt, dk.hex()

def verify_password(password: str, salt: str, stored_hash: str):
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200_000)
    return dk.hex() == stored_hash

# ---------------- Socket JSON helpers ----------------
def send_json(conn: socket.socket, obj):
    data = json.dumps(obj, separators=(',', ':')).encode()
    header = struct.pack('>I', len(data))
    conn.sendall(header + data)

def recv_json(conn: socket.socket):
    header = conn.recv(4)
    if not header or len(header) < 4:
        return None
    total = struct.unpack('>I', header)[0]
    chunks, bytes_recd = [], 0
    while bytes_recd < total:
        chunk = conn.recv(min(total - bytes_recd, 4096))
        if not chunk:
            return None
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return json.loads(b''.join(chunks).decode())

# ---------------- Broadcast / Private send ----------------
def broadcast(sender: str, message: str):
    payload = {'type': 'broadcast', 'from': sender, 'text': message}
    with lock:
        for user, sock in list(clients.items()):
            try:
                send_json(sock, payload)
            except Exception:
                remove_client(user)

def send_private(sender: str, target: str, message: str):
    payload = {'type': 'private', 'from': sender, 'text': message}
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
    send_json(conn, {'type': 'system', 'text': text})

def remove_client(username: str):
    with lock:
        sock = clients.pop(username, None)
        if sock:
            addresses.pop(sock, None)
            try:
                sock.close()
            except Exception:
                pass

# ---------------- Per-client handler ----------------
def handle_client(conn: socket.socket, addr):
    username = None
    try:
        users = load_users()
        send_system(conn, 'WELCOME: send login/register request')
        auth = recv_json(conn)
        if not auth:
            conn.close(); return
        action = auth.get('action')
        username = auth.get('username')
        password = auth.get('password')
        if not action or not username or not password:
            send_system(conn, 'Invalid auth payload')
            conn.close(); return

        if action == 'register':
            if username in users:
                send_json(conn, {'status': 'error', 'message': 'username_taken'})
                conn.close(); return
            salt, phash = hash_password(password)
            users[username] = {'salt': salt, 'hash': phash}
            save_users(users)
            send_json(conn, {'status': 'ok', 'message': 'registered'})
        elif action == 'login':
            info = users.get(username)
            if not info or not verify_password(password, info['salt'], info['hash']):
                send_json(conn, {'status': 'error', 'message': 'invalid_credentials'})
                conn.close(); return
            send_json(conn, {'status': 'ok', 'message': 'welcome'})
        else:
            send_system(conn, 'Unknown action')
            conn.close(); return

        with lock:
            if username in clients:
                send_json(conn, {'status': 'error', 'message': 'already_logged_in'})
                conn.close(); return
            clients[username] = conn
            addresses[conn] = f'{addr[0]}:{addr[1]}'

        broadcast('SYS', f'--- {username} has joined the chat ---')

        while True:
            payload = recv_json(conn)
            if payload is None:
                break
            typ = payload.get('type')
            if typ == 'message':
                text = payload.get('text','')
                broadcast(username, text)
            elif typ == 'private':
                target = payload.get('to')
                text = payload.get('text','')
                ok = send_private(username, target, text)
                if not ok:
                    send_system(conn, f'user {target} not found')
            elif typ == 'list':
                with lock:
                    send_json(conn, {'type': 'list', 'users': list(clients.keys())})
            elif typ == 'quit':
                break
            else:
                send_system(conn, 'unknown_type')

    except Exception as e:
        print('Client error:', e)
    finally:
        if username:
            remove_client(username)
            broadcast('SYS', f'--- {username} has left the chat ---')
        try:
            conn.close()
        except:
            pass

# ---------------- Server main ----------------
def start_server(host=HOST, port=PORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(100)
    print(f'Server listening on {host}:{port}')
    try:
        while True:
            conn, addr = sock.accept()
            print('Connection from', addr)
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print('Server shutting down...')
    finally:
        sock.close()

if __name__ == '__main__':
    start_server()
