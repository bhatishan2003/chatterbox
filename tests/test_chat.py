import threading
import time
import socket
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from io import StringIO
import chatterflow
from chatterflow import server, client, cli


# ---------------- Fixtures ----------------
@pytest.fixture(scope="module")
def temp_users_file(tmp_path_factory):
    """Provide isolated users.json path for tests."""
    temp_file = tmp_path_factory.mktemp("data") / "users.json"
    chatterflow.env.CHATTERFLOW_USERS_FILE_PATH = str(temp_file)
    return temp_file


@pytest.fixture(scope="module")
def run_server(temp_users_file):
    """Run chat server in background thread."""
    t = threading.Thread(target=server.start_server, kwargs={"host": "127.0.0.1", "port": 9020}, daemon=True)
    t.start()
    time.sleep(1)
    yield


# ---------------- Helpers ----------------
def drain_until(conn, condition, limit=10):
    """Keep reading until condition(msg) is True or fail."""
    messages = []
    for _ in range(limit):
        try:
            msg = server.recv_json(conn)
            if msg is None:
                break
            messages.append(msg)
            if condition(msg):
                return msg
        except Exception:
            break
    pytest.fail(f"Expected message not found. Received messages: {messages}")


def drain_messages(conn, count=5):
    """Read multiple messages and return them."""
    messages = []
    for _ in range(count):
        try:
            msg = server.recv_json(conn)
            if msg is None:
                break
            messages.append(msg)
        except Exception:
            break
    return messages


# ---------------- Unit tests ----------------
def test_hash_and_verify_password():
    pw = "pw123"
    salt, hashed = server.hash_password(pw)
    assert server.verify_password(pw, salt, hashed)
    assert not server.verify_password("wrong", salt, hashed)


def test_send_and_recv_json():
    s1, s2 = socket.socketpair()
    data = {"hello": "world"}
    server.send_json(s1, data)
    received = server.recv_json(s2)
    assert received == data
    s1.close()
    s2.close()


# ---------------- Integration tests ----------------
def test_register_and_login(run_server):
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)  # welcome

    # Register user
    server.send_json(conn, {"action": "register", "username": "alice", "password": "pw123"})
    resp = server.recv_json(conn)
    assert resp.get("status") == "ok"
    conn.close()

    # Login
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)
    server.send_json(conn, {"action": "login", "username": "alice", "password": "pw123"})
    resp = server.recv_json(conn)
    assert resp.get("status") == "ok"
    conn.close()


def test_broadcast_message(run_server):
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)  # welcome message
    server.send_json(conn, {"action": "login", "username": "alice", "password": "pw123"})
    server.recv_json(conn)  # login response

    # Drain the "joined chat" system message
    drain_until(conn, lambda m: m.get("type") == "broadcast" and "joined the chat" in m.get("text", ""))

    # Now send actual message
    server.send_json(conn, {"type": "message", "text": "hello world"})

    # Look for the broadcast message we just sent
    msg = drain_until(
        conn, lambda m: m.get("type") == "broadcast" and m.get("from") == "alice" and "hello world" in m.get("text", "")
    )
    assert msg["from"] == "alice"
    assert "hello world" in msg["text"]
    conn.close()


def test_private_message_and_list(run_server):
    # Connect alice
    u1 = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(u1)  # welcome
    server.send_json(u1, {"action": "login", "username": "alice", "password": "pw123"})
    server.recv_json(u1)  # login response
    # Drain alice's join message
    drain_until(u1, lambda m: m.get("type") == "broadcast" and "joined the chat" in m.get("text", ""))

    # Connect and register bob
    u2 = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(u2)  # welcome
    server.send_json(u2, {"action": "register", "username": "bob", "password": "pw456"})
    server.recv_json(u2)  # register response
    u2.close()

    # Connect bob again to login
    u2 = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(u2)  # welcome
    server.send_json(u2, {"action": "login", "username": "bob", "password": "pw456"})
    server.recv_json(u2)  # login response

    # Both users should see bob's join message
    drain_until(
        u1, lambda m: m.get("type") == "broadcast" and "bob" in m.get("text", "") and "joined the chat" in m.get("text", "")
    )
    drain_until(
        u2, lambda m: m.get("type") == "broadcast" and "bob" in m.get("text", "") and "joined the chat" in m.get("text", "")
    )

    # Bob sends private message to alice using proper format
    server.send_json(u2, {"type": "private", "to": "alice", "text": "hi alice"})

    # Alice should receive the private message
    msg = drain_until(u1, lambda m: m.get("type") == "private" and "hi alice" in m.get("text", ""))
    assert msg["from"] == "bob"
    assert "hi alice" in msg["text"]

    # Bob requests user list
    server.send_json(u2, {"type": "list"})
    msg = drain_until(u2, lambda m: m.get("type") == "list")
    users = msg.get("users", [])
    assert "alice" in users
    assert "bob" in users

    u1.close()
    u2.close()


