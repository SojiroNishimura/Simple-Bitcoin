import json
from time import time


class Block:
    def __init__(self, transaction, previous_block_hash):
        self.timestamp = time()
        self.transaction = transaction
        self.previous_block = previous_block_hash

    def to_dict(self):
        d = {
            'timestamp': self.timestamp,
            'transaction': json.dumps(self.transaction),
            'previous_block': self.previous_block,
        }
        return d


class GenesisBlock(Block):
    def __init__(self):
        super().__init__(transaction='AD9B477B42B22CDF18B1335603D07378ACE83561D8398FBFC8DE94196C65D806', previous_block_hash=None)

    def to_dict(self):
        d = {
            'transaction': self.transaction,
            'genesis_block': True,
        }
        return d

