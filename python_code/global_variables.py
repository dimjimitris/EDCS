# global_variables.py
# Description: This file contains the global variables used in the project.
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

# Define global variables
HEADER_LENGTH = int(os.getenv("HEADER_LENGTH"))                                     # 64
FORMAT = os.getenv("FORMAT")                                                        # 'utf-8'               
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT"))                           # 5
LEASE_TIMEOUT = int(os.getenv("LEASE_TIMEOUT"))                                     # 3    
SERVERS = [tuple(server.split(":")) for server in os.getenv("SERVERS").split(",")]
SERVERS = [(server[0], int(server[1])) for server in SERVERS] 
MEMORY_SIZE = int(os.getenv("MEMORY_SIZE"))                                         # 300
SUCCESS = int(os.getenv("SUCCESS"))                                                 # 0      
ERROR = int(os.getenv("ERROR"))                                                     # 1
INVALID_ADDRESS = int(os.getenv("INVALID_ADDRESS"))                                 # 2
INVALID_OPERATION = int(os.getenv("INVALID_OPERATION"))                             # 3