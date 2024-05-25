# global_variables.py
# Description: This file contains the global variables used in the project.

HEADER_LENGTH = 64
FORMAT = "utf-8"

CONNECTION_TIMEOUT = 5
LEASE_TIMEOUT = 5

SERVERS = [
    ("localhost", 5000),
    ("localhost", 5001),
    ("localhost", 5002),
]

MEMORY_SIZE = 300

# communication message status
SUCCESS = 0
ERROR = 1
INVALID_ADDRESS = 2
INVALID_OPERATION = 3