def test_invalid_command(run_server):
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)  # welcome
    server.send_json(conn, {"action": "login", "username": "alice", "password": "pw123"})
    server.recv_json(conn)  # login response
    # Drain join message
    drain_until(conn, lambda m: m.get("type") == "broadcast" and "joined the chat" in m.get("text", ""))

    # Send invalid message type
    server.send_json(conn, {"type": "unknown_type", "data": "test"})
    msg = drain_until(conn, lambda m: m.get("type") == "system")
    assert "unknown" in msg.get("text", "").lower()
    conn.close()


def test_duplicate_username_registration(run_server):
    """Test registering with existing username"""
    # First registration
    conn1 = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn1)
    server.send_json(conn1, {"action": "register", "username": "duplicate", "password": "pw123"})
    resp1 = server.recv_json(conn1)
    assert resp1.get("status") == "ok"
    conn1.close()

    # Try to register same username
    conn2 = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn2)
    server.send_json(conn2, {"action": "register", "username": "duplicate", "password": "pw456"})
    resp2 = server.recv_json(conn2)
    assert resp2.get("status") == "error"
    assert resp2.get("message") == "username_taken"
    conn2.close()


def test_invalid_credentials_login(run_server):
    """Test login with wrong password"""
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)
    server.send_json(conn, {"action": "login", "username": "alice", "password": "wrongpw"})
    resp = server.recv_json(conn)
    assert resp.get("status") == "error"
    assert resp.get("message") == "invalid_credentials"
    conn.close()


def test_nonexistent_user_login(run_server):
    """Test login with non-existent user"""
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)
    server.send_json(conn, {"action": "login", "username": "nonexistent", "password": "pw123"})
    resp = server.recv_json(conn)
    assert resp.get("status") == "error"
    assert resp.get("message") == "invalid_credentials"
    conn.close()


def test_private_message_to_nonexistent_user(run_server):
    """Test sending private message to non-existent user"""
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)
    server.send_json(conn, {"action": "login", "username": "alice", "password": "pw123"})
    server.recv_json(conn)
    drain_until(conn, lambda m: m.get("type") == "broadcast" and "joined the chat" in m.get("text", ""))

    # Send PM to non-existent user
    server.send_json(conn, {"type": "private", "to": "nonexistent", "text": "hello"})
    msg = drain_until(conn, lambda m: m.get("type") == "system" and "not found" in m.get("text", ""))
    assert "nonexistent" in msg.get("text", "")

    conn.close()


def test_connection_error_handling():
    """Test connection error scenarios"""
    # Test recv_json with broken connection
    s1, s2 = socket.socketpair()
    s1.close()
    result = server.recv_json(s2)
    assert result is None
    s2.close()

    # Test recv_json with incomplete header
    s1, s2 = socket.socketpair()
    s1.send(b"\x00\x00")  # incomplete header
    s1.close()
    result = server.recv_json(s2)
    assert result is None
    s2.close()


def test_quit_message(run_server):
    """Test quit message handling"""
    conn = socket.create_connection(("127.0.0.1", 9020))
    server.recv_json(conn)
    server.send_json(conn, {"action": "login", "username": "alice", "password": "pw123"})
    server.recv_json(conn)
    drain_until(conn, lambda m: m.get("type") == "broadcast" and "joined the chat" in m.get("text", ""))

    # Send quit message
    server.send_json(conn, {"type": "quit"})
    # Connection should close gracefully
    time.sleep(0.5)
    conn.close()


