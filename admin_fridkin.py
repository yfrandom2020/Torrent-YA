"""
Yonathan Fridkin
Torrent project - management server file
"""
# MS = management server
import time
from socket import *
import sys
import os
import re
import sqlite3 as lite
import threading
import select

def open_port():
    """
    Find the first free port and return it
    """
    s = socket(AF_INET, SOCK_STREAM)
    s.bind(("",0))
    port = s.getsockname()[1]
    s.close()
    return port


active_nodes = 'Fridkin_Management'
files_shared = 'Fridkin_Files' # a db containing all the files peers shared
sockets = {} # a dictionary that holds a reference to the socket communicating with the client. Key -> main port, value -> socket object to this client
main_port = 9999

# import api of connection server
try:
    import Connection_Server.Api as Api
except ModuleNotFoundError:
    import Api

class Management_Server:

    def __init__(self, active_nodes, files_shared, sockets, main_port):
        self.active_nodes = active_nodes # db
        self.files_shared = files_shared # db
        self.sockets = sockets # dicionary
        self.main_port = main_port
        self.response = ""
        self.main()


    def main(self):
        """
        Main function of MS - wait for new connections from new nodes   
        """
        # start by creating a db of active nodes
        self.update_connections_server()
        self.initiate_dbs()
        conn = lite.connect(self.active_nodes)
        ip = gethostbyname(gethostname()) 
        MS = socket(AF_INET, SOCK_STREAM)
        MS.bind((ip,self.main_port))
        MS.listen(5)
        # now is the MS main loop. The MS waits for new connections and for each creates a thread   
        while True:
            node_sock, addr = MS.accept()
            print(f"received new connection from {addr}")
            data = node_sock.recv(1024).decode('utf-8')
            client_port = int(data.split('\n')[1])
            self.sockets[client_port] = node_sock
            conn.execute("INSERT INTO nodes (ip,main_port,files) VALUES (?,?,?)", (addr[0],client_port,"")) # insert IP upon first connection
            conn.commit()
            threading.Thread(target=self.node_con, daemon=True, args=(node_sock, addr, client_port)).start()

    def client_update(self,node_sock):
        """
        Update client every 2 seconds about the state of active clients
        for now I have no idea how to incorporate it inside node_con so it will be a thread
        """
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()
        begin_time = time.time() # have a timer so that the number of clients will be sent to the client every 2 seconds    

        while True:
            try:
                end_time = time.time() # update client about number of active clients every 2 seconds
                if end_time - begin_time > 2:
                    begin_time = time.time()
                    number = c.execute("SELECT * FROM nodes").fetchall()
                    active_clients = f"Clients num\n{str(len(number))}"
                    node_sock.send(active_clients.encode('utf-8'))
            except:
                return  

    def share(self,file_name, node_sock, client_port):
        """
        This is the function that's called when a client requests to upload a file to the web
        The client has sent to the server the share command along with the file name
        file name is the long form -> a file's path C:..
        """
        print("In share")
        print(f"the file name requested is")
        print(file_name)
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()

        conn2 = lite.connect(self.files_shared)
        c2 = conn2.cursor()
        new_file = r'{}'.format(file_name)
        peer_ip = conn.execute("SELECT ip FROM nodes WHERE main_port = (?)", (client_port,)).fetchall()[0][0] # get the ip of the peer who asks to share a file
        # begin by validating the requested file has not been shared already
        all_files = c2.execute("SELECT file from files").fetchall()
        if new_file.split('\\')[-1] in all_files and len(all_files) != 0: # if the file has been shared already, deny request
            response = "nack".encode('utf-8')
            node_sock.send(response)
            return
        
        # file has not been shared, send the client the list of other clients and wait for an update
        all_clients = conn.execute("SELECT * FROM nodes WHERE main_port != (?)",(client_port,)).fetchall()
        if len(all_clients) > 0:
            clients = f"clients - share \n{file_name}"
            for client in all_clients:
                clients += '\n'+(str(client[0]) + "," + str(client[1]))
            node_sock.send(clients.encode('utf-8'))
        else:
            reponse = "nack".encode('utf-8')
            node_sock.send(reponse)   
            return 

        # after the list of clients has been sent to the client we should wait for an update response
        # if one is not received the server will go over the clients he shared  

        readable, writable, exceptional = select.select([node_sock], [], [],2)
        if readable:
            data = node_sock.recv(1024).decode('utf-8')
            print(f"data received is: {data}")
            if data != "None":
                conn2.execute("INSERT INTO files (file, main_port, ip) VALUES (?,?,?)", (new_file.split('\\')[-1],client_port, peer_ip))
                conn2.commit()
                clients = data.split('\n') # the client will send the info (ip and main port) of clients he successfuly shared the files with
                for client in clients:
                    if client == "": break
                    client_ip = re.findall(r'\d+\.\d+\.\d+\.\d+',client)[0]
                    the_client_port = int(re.findall(r'\d+',client)[-1])
                    updated_data = conn.execute("SELECT files FROM nodes WHERE ip = (?) AND main_port = (?)", (client_ip, the_client_port)).fetchall()[0][0] + "\n" + file_name.split('\\')[-1] + f"-{clients.index(client)}" # maybe use fetchall if doesn't work
                    conn.execute("UPDATE nodes SET files = ? WHERE ip = ? AND main_port = ?",(updated_data, client_ip, the_client_port))
                    conn.commit()
            else: 
                # no clients wanted the file the peer wanted to share
                # basically do nothing
                pass        
        else: # if the client did not send an update after uploading a file the MS will go over his clients and ask them if they hold the file
            for client in all_clients:
                # for each of these client query create a small thread that sends a request and waits for response
                # again with a timer of 2 seconds, and after that assuming it doesn't work
                client_ip = re.findall(r'\d+\.\d+\.\d+\.\d+',client)[0]
                the_client_port = int(re.findall('\d+',client)[-1])
                threading.Thread(target=client_file_status, daemon=True, args=(file_name, client_ip, the_client_port)).start()     

    def parts(self,file_name, node_sock, main_port):
        """
        This is the function where a client requests the other parts of a file since he only has part of it
        file_name is the abbreviated form -> test.txt
        """
        print("client asking for parts")
        # the MS needs to go over the db and return those who have parts of the file
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()
        clients = c.execute("SELECT ip,main_port FROM nodes WHERE files LIKE '%' || ? || '%' ", (file_name,)).fetchall() # select the clients that have the file
        print(f"clients are: {clients}")
        data = f"clients parts \n{file_name}"
        for client in clients:
            data += f"\n{client[0]},{client[1]}"
        print()
        print()
        print(f"final clients")
        print(data)
        node_sock.send(data.encode('utf-8'))
        return

    def disconnect(self,file_name, node_sock, main_port):
        """
        Remove user from db
        """
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()
        conn2 = lite.connect(self.files_shared)
        conn.execute("DELETE FROM nodes WHERE main_port = (?)",(main_port,))
        conn.commit()
        conn2.execute("DELETE FROM files WHERE main_port = (?)",(main_port,))
        conn2.commit()
        node_sock.close()


    def client_file_status(self,file,ip,port):
        """
        It is possible that after a client requests to share a file he will not send an update message
        For that reason the MS requests update messages from the other clients after 2 seconds
        This is a thread that is opened for each client request
        """
        try:
            conn = lite.connect(self.active_nodes)
            client_sock = sockets[port]
            query = ("parts status \n" + file).encode('utf-8')
            client_sock.send(query)
            readable, writable, exceptional = select.select([client_sock], [], [],2)
            if readable:
                answer = client_sock.recv(1024).decode('utf-8')
                if "True" in answer:
                    previous_data = conn.execute("SELECT files FROM nodes WHERE ip = (?) AND main_port = (?)",(ip,port)).fethchall() + file # client has answered positively  - add the file name to the previous data in table
                    conn.execute("UPDATE nodes SET files = ? WHERE ip = ? AND main_port = ?",(previous_data, ip, port))
                    conn.commit()
                else:
                    pass
            else: # client is probably dead, remove him
                conn.execute("DELETE FROM nodes where ip = (?) AND main_port = (?)", (ip,port))
                conn.commit()
                return
        except: 
            return

    def file_part(self, file_name, node_sock, main_port):
        """
        As a backup, give the client the info of the original peer who uploaded the file the web, in case his request of parts doesn't work
        """   
        print("inside part")
        conn2 = lite.connect(self.files_shared)
        c2 = conn2.cursor()
        data = conn2.execute("SELECT ip,main_port FROM files WHERE file LIKE '%' || ? || '%' ", (file_name,)).fetchall()[0]
        answer = f"{data[0]},{data[1]}".encode('utf-8')
        node_sock.send(answer)
        threading.Thread(target=self.bombard, daemon=True, args=(node_sock, answer)).start()
        self.response = node_sock.recv(1024).decode('utf-8')
        return        
        
    def bombard(self, node_sock, answer):
        print("inside bombard")
        while self.response == "":
            node_sock.send(answer)
            time.sleep(0.1)
        self.response = ""
        time.sleep(3)
        return    
    def node_con(self,node_sock, addr, main_port):
        """
        This is a thread function that runs for each new connection with node   
        send data of online clients upon connection
        main_port is port of client
        """
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()
        conn2 = lite.connect(self.files_shared)
        c2 = conn2.cursor()
        
        client_status = threading.Thread(target=self.client_update, daemon=True, args=(node_sock,)) # a thread that updates the client about the current number of online clients, for graphics
        client_status.start()
        requests = {"share": self.share, "parts": self.parts, "dis": self.disconnect, "file part": self.file_part} # a dictionary that for each possible request client makes holds an address of a function that executes it
        while True:
            # now main connection can run - things like requests to share and such
            data = node_sock.recv(1024).decode('utf-8')
            print(f"Inside the connection with {main_port}")
            print("received new data...")
            print(data)
            if not data.split('\n')[0] in requests.keys(): # invalid request - client didn't send his main port and didn't request valid thing
                print("Invalid request")
                node_sock.send(("Invalid request").encode('utf-8')) 
            else:
                requests[data.split('\n')[0]](data.split('\n')[1], node_sock, main_port) # call the right function with the parameter  
        return
                
    def initiate_dbs(self):
        """
        Initiate a SQL db that holds the active connections
        Initiate a SQL db that holds the files sent between nodes
        """
        conn = lite.connect(self.active_nodes)
        c = conn.cursor()
        conn2 = lite.connect(self.files_shared)
        c2 = conn2.cursor()    
        
        try:
            # Each node has a socket based connection and therefore the port used by MS is the identifying in the SQL table
            c.execute("""CREATE TABLE nodes(
            ip text,
            main_port integer,
            files text
            )""")

            c2.execute("""CREATE TABLE files(
            file text,
            main_port integer,
            ip text
            )""") # a simple table containing all the files that have been uploaded to the web along with who uploaded them
        except:
            pass   
        return

    def update_connections_server(self) -> None:
        """
        First the management server needs to connect to the connection server
        """
        try:
            CONNECTIONS_SERVER = (gethostbyname(gethostname()), 11000)
            TCP_sock = socket(AF_INET, SOCK_STREAM)
            TCP_sock.connect(CONNECTIONS_SERVER)
            
            process_result = Api.Methods_API.set(TCP_sock, "FRIDKIN", (gethostbyname(gethostname()), self.main_port))
            if not process_result:
                raise 'Error in API'

            while True:

                # Finish handshake
                data = TCP_sock.recv(1024).decode('utf-8')
                if data == 'Fin':
                    TCP_sock.close()
                    break

        except ConnectionRefusedError:
            print("Error occurred, maybe main server is not online.")

        except Exception as e:
            raise e    


if __name__ == '__main__':
    management_server = Management_Server(active_nodes, files_shared, sockets, main_port)