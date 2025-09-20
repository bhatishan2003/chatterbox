.. chatterflow documentation master file, created by
   sphinx-quickstart on Wed Sep 17 15:21:20 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to chatterflow's documentation!
======================================

**chatterflow** is a simple, terminal-based chat application with user authentication and private messaging, built with Python sockets.

Features
--------

*   **User Authentication:** Secure registration and login system.
*   **Password Hashing:** Passwords are securely hashed using PBKDF2.
*   **Public Chat:** Broadcast messages to all connected users.
*   **Private Messaging:** Send private messages to specific users.
*   **User List:** View a list of all online users.
*   **Multi-client Support:** The server uses threading to handle multiple clients concurrently.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   test
   modules
   api
