import argparse
import random

import global_variables as gv
import client_logic


def main():
    parser = argparse.ArgumentParser(description="Client to connect to a memory server")
    parser.add_argument(
        "-server", type=int, help="The index of the server in the list of servers"
    )
    args = parser.parse_args()

    server_index = args.server

    server_address = random.choice(gv.SERVERS) if server_index is None else gv.SERVERS[args.server]
    client = client_logic.Client(server_address)
    client.connect()

    while True:
        try:
            user_input = input("Enter command (read <address> | write <address> <data> | disconnect): ").strip()
            if not user_input:
                continue

            user_input = user_input.split(maxsplit=2)
            command = user_input[0].lower()
            if command == "read" and len(user_input) == 2:
                mem_address = int(user_input[1])
                result = client.read(mem_address)
                print(f"Read from {mem_address}: {result}")

            elif command == "write" and len(user_input) == 3:
                mem_address = int(user_input[1])
                data = None
                try:
                    data = int(user_input[2])
                except:
                    data = user_input[2]
                result = client.write(mem_address, data)
                print(f"Write to {mem_address}: {result}")

            elif command == "disconnect":
                client.disconnect()
                break

            else:
                print("Invalid command. Please use read <address>, write <address> <data>, or disconnect.")

        except KeyboardInterrupt:
            print("\nDisconnecting due to keyboard interrupt.")
            client.disconnect()
            break
        except Exception:
            try:
                client.disconnect()
            except:
                pass

            reconnected = -1
            for index, server in enumerate(gv.SERVERS):
                try:
                    client = client_logic.Client(server)
                    client.connect()
                    reconnected = index
                    break
                except:
                    pass

            if reconnected < 0:
                print("Failed to reconnect to server. Exiting.")
                break
            else:
                print(f"Reconnected to server with index: {reconnected}.")


if __name__ == "__main__":
    main()
