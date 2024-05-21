HEADER_LENGTH = 64
FORMAT = 'utf-8'

CONNECTION_TIMEOUT = 1
LEASE_TIMEOUT = 1

SERVER_ADDRESSES = [
    ('localhost', 5000),
    ('localhost', 5001),
    ('localhost', 5002),
]

MEMORY_SIZE = 300

# communication message status
SUCCESS = 0
ERROR = 1
INVALID_ADDRESS = 2
INVALID_OPERATION = 3

# internal message status
NON_LOCAL = -1