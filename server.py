import argparse
import socket
import threading
import time
from typing import Dict, List, Optional, Union

PORT = 2222

# ANSI escape code to clear the screen
ANSI_CLEAR_SCREEN = "\x1b[2J\x1b[H"
SPINNER_ANIMATION_FRAMES = ["|", "/", "-", "\\"]


class Client:

    def __init__(self, name: str, soc_client: socket.socket, is_host: bool = False) -> None:
        self.name: str = name
        # Socket of the client
        self.soc_client: socket.socket = soc_client
        # Client can be a host if he/she started the room
        self.is_host: bool = is_host


class Room:

    def __init__(self, room_name: str) -> None:
        # Unique identifier of the room - clients can join with this
        self.room_name: str = room_name
        # Indicates wheather the room has already started the estimation session or not
        self.session_started: bool = False
        # Clients participating in the estimation session
        self.clients: Dict[str, Client] = {}
        # Estimations of the clients for a single round
        self.estimations_for_round: Dict[int, Dict[str, Union[int, str]]] = {}

    def add_client(self, client: Client) -> None:
        self.clients[client.name] = client

    def get_client(self, client_name: str) -> Union[Client, None]:
        if self.exist_client(client_name):
            return self.clients[client_name]
        else:
            return None

    def get_other_clients(self, client: Client) -> List[Client]:
        other_clients = []
        for client_name, _ in self.clients.items():
            if client_name != client.name:
                other_clients.append(self.clients[client_name])
        return other_clients

    def exist_client(self, client_name: str) -> bool:
        return client_name in self.clients

    def remove_client(self, client_name: str) -> None:
        if self.exist_client(client_name):
            del self.clients[client_name]


class RoomManager:

    def __init__(self, max_nb_rooms: int) -> None:
        self.max_nb_rooms: int = max_nb_rooms
        self.rooms: Dict[str, Room] = {}

    def add(self, room: Room) -> None:
        if len(self.rooms) < self.max_nb_rooms:
            self.rooms[room.room_name] = room
        else:
            raise Exception("Too many rooms")

    def exist(self, room_name: str) -> bool:
        return room_name in self.rooms

    def get(self, room_name: str) -> Room:
        if self.exist(room_name):
            return self.rooms[room_name]
        else:
            raise Exception("Room does not exist")


# Define a dictionary to store rooms and their clients
room_manager = RoomManager(5)


def send_message(clients: Union[Client, List[Client], Dict[str, Client], socket.socket, List[socket.socket]], message):
    if isinstance(clients, dict):
        clients = list(clients.values())

    if not isinstance(clients, list):
        clients = [clients]    # type: ignore

    for client in clients:    # type: ignore
        if isinstance(client, Client):
            client.soc_client.send(message.encode())
        else:
            client.send(message.encode())


def receive_message(client: Union[Client, socket.socket], message: Optional[str]):
    if message is not None:
        send_message(client, message)
    if isinstance(client, Client):
        return client.soc_client.recv(1024).strip().decode()
    else:
        return client.recv(1024).strip().decode()


def handle_room_join_and_creation(soc_client: socket.socket):
    send_message(soc_client, ANSI_CLEAR_SCREEN)
    send_message(soc_client, "Welcome to the planning poker server!\n")

    room_number = receive_message(soc_client, "Enter the room number you want to join: ")

    # If the user creates the room, then he/she will be the host
    is_user_host: bool = False

    if room_manager.exist(room_number):
        room = room_manager.get(room_number)
        if room.session_started:
            send_message(soc_client, "The session has already started. Please try again later.\n")
            return
        send_message(soc_client, f"Joined room {room_number}.\n")
    else:
        room = Room(room_number)
        room_manager.add(room)
        print(f"Created room {room_number}.")
        send_message(soc_client, f"Room {room_number} created where you are the host.\n")
        is_user_host = True

    client_name = receive_message(soc_client, "Entry your name: ")
    client = Client(client_name, soc_client, is_user_host)
    room.add_client(client)
    print(f"Client {client_name} joined room {room_number}.")
    send_message(room.get_other_clients(client), f"{client.name} joined the room.\n")

    if client.is_host:
        started_input = ""
        while started_input != "start":
            started_input = receive_message(
                client, f"Type 'start' anytime to begin the session (wait for the other players).\n")
        if started_input == "start":
            room.session_started = True
            send_message(room.clients, ANSI_CLEAR_SCREEN)
            print(f"Session started for rooom {room.room_name}.")
    else:
        send_message(client, "Waiting for host to start the session...\n")
        while not room.session_started:
            for f in SPINNER_ANIMATION_FRAMES:
                time.sleep(0.5)
                send_message(client, f"\r{f}")
        send_message(client, "\n")

    handle_game(room, client)


def handle_game(room: Room, client: Client):
    round_cntr = 0

    while True:
        round_cntr += 1
        room.estimations_for_round[round_cntr] = {}

        send_message(client, f"+++ Round {round_cntr} +++\n")
        estimate = receive_message(client, "Enter your estimate: ")

        if estimate == "exit":
            send_message(client, "\nBye bye!\n")
            send_message(room.get_other_clients(client), f"\n{client.name} left the room.\n")
            room.remove_client(client.name)
            # Let's terminate the thread for this client
            return

        # send_message(room.get_other_clients(client), f"\n{client.name} estimated.\n")
        room.estimations_for_round[round_cntr][client.name] = estimate
        send_message(client, "\n")

        if len(room.estimations_for_round[round_cntr]) < len(room.clients):
            send_message(client, "Waiting for other players to estimate...")
        while len(room.estimations_for_round[round_cntr]) < len(room.clients):
            for f in SPINNER_ANIMATION_FRAMES:
                time.sleep(0.5)
                send_message(client, f"\r{f}")
        send_message(client, "\n\n")

        if len(room.estimations_for_round[round_cntr]) == len(room.clients):
            send_message(client, ANSI_CLEAR_SCREEN)
            send_message(client, f"All estimates received for Round {round_cntr}.\n\n")
            send_message(client, "Estimates are:\n")
            for client_name, estimate in room.estimations_for_round[round_cntr].items():
                send_message(client, f"- {client_name}: {estimate}\n")
            send_message(client, "Round finished.\n")
            send_message(client, "-" * 50 + "\n")
            send_message(client, "\n\n")
            time.sleep(1)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Planning poker server")
    parser.add_argument("-p", "--port", type=int, default=PORT, help="Port to listen on")
    return parser.parse_args()


def start_server(port: int):
    # Set up a socket to listen for incoming SSH connections
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)

    print(f"Server listening on port {port}...")

    while True:
        client, addr = server_socket.accept()
        print(f"Accepted connection from {addr[0]}:{addr[1]}")
        client_handler = threading.Thread(target=handle_room_join_and_creation, args=(client,))
        client_handler.start()


if __name__ == "__main__":
    args = parse_arguments()
    start_server(args.port)
