# chatapp/cli.py
import argparse
import sys

from . import server, client


def main():
    parser = argparse.ArgumentParser(prog="chatapp", description="Multi-client chat app with authentication")
    parser.add_argument("--server", action="store_true", help="Run the chat server")
    parser.add_argument("--client", action="store_true", help="Run the chat client")
    args = parser.parse_args()

    if args.server:
        server.start_server()
    elif args.client:
        client.main()
    else:
        parser.print_help()
        sys.exit(1)
