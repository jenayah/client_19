import sys
import os

# Ensure parent directory is in path for legacy rpc.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .rpc import JSONRPCClient

class Session:
    def __init__(self):
        self.client = JSONRPCClient("http://localhost:8069")
        self.user_info = {}
        self.is_authenticated = False

    def connect(self, url, db, login, password):
        self.client = JSONRPCClient(url)
        try:
            self.user_info = self.client.authenticate(db, login, password)
            self.is_authenticated = True
            return True
        except Exception as e:
            self.is_authenticated = False
            raise e

    def list_db(self, url):
        import requests
        import json
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": "db", "method": "list", "args": []},
            "id": 1
        }
        try:
            response = requests.post(f"{url}/jsonrpc", json=payload, timeout=5)
            return response.json().get('result', [])
        except:
            return []

session = Session()
