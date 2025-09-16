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

import socket
import struct
import json
import threading
import getpass
import sys

HOST = '127.0.0.1'
PORT = 9009

# ---------------- Socket helpers ----------------
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

# ---------------- Receiver thread ----------------
def receiver_thread(conn):
    try:
        while True:
            msg = recv_json(conn)
            if msg is None:
                print('\n[Disconnected]')
                break
            typ = msg.get('type')
            if typ == 'system':
                print(f"[SYSTEM] {msg.get('text')}")
            elif typ == 'broadcast':
                print(f"[{msg.get('from')}] {msg.get('text')}")
            elif typ == 'private':
                print(f"[PRIVATE from {msg.get('from')}] {msg.get('text')}")
            elif typ == 'list':
                print('[USERS] ' + ', '.join(msg.get('users', [])))
            else:
                print('[UNKNOWN]', msg)
    finally:
        conn.close()
        sys.exit(0)

# ---------------- Helpers ----------------
def print_help():
    print('Commands:')
    print('  /msg <user> <text>   private message')
    print('  /list                list users')
    print('  /help                show help')
    print('  /quit                quit')

# ---------------- Client main ----------------
def main():
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((HOST, PORT))

    welcome = recv_json(conn)
    if welcome and welcome.get('type') == 'system':
        print('[SERVER]', welcome.get('text'))

    while True:
        choice = input('Do you want to (l)ogin or (r)egister? [l/r]: ').strip().lower()
        if choice in ('l','r'):
            break
    action = 'login' if choice == 'l' else 'register'
    username = input('username: ').strip()
    password = getpass.getpass('password: ')

    send_json(conn, {'action': action, 'username': username, 'password': password})
    resp = recv_json(conn)
    if not resp or resp.get('status') != 'ok':
        print('Auth failed:', resp)
        conn.close(); return
    print('[AUTH]', resp.get('message'))

    t = threading.Thread(target=receiver_thread, args=(conn,), daemon=True)
    t.start()

    print('Type /help for commands. Start chatting!')
    try:
        while True:
            line = input()
            if not line:
                continue
            if line.startswith('/'):
                parts = line.split(' ', 2)
                cmd = parts[0].lower()
                if cmd == '/msg' and len(parts) == 3:
                    send_json(conn, {'type': 'private', 'to': parts[1], 'text': parts[2]})
                elif cmd == '/list':
                    send_json(conn, {'type': 'list'})
                elif cmd == '/help':
                    print_help()
                elif cmd == '/quit':
                    send_json(conn, {'type': 'quit'})
                    print('Quitting...')
                    break
                else:
                    print('Unknown command. Use /help')
            else:
                send_json(conn, {'type': 'message', 'text': line})
    except KeyboardInterrupt:
        send_json(conn, {'type': 'quit'})
    finally:
        conn.close()

if __name__ == '__main__':
    main()
