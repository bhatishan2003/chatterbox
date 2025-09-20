Usage
=====

1. Start the Server
-------------------

Open a terminal and run the following command to start the chat server on the default host (`127.0.0.1`) and port (`9009`):

.. code-block:: bash

    chatterflow --server

2. Start the Client
-------------------

Open one or more new terminals and run the following command to connect a client to the server:

.. code-block:: bash

    chatterflow --client

Commands
--------

The client supports the following commands:

+---------------------------+------------------------------+
| Command                   | Description                  |
+===========================+==============================+
| ``/msg <user> <message>`` | Send a private message.      |
+---------------------------+------------------------------+
| ``/list``                 | List all online users.       |
+---------------------------+------------------------------+
| ``/help``                 | Show this help message.      |
+---------------------------+------------------------------+
| ``/quit``                 | Disconnect from the server.  |
+---------------------------+------------------------------+
