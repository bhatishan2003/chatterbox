# Chatterbox <!-- omit in toc -->

A simple socket-based chat app with login, broadcast, and private messaging.

![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)
[![License](https://img.shields.io/github/license/bhatishan2003/chatterbox)](LICENSE)

## Table of Contents <!-- omit in toc -->

- [Installation](#installation)
  - [Clone the repository:](#clone-the-repository)
- [Usage](#usage)
  - [1. Start the Server](#1-start-the-server)
  - [2. Start the Client](#2-start-the-client)
- [Testing](#testing)

## Installation

1. **Create a Virtual Environment [Optional, but recommended]**

   Run the following command to create a [virtual environment](https://docs.python.org/3/library/venv.html):

   ```bash
   python -m venv .venv
   ```

   - **Activate:**

     - **Windows (PowerShell):**

     ```bash
     .venv\Scripts\activate
     ```

     - **Linux/Mac (Bash):**

     ```bash
     source .venv/bin/activate
     ```

   - **Deactivate:**
     ```bash
     deactivate
     ```

### Clone the repository:

```bash
git clone https://github.com/bhatishan2003/chatterbox.git
cd chatterbox
```

- Install the package:

  ```bash
  pip install .
  ```

- For development (editable mode):

  ```bash
  pip install -e .
  ```

## Usage

### 1. Start the Server

- Open first termina run the server on the default port (`9009`) :

  ```bash
  chatterbox --server
  ```

### 2. Start the Client

- Open two more terminals and run the client and connect to the server (default: `127.0.0.1:9009`):

  ```bash
  python -m chatterbox.client
  ```

## Testing

Run all tests:

```bash
pytest -v
```
