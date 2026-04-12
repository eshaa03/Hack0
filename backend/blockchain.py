import hashlib
import json
import os
from typing import Dict, List
from datetime import datetime

class BlockchainLedger:
    def __init__(self):
        self.filename = os.path.join(os.path.dirname(__file__), 'blockchain_ledger.json')
        self.ledger: Dict[str, str] = {}  # hash -> timestamp
        self.chain = []
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.ledger = data.get('ledger', {})
                    self.chain = data.get('chain', [])
            except Exception as e:
                print(f"Failed to load ledger: {e}")

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump({'ledger': self.ledger, 'chain': self.chain}, f)
        except Exception as e:
            print(f"Failed to save ledger: {e}")

    def add_hash(self, data_hash: str) -> str:
        timestamp = datetime.now().isoformat()
        self.ledger[data_hash] = timestamp
        self.chain.append({'hash': data_hash, 'timestamp': timestamp})
        self.save()
        return timestamp

    def verify_hash(self, data_hash: str) -> bool:
        self.load() # sync with latest
        return data_hash in self.ledger

    def compute_sha3_hash(self, data: bytes) -> str:
        return hashlib.sha3_256(data).hexdigest()

ledger = BlockchainLedger()
