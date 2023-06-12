"""
Cyber project - client server
Yonathan Fridkin
"""
# MS = management server
import threading
import re
import time
import os   
import sys
from socket import *
import subprocess
from PyQt5 import *
from PyQt5.QtCore import QTimer
import sqlite3 as lite
import select
import random
import ast
from User_ui2 import *

# import api
try:
    import Connection_Server.Api as Api
except ModuleNotFoundError:
    import Api

try:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = r'C:\Users\יונתן\AppData\Local\Programs\Python\Python310\Lib\site-packages\PyQt5\Qt5\plugins'
except:
    pass    

app = QtWidgets.QApplication(sys.argv)
MainWindow = QtWidgets.QMainWindow()    

class Peer:
    
    def __init__(self):
        self.main_port = self.open_port()
        print(f"my main port is {self.main_port}")
        self.my_files = f'Fridkin_Files_Server{self.main_port}'
        self.active_clients = 0
        self.share_status = {}
        self.pending = []
        self.parts_status = {}  # a dicionary that contains a value for each of the clients that need to share a part 
        self.pending_parts = [] # a list of all parts pending
        self.GUI = Ui_MainWindow() # initiate a GUI object from the User_ui2.py file
        self.Initiate_db()
        self.timer = None
        threading.Thread(target=self.main, daemon=True).start()
        self.handle_GUI()
    
    def handle_GUI(self):
        """
        Initiate the graphics and update them according to new data
        """
        global app
        global MainWindow
        self.GUI.setupUi(MainWindow)
        self.GUI.retranslateUi(MainWindow)
        MainWindow.show()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_GUI)
        self.timer.start(2000)  # Update every 2 seconds
        sys.exit(app.exec_())

    def update_GUI(self):
        conn = lite.connect(self.my_files)
        self.GUI.update_data(self.active_clients, conn.execute("SELECT * FROM files").fetchall(), self.pending_parts)
        QTimer().singleShot(0, self.reset_timer)  # Reset the timer
    
    def reset_timer(self):
        """
        Reset the timer to trigger the update_GUI() method again
        """
        self.timer.start(2000)  # Update every 2 seconds    

        
    
    def open_port(self):
        """
        Find the first free port and return it
        """
        s = socket(AF_INET, SOCK_STREAM)
        s.bind(("",0))
        port = s.getsockname()[1]
        s.close()
        return port

    def Initiate_db(self):
        """
        The server holds a SQL db containing information about his files
        If you upload a file it is saved in the db and if you receive parts as well
        """
        conn = lite.connect(self.my_files)
        c = conn.cursor()
        try:
            c.execute("""CREATE TABLE files(
            file_path text
            )""") # a db containing all full data (path of uploaded file and path of the files received in parts)
        except:
            pass
        return 

    def temp_con(self,temp_sock):
        """
        This function actually handles the connections between peers
        """
        conn = lite.connect(self.my_files)
        c = conn.cursor()
        while True:
            data = temp_sock.recv(1024) # the initial request request
            data = data.decode('utf-8')
            print("data received")
            print(data)
            if "file share" in data: # peer asks if we are interested in file
                response = "True".encode('utf-8')
                self.pending.append(data.split('\n')[1]) # appending something like test.txt
                temp_sock.send(response)
                temp_sock.close()
                return
            elif "file upload" in data and data.split('\n')[1] in self.pending: # peer sending a file that was requested before
                name = data.split('\n')[1]
                self.pending.remove(data.split('\n')[1])
                if not "one" in data: 
                    self.pending_parts.append(name)
                else: 
                    conn.execute("INSERT INTO files (file_path) VALUES (?)",(name,))
                    conn.commit()
                content = b""
                message = temp_sock.recv(4096)
                while message != "over".encode('utf-8'):
                    content += message
                    message = temp_sock.recv(4096)
                actual_name = data.split('\n')[1].split('\\')[-1]
                new_file = open(r'{}\{}\{}'.format(os.getcwd(), self.main_port, name), 'wb+')
                new_file.write(content)
                new_file.close()
                temp_sock.close()  
                return
            elif "parts request" in data:
                print("Inside part request")
                # another peer requesting part of file both peers have
                # send the client what we have
                file_name = data.split('\n')[1]  # test.txt
                print("file is")
                print(file_name)
                all_files = conn.execute("SELECT * FROM files").fetchall()
                if file_name.split(' ')[0] in [f_name[0].split('\\')[-1].split(' ')[0] for f_name in all_files]: 
                    response = "nack".encode('utf-8')
                    temp_sock.send(response)
                    return
                
                file_size = os.stat(r'{}\{}\{}'.format(os.getcwd(), self.main_port,file_name)).st_size
                f = open(r'{}\{}\{}'.format(os.getcwd(), self.main_port, file_name), 'rb+')
                print("successfuly opened")
                parts = []
                while file_size > 0:
                    if file_size < 4096:
                        parts.append(f.read(file_size))
                        break
                    else:
                        parts.append(f.read(4096))
                        file_size -= 4096
                print("there is parts")
                for part in parts:
                    temp_sock.send(part)
                    time.sleep(0.1)
                over = "over".encode('utf-8')
                temp_sock.send(over)
                f.close()
                return

            elif "full file" in data:
                file_name = data.split('\n')[1] # the received
                all_files = conn.execute("SELECT * FROM files").fetchall()
                path = ""
                for file_path in [the_file_path[0] for the_file_path in all_files]:
                    if file_name in file_path: 
                        path = file_path
                parts = []
                open_file = open(r'{}'.format(path), 'rb+')
                size = os.stat(path).st_size 
                while size > 0:
                    if size < 4096:
                        parts.append(open_file.read(size))
                        break
                    else:
                        parts.append(open_file.read(4096))
                        size -= 4096
                for part in parts:
                    temp_sock.send(part)
                    time.sleep(0.1)
                temp_sock.send("over".encode('utf-8'))
                return               


    def main_sock_run(self):
        """
        This function handles the main socket of the client
        connections accepted by this socket are temporary connections with other peers
        Those other peers might ask if peer is interested in a part of file or request a part of file
        These are the only two options for communications between clients
        """
        main_sock = socket(AF_INET, SOCK_STREAM)
        main_sock.bind((gethostbyname(gethostname()), self.main_port))
        main_sock.listen(5)
        while True:
            temp_sock, addr = main_sock.accept()
            threading.Thread(target=self.temp_con, daemon=True, args=(temp_sock,)).start()
                
    def server(self,ms_sock):
        """
        This is the side of the server within the client-server file
        The server is the one listening to incoming messages, from MS and other clients
        It handles file sharing
        """
        conn = lite.connect(self.my_files)
        c = conn.cursor()
        # the server logic needs to listen on its main port and on it's connection with the server
        threading.Thread(target=self.main_sock_run, daemon=True).start()
        while True:
            MS_data = ms_sock.recv(1024).decode('utf-8')
            if "Clients num" in MS_data: # MS shares the number of online clients - happens every 2 seconds
                try:
                    self.active_clients = int(MS_data.split('\n')[1])
                except:
                    continue    
            elif "parts status" in MS_data: # MS asks this client whether he has a specific file - happens in case another client shared a file and didn't send a response to the MS
                if MS_data.split('\n')[1] in conn.execute("SELECT * FROM file").fetchall():
                    ms_sock.send(("True").encode('utf-8'))
                else:
                    ms_sock.send(("False").encode('utf-8'))
            elif "clients - share" in MS_data: # receiving data about sharing of file - MS sent the clients after the request of the client side to upload a file
                print("In share")
                path_of_file =  MS_data.split('\n')[1]
                print("path of file is")
                print(path_of_file)
                file_name = MS_data.split('\n')[1].split('/')[-1] # actual name - such as test.txt
                print("the file name is")
                print(file_name)
                clients = []
                for row in MS_data.split('\n')[2:]:
                    self.share_status[(row.split(',')[0], int(row.split(',')[1]))] = True # all clients
                    clients.append((row.split(',')[0], int(row.split(',')[1])))
                # now is the sharing part
                # first, the server sends the share request to all clients
                # The file will be seperated equally between the clients and sent
                for client in clients:
                    threading.Thread(target=self.client_share_request, daemon=True, args=(client,file_name)).start() # sending something like test.txt
                time.sleep(1)
                share_clients = [client for client in self.share_status.keys() if self.share_status[client]] # only the clients with value of true in the dictionary
                if len(share_clients) != 0:
                    f = open(r'{}'.format(path_of_file), 'rb+')
                    print('total data')
                    print(f.read())
                    f.seek(0)
                    size = os.stat(path_of_file).st_size // len(share_clients) 
                    for client in share_clients:
                        if share_clients[-1] == client and size*len(share_clients) < os.stat(path_of_file).st_size:
                            size += os.stat(path_of_file).st_size - size*len(share_clients)
                        parts = [] # parts contains binary chunks of the file!!
                        if size > 4096:
                            copy_size = size
                            while copy_size > 0:
                                if copy_size < 4096:
                                    parts.append(f.read(copy_size))
                                    break
                                parts.append(f.read(4096))
                                copy_size -= 4096
                        else:
                            parts.append(f.read(size)) # parts are binary
                        print("the parts sent")
                        print(parts)
                        threading.Thread(target=self.share_file, daemon=True, args=(client, parts, file_name, share_clients)).start()
                                # now send to MS an updating message about file status
                    f.close()
                    data = ""
                    for client in share_clients:   
                        data += f"{client[0]} {client[1]} \n"
                    ms_sock.send(data.encode('utf-8'))  
                    self.share_status = {}  
                    conn.execute("INSERT INTO files (file_path) values (?)",(path_of_file,)) # maybe add coma
                    conn.commit()
                else: # no clients want the file :(
                    # send "none" to MS
                    message = "None".encode('utf-8')
                    ms_sock.send(message)

            elif "clients parts" in MS_data: # MS sending the clients with parts after client asked for parts
                print("received the parts")
                file_name = MS_data.split('\n')[1] # something like test.txt
                clients = []
                open_file = open(r'{}\{}\{}'.format(os.getcwd(),self.main_port,file_name), 'rb+')
                for client in MS_data.split('\n')[2:]:
                    if client != "":
                        clients.append((client.split(',')[0], int(client.split(',')[1])))
                for client in clients:
                    self.parts_status[client] = True
                    threading.Thread(target=self.ask_part, daemon=True, args=(client, open_file, file_name, clients.index(client), clients)).start()
                    time.sleep(3)
                time.sleep(1)
                if False in [value for key, value in self.parts_status.items()]:
                    # a peer that was supposed to send his part didn't do so
                    # contact the MS and ask for the original guy
                    print("completing from others")
                    query = f"file part\n{file_name}".encode('utf-8')
                    ms_sock.send(query)
                    data = ms_sock.recv(1024).decode('utf-8') # info of client
                    while "Clients" in data:
                        data = ms_sock.recv(1024).decode('utf-8')
                    reponse = "over".encode('utf-8')
                    ms_sock.send(reponse)
                    print(data)
                    info = (data.split(',')[0], int(data.split(',')[1]))
                    special_sock = socket(AF_INET, SOCK_STREAM) 
                    special_sock.connect(info)
                    query = f"full file\n{file_name}".encode('utf-8')
                    special_sock.send(query)
                    data = b""
                    message = special_sock.recv(4096)
                    while message != "over".encode('utf-8'):
                        data += message
                        message = special_sock.recv(4096)
                    open_file.write(data)
                    open_file.close()
                    self.pending_parts.remove(file_name)   
                    conn.execute("INSERT INTO files (file_path) VALUES (?)", (r'{}\{}\{}'.format(os.getcwd(),self.main_port,file_name),)) # the path of the file inserted
                    conn.commit()
                else:
                    open_file.close() 
                    print("Inserting")
                    self.pending_parts.remove(file_name)
                    conn.execute("INSERT INTO files (file_path) VALUES (?)", (r'{}\{}\{}'.format(os.getcwd(),self.main_port,file_name),)) # the path of the file inserted
                    conn.commit()
                self.parts_status = {}    

    def ask_part(self,client, open_file, file_name, number, clients):
        """
        This is the function for a peer to ask other peers for their part of file (to complete what he has)
        number -> the client number in the array of all peers - to indicate where to write the data he sends
        file_name -> test.txt
        """
        print("inside ask part")
        self_number = -1
        for new_client in clients:
            if new_client[0] == gethostbyname(gethostname()) and new_client[1] == self.main_port: self_number = clients.index(new_client)
        if client[0] == gethostbyname(gethostname()) and client[1] == self.main_port: 
            print("immediately closing")
            return    
        peer_ip = client[0]
        peer_port = client[1]
        file_sock = socket(AF_INET, SOCK_STREAM)
        file_sock.connect((peer_ip, peer_port))
        query = f"parts request \n{file_name}".encode('utf-8')
        file_sock.send(query)
        query_number = clients.index(client)
        print("self number is")
        print(self_number)
        print("and query number is")
        print(query_number)
        response, w,e = select.select([file_sock], [], [], 5) # timeout of 5
        if response:
            print("received reponse")
            try:
                parts = [] # the parts of the message sent
                message = file_sock.recv(4096)
                if message == "nack".encode('utf-8'):
                    print("receiving denial")
                    self.parts_status[client] = False
                    return
                print("not nack")
                while message != "over".encode('utf-8'):
                    parts.append(message)
                    message = file_sock.recv(4096)
                if self_number > query_number: # 1 > 0, insert new data before the existing data, for that reverse the array
                    open_file.seek(0)
                    print("it is")
                    total_data = b""
                    for part in parts:
                        total_data += part
                    total_data += open_file.read()
                    open_file.seek(0)
                    open_file.write(total_data)   
                else:
                    open_file.seek(0)
                    print("it is not")
                    total_data = open_file.read()
                    print("total data before")
                    print(total_data)
                    for part in parts:
                        print("iteration")
                        print(total_data)
                        total_data += part
                    print("total data is now")
                    print(total_data)
                    open_file.seek(0)
                    open_file.write(total_data) 

                    print("in end")
            except error as e:
                print("in exception")
                print(e)
                self.parts_status[client] = False 
                return
                        

        else:
            # client probably disconnect
            # In that case the threads of asking peers can be terminated and the peer will go to the MS to receive the details of the original one who uploaded
            self.parts_status[client] = False 
            return

    def share_file(self,client, parts, file_name, clients):
        """
        This is a function that sends a client part of the file
        client -> info of client (ip and main port)
        parts -> parts of the file segment to fit the buffer size of receiver
        file_name -> test.txt
        """                 
        file_sock = socket(AF_INET, SOCK_STREAM)
        file_sock.connect(client)
        if len(clients) == 1:
            introduction = f"file upload\n{file_name}\none".encode('utf-8')
        else: introduction = f"file upload\n{file_name}".encode('utf-8') 
        file_sock.send(introduction)
        time.sleep(0.1)
        for part in parts:
            file_sock.send(part)
            time.sleep(0.1)
        over = "over".encode('utf-8')
        file_sock.send(over)  
        file_sock.close()  
        return

    def client_share_request(self,client, file):
        """
        Ask a specific client whether he is interested in a file or not
        The request will be pending for 5 seconds
        """  
        share_sock = socket(AF_INET, SOCK_STREAM)
        share_sock.connect(client)
        query = f"file share \n{file}"
        print("query is")
        print(query)
        query = query.encode('utf-8') 
        share_sock.send(query)
        readable, w, e = select.select([share_sock], [], [], 5)
        if readable:
            response = share_sock.recv(1024).decode('utf-8')
            if not "True" in response: self.share_status[client] = False
        else: self.share_status[client] = False  
        share_sock.close() 
        return

    def client(self,ms_sock):
        """
        This is the client side of the peer
        The client create the different requests such as to upload a file or receive parts of other files
        And the server executes these requests
        """
        conn = lite.connect(self.my_files)
        port_share = False
        while True:
            if not port_share:
                request = f"main port \n{str(self.main_port)}".encode('utf-8')
                ms_sock.send(request)
                port_share = True
            while True:
                if self.GUI.get_data() != "":
                    request = self.GUI.get_data()
                    break
                time.sleep(0.1)
            print("request changed!")
            print(request)
            if "view" in request:
                print("view in request")
                print(request)
                file_name = request[5:]
                self.Gui.view(file_name, conn.execute("SELECT * FROM files").fetchall())
            
            other_parts = [part for part in request.split(' ')[1:]]
            second_part = request[6:]
            request = f"{request.split(' ')[0]}\n{second_part}"
            print("request is")
            print(request)

            request = request.encode('utf-8')
            ms_sock.send(request)
            self.GUI.relapse_data()

    def main(self):
        # Each client will open a folder upon running that is named after his main port, and there he will save the files he gets
        ip = gethostbyname(gethostname())
        ms_sock = socket(AF_INET, SOCK_STREAM)
        # for now details of MS are hard coded
        admin = self.management_connect()
        ms_sock.connect(admin)
        os.mkdir(f'{os.getcwd()}\{self.main_port}') # create the folder with the name of main port
        thread2 = threading.Thread(target=self.client, daemon=True, args=(ms_sock,)) # client thread, only for creating requests
        thread2.start() 
        self.server(ms_sock)

    def management_connect(self) -> None:
        """
        The client needs the ip and port of admin server so he first needs to go to the connection server
        """
        TCP_sock = socket(AF_INET, SOCK_STREAM)
        TCP_sock.connect((gethostbyname(gethostname()),11000))

        # Get the address.
        process_result = Api.Methods_API.get(TCP_sock, "FRIDKIN")

        # Check if there was an Error.
        if not process_result['status']:
            raise "Error in API"

        TCP_sock.close()
        admin = ast.literal_eval(process_result['addr'])
        return admin

if __name__ == '__main__':
    peer = Peer()