def test_users_file_creation():
    """Test users file creation when it doesn't exist"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = os.path.join(temp_dir, "nonexistent_users.json")
        original_file = chatterflow.env.CHATTERFLOW_USERS_FILE_PATH
        chatterflow.env.CHATTERFLOW_USERS_FILE_PATH = temp_file

        try:
            users = server.load_users()
            assert users == {}

            # Save users to create the file
            test_users = {"test": {"salt": "abc", "hash": "def"}}
            server.save_users(test_users)
            assert os.path.exists(temp_file)

            loaded = server.load_users()
            assert loaded == test_users
        finally:
            chatterflow.env.CHATTERFLOW_USERS_FILE_PATH = original_file


# ---------------- CLI tests ----------------
def test_cli_server():
    """Test CLI server command"""
    with patch("chatterflow.server.start_server") as mock_server:
        with patch("sys.argv", ["chatapp", "--server"]):
            cli.main()
        mock_server.assert_called_once()


def test_cli_client():
    """Test CLI client command"""
    with patch("chatterflow.client.main") as mock_client:
        with patch("sys.argv", ["chatapp", "--client"]):
            cli.main()
        mock_client.assert_called_once()


def test_cli_help():
    """Test CLI with no arguments shows help"""
    with patch("sys.argv", ["chatapp"]):
        with patch("sys.exit") as mock_exit:
            with patch("sys.stdout", new_callable=StringIO):
                cli.main()
        mock_exit.assert_called_once_with(1)


# ---------------- Client tests ----------------
def test_client_socket_helpers():
    """Test client socket helper functions"""
    s1, s2 = socket.socketpair()
    data = {"test": "message", "number": 42}

    # Test send/recv
    client.send_json(s1, data)
    received = client.recv_json(s2)
    assert received == data

    s1.close()
    s2.close()


def test_client_recv_json_connection_error():
    """Test client recv_json with connection errors"""
    s1, s2 = socket.socketpair()
    s1.close()
    result = client.recv_json(s2)
    assert result is None
    s2.close()


def test_client_print_help():
    """Test client help function"""
    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        client.print_help()
        output = mock_stdout.getvalue()
        assert "/msg" in output
        assert "/list" in output
        assert "/help" in output
        assert "/quit" in output


@patch("socket.socket")
@patch("chatterflow.client.recv_json")
@patch("chatterflow.client.send_json")
@patch("builtins.input")
@patch("getpass.getpass")
def test_client_auth_failure(mock_getpass, mock_input, mock_send, mock_recv, mock_socket):
    """Test client authentication failure"""
    mock_conn = MagicMock()
    mock_socket.return_value = mock_conn

    # Mock input sequence
    mock_input.side_effect = ["l", "testuser"]
    mock_getpass.return_value = "testpass"

    # Mock recv responses
    welcome_msg = {"type": "system", "text": "Welcome"}
    auth_failure = {"status": "error", "message": "invalid credentials"}
    mock_recv.side_effect = [welcome_msg, auth_failure]

    with patch("sys.stdout", new_callable=StringIO):
        client.main()

    mock_conn.close.assert_called()


@patch("socket.socket")
@patch("chatterflow.client.recv_json")
@patch("chatterflow.client.send_json")
@patch("builtins.input")
@patch("getpass.getpass")
@patch("threading.Thread")
def test_client_successful_auth_and_commands(mock_thread, mock_getpass, mock_input, mock_send, mock_recv, mock_socket):
    """Test client successful auth and command handling"""
    mock_conn = MagicMock()
    mock_socket.return_value = mock_conn

    # Mock input sequence
    mock_input.side_effect = [
        "r",  # register
        "testuser",  # username
        "/help",  # help command
        "/msg alice hello",  # private message
        "/list",  # list users
        "/unknown",  # unknown command
        "/quit",  # quit
    ]
    mock_getpass.return_value = "testpass"

    # Mock recv responses
    welcome_msg = {"type": "system", "text": "Welcome"}
    auth_success = {"status": "ok", "message": "registered"}
    mock_recv.side_effect = [welcome_msg, auth_success]

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with patch("sys.stderr", new_callable=StringIO):
            client.main()

    # Verify help was printed
    output = mock_stdout.getvalue()
    assert "Commands:" in output or "/msg" in output

    # Verify various send_json calls were made
    assert mock_send.call_count >= 4  # auth + private + list + quit


@patch("socket.socket")
@patch("chatterflow.client.recv_json")
@patch("builtins.input")
@patch("getpass.getpass")
def test_client_keyboard_interrupt(mock_getpass, mock_input, mock_recv, mock_socket):
    """Test client handling keyboard interrupt"""
    mock_conn = MagicMock()
    mock_socket.return_value = mock_conn

    mock_input.side_effect = ["l", "testuser", KeyboardInterrupt()]
    mock_getpass.return_value = "testpass"

    welcome_msg = {"type": "system", "text": "Welcome"}
    auth_success = {"status": "ok", "message": "welcome"}
    mock_recv.side_effect = [welcome_msg, auth_success]

    with patch("threading.Thread"):
        with patch("sys.stdout", new_callable=StringIO):
            client.main()

    mock_conn.close.assert_called()


def test_receiver_thread_message_types():
    """Test receiver thread handling different message types"""
    s1, s2 = socket.socketpair()

    # Test different message types
    messages = [
        {"type": "system", "text": "System message"},
        {"type": "broadcast", "from": "alice", "text": "Hello everyone"},
        {"type": "private", "from": "bob", "text": "Private message"},
        {"type": "list", "users": ["alice", "bob"]},
        {"type": "unknown", "data": "unknown message"},
        None,  # End connection
    ]

    def send_messages():
        for msg in messages[:-1]:  # Don't send None
            client.send_json(s1, msg)
        s1.close()

    # Start sender thread
    sender = threading.Thread(target=send_messages)
    sender.start()

    with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
        with patch("sys.exit"):
            client.receiver_thread(s2)

    output = mock_stdout.getvalue()
    assert "[SYSTEM]" in output
    assert "[alice]" in output
    assert "[PRIVATE from bob]" in output
    assert "[USERS]" in output
    assert "[UNKNOWN]" in output

    sender.join()
    s2.close()
