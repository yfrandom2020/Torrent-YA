# By Daniel Sapojnikov, start 8.4.2023.
# Class connections' server, the purpose of this server is to provide connections to clients across the network.


# MODULES

import ast
import os
import re
import sqlite3 as sl
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from socket import *
from threading import Thread
from typing import Tuple

# Important utils
ADDRESS = (gethostbyname(gethostname()), 11000)
FILTER_REG = r'[^\w\n|.]'
IP_REG = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?=\s|\Z)'


def server_credentials():
    """
    RETURNS: the credentials of the server -> (IP, PORT)
    1. uses subprocess to fetch the ip + string manipulation.
    2. uses the following 'port' code in order to find the first OPEN port on the device - (SERVER).
    """

    data = subprocess.check_output('ipconfig').decode('utf-8')
    data = re.sub(FILTER_REG, '', data)

    k = data.index("IPv4Address") + 1  # the index of the ip address.
    ip = re.search(IP_REG, data[k: data.index('\n', k)])
    ip = ip.group(0) if ip is not None else None

    # PORT
    scan_socket = socket(AF_INET, SOCK_STREAM)
    scan_socket.bind(("", 0))
    scan_socket.listen(1)

    port = scan_socket.getsockname()[1]
    scan_socket.close()

    return ip, port


# --- SERVER CLASS ---

class Graphics:
    pass


@dataclass
class Server:
    # Class variables.
    BUFSIZE = 1024

    # Fields.
    db: str
    nodes: int
    sock: socket
    gui: Graphics
    address: tuple
    online_servers: dict = field(default_factory=dict)

    def __init__(self) -> None:

        self.db = 'server_data_base.db'
        self.create_db()

        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.bind(ADDRESS)
        self.sock.listen(5)
        print("Connections server online, listening for requests at: ", self.sock.getsockname())
        
        while True:
        
            # 'GET' / 'POST' requests for clients who want to fetch the desired server.
            req_sock, addr = self.sock.accept()
            
            print(f"Connection with: {addr}")
            server_requests = Thread(target=self.handle_requests, daemon=True, args=(req_sock, addr))
            server_requests.start()

    def handle_requests(self, sock, addr) -> None:

        while True:

            # catch type of request.
            try:
                data = sock.recv(Server.BUFSIZE).decode('utf-8').replace(' ', '')
                if not data:
                    break
                if 'POST:' in data:

                    modified_data = data.replace('POST:', '').split('-')
                    server_name = str(modified_data[0])
                    server_address = ast.literal_eval(modified_data[1])
                    self.insert_server(server_name, str(server_address))

                    # Tell the server that we updated the date base.
                    sock.send('Fin'.encode('utf-8'))

                elif 'GET:' in data:
                    data = data.replace('GET:', '')
                    server = data.strip()

                    # Get the servers address.
                    server_address = self.get_server(server)

                    # Send it to the client.
                    sock.send(f'{server} AT {server_address}'.encode('utf-8'))

            except Exception as e:
                raise e

    def create_db(self) -> None:

        """
        Gets the self object
        :Creates a database with the next format. <SERVER NAME> <ADDRESS>

        $ Purpose $ :When a server is up, he sends a POST request (function) to this server, saying that he is up
        with his IP,PORT :This server will update the database so that upcoming clients will get redirected from
        this server using the GET request (function) & database to their desired server.
        """

        try:
            entry = sl.connect(self.db)
            cursor = entry.cursor()
            cursor.execute("""CREATE TABLE servers (
                SERVER text,
                ADDRESS text,
                REGISTERED text
                )"""
                           )
            entry.commit()
            entry.close()

        except sl.OperationalError:
            return
            #print("Table already exists")

        except Exception as e:
            raise e

    def show(self) -> None:
        try:
            entry = sl.connect(self.db)
            cursor = entry.cursor()

            for name, cred in {row[0]: row[1:] for row in cursor.execute('''SELECT * FROM servers''')}.items():  # --- server credentials --- #
                print(f'{name} --- {cred[0]} at {cred[1]}')
        except Exception as e:
            raise e

    def insert_server(self, server: str, address: str) -> None:
        try:
            entry = sl.connect(self.db)
            cursor = entry.cursor()
            
            # check if server is already in DB
            query = f'''SELECT 1 FROM servers WHERE SERVER = "{server}" LIMIT 1'''
            check = cursor.execute(query).fetchone()
            if check: 
                
                print(f"Server: {server} already inside DB")
                
                cursor.close()
                entry.close()
                return
            
            # registered time
            today = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''INSERT INTO servers VALUES(?, ?, ?)''', (server, address, today))  # inserting

            # finishing the work.
            entry.commit()
            entry.close()
            
        except Exception as e: 
            raise e

    # return the server based on the name.
    def get_server(self, name: str) -> Tuple[str, int]:
        try:
            entry = sl.connect(self.db)
            cursor = entry.cursor()

            # Fetch the desired server.
            query = f'''SELECT * FROM servers WHERE SERVER = "{name}"'''
            server_data = cursor.execute(query).fetchone()[1]
            
            # Close the cursor & con
            cursor.close()
            entry.close()
            return server_data
        
        except Exception as e:
            raise e

    def gui_loop(self) -> None:
        pass

    def __hash__(self) -> None:
        pass


if __name__ == '__main__':
    # Define the server.
    connections_server = Server()
