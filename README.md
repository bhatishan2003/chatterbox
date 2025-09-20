# chatterflow

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
[![License](https://img.shields.io/github/license/bhatishan2003/chatterflow)](LICENSE)
[![Python CI](https://github.com/bhatishan2003/chatterflow/actions/workflows/python-app.yml/badge.svg)](https://github.com/bhatishan2003/chatterflow/actions/workflows/python-app.yml)
[![Build and Deploy Sphinx Docs](https://github.com/bhatishan2003/chatterflow/actions/workflows/sphinx.yml/badge.svg)](https://github.com/bhatishan2003/chatterflow/actions/workflows/sphinx.yml)

A simple, terminal-based chat application with user authentication and private messaging, built with Python sockets.

## Features

- **User Authentication:** Secure registration and login system.
- **Password Hashing:** Passwords are securely hashed using PBKDF2.
- **Public Chat:** Broadcast messages to all connected users.
- **Private Messaging:** Send private messages to specific users.
- **User List:** View a list of all online users.
- **Multi-client Support:** The server uses threading to handle multiple clients concurrently.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.11 or higher

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/bhatishan2003/chatterflow.git
    cd chatterflow
    ```

2.  **Create and activate a virtual environment (recommended):**

    - **Windows:**

      ```bash
      python -m venv .venv
      .venv\Scripts\activate
      ```

    - **macOS & Linux:**
      ```bash
      python -m venv .venv
      source .venv/bin/activate
      ```

3.  **Install the package:**

    - For regular use:

      ```bash
      pip install .
      ```

    - For development (editable mode):
      ```bash
      pip install -e .
      ```

## Usage

### 1. Start the Server

Open a terminal and run the following command to start the chat server on the default host (`127.0.0.1`) and port (`9009`):

```bash
chatterflow --server
```

### 2. Start the Client

Open one or more new terminals and run the following command to connect a client to the server:

```bash
chatterflow --client
```

## Commands

The client supports the following commands:

| Command                 | Description                 |
| ----------------------- | --------------------------- |
| `/msg <user> <message>` | Send a private message.     |
| `/list`                 | List all online users.      |
| `/help`                 | Show this help message.     |
| `/quit`                 | Disconnect from the server. |

## Testing

To run the test suite, execute the following command:

```bash
pytest -v
```

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
