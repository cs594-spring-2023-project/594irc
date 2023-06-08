''' server.py ~ Amelia Miner
'   Implements the server side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

import selectors
import socket
import threading
from time import sleep

from conf import *

class User:
    ''' represents a user with a username and a socket '''
    def __init__(self, username, sock):
        self.username = username
        self.sock = sock

class Server:
    ''' represents the server with users, rooms, and a selector '''
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.users = []
        self.rooms = {}

    def close_on_err(self, sock, err_code):
        close_on_err(sock, err_code)
        try:
            self.sel.unregister(sock)
        except KeyError:
            pass # socket already unregistered
        except ValueError:
            pass # socket already closed
        self.clean_userlist(sock)

    def accept_new_user(self, sock):
        ''' accepts a new user and adds them to the users list '''
        try:
            client_sock = None
            client_sock, client_tcpip_tuple = sock.accept()
            client_sock.settimeout(TIMEOUT)
            received_hello_bytes = client_sock.recv(IrcPacketHello.packet_length)
            username = IrcPacketHello().from_bytes(received_hello_bytes).payload
            if username in [user.username for user in self.users]:
                self.close_on_err(client_sock, IRC_ERR_NAME_EXISTS)
                return
            self.users.append(User(username, client_sock))
            self.sel.register(client_sock, selectors.EVENT_READ)
            print(f'received hello from {username} at {client_tcpip_tuple} (fd {client_sock.fileno()})')
        except IRCException as e:
            self.close_on_err(client_sock, e.err_code)
            return
        except ValueError as e:
            print('client connection at addr/port already exists')
            self.close_on_err(client_sock, IRC_ERR) # unsure...

    def add_user_to_room(self, sock, join_msg):
        try:
            # create room if it doesn't exist
            if join_msg.other not in self.rooms.keys():
                self.rooms[join_msg.other] = []
            # add user to room
            self.rooms[join_msg.other].append(sock)
            # send list of users to all users in room
            list_users_packet = IrcPacketListUsersResp() # TODO
            for room in self.rooms.keys():
                for user in self.rooms[room]:
                    #user.sendall(join_msg.to_bytes())
                    pass # TODO write and use a listusers packet
        except IRCException as e:
            self.close_on_err(sock, e.err_code)
            return

    def remove_user_from_room(self, user):
        pass # TODO

    def send_list(self, user):
        pass # TODO

    def send_msg(self, sock, msg):
        print(f'received "{msg}" from {sock.getpeername()}') # TODO
        if msg.other in self.rooms.keys():
            for user in self.rooms[msg.other]:
                #user.sendall(msg.to_bytes())
                pass # TODO write and use a tellmsg packet

    def react_to_client_err(self, user):
        pass # TODO

    def clean_userlist(self, bad_sock=None):
        self.users = [user for user in self.users if user.sock != bad_sock and user.sock.fileno() != -1]


    def send_keepalive(self, sock):
        ''' sends a keepalive packet to the given socket '''
        try:
            sock.sendall(IrcPacketKeepalive().to_bytes())
        except socket.timeout:
            print(f'connection to {sock.getpeername()} timed out')
            sock.close()
        except socket.error as e:
            print(f'KEEPALIVE THREAD: connection to fd {sock} errored: {e}')
            self.sel.unregister(sock)
            self.clean_userlist(sock)
            sock.close()

    def send_keepalives(self, main_sock):
        ''' Should be its own thread '''
        while True:
            sleep(4)
            clients = [val.fileobj for val in self.sel.get_map().values() if val.fileobj != main_sock]
            self.clean_userlist()
            for client in clients:
                self.send_keepalive(client)

    def main(self):
        ''' creates a socket to listen on, initializes rooms and users lists, and enters a loop '''
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as main_sock:
            self.sel.register(main_sock, selectors.EVENT_READ)
            main_sock.settimeout(TIMEOUT)
            main_sock.bind(('', IRC_SERVER_PORT))
            print("listening")
            main_sock.listen()
            print("looping")
            self.mainloop(main_sock)

    def mainloop(self, main_sock):
        keepalive_thread = threading.Thread(target=self.send_keepalives, args=[main_sock])
        keepalive_thread.start() # TODO handle OS errors gracefully
        while True:
            events = self.sel.select(timeout=TIMEOUT)
            for key, _ in events:
                if key.fileobj == main_sock: # new client (this should be a hello pkt)
                    self.accept_new_user(main_sock)
                else: # established client
                    # (this should be a keepalive, msg, err, join, leave, or list pkt)
                    client_sock = key.fileobj
                    this_user = None
                    for user in self.users:
                        if user.sock == client_sock:
                            this_user = user
                            break
                    if this_user is None:
                        print(f'ERROR: could not find user with socket {client_sock}')
                        continue
                    self.receive_from_client(this_user)

    def receive_from_client(self, this_user):
        ''' receives a packet from the given socket and reacts to it '''
        try:
            header_bytes = this_user.sock.recv(IrcHeader.header_length)
        except OSError as e: # tried to read from a dead connection
            if this_user.sock.fileno() != -1:
                self.sel.unregister(this_user.sock)
            self.clean_userlist(this_user.sock)
            this_user.sock.close()
            return 
        if header_bytes == b'':
            #print(f'received nothing from {this_user.sock.getpeername()}')
            return # not sure why this happens...
            # if there's no inbound traffic why does the FD get selected?
        header_obj = IrcHeader().from_bytes(header_bytes)
        if header_obj.opcode == IRC_KEEPALIVE:
            print(f'received keepalive from {this_user.sock.getpeername()}') # TODO
        elif header_obj.opcode == IRC_SENDMSG:
            packet_bytes = header_bytes + this_user.sock.recv(header_obj.length)
            msg_obj = IrcPacketSendMsg().from_bytes(packet_bytes)
            self.send_msg(this_user.sock, msg_obj)
        elif header_obj.opcode == IRC_ERR:
            print(f'received err from {this_user.sock.getpeername()}') # TODO
        elif header_obj.opcode == IRC_JOINROOM:
            print(f'received join from {this_user.sock.getpeername()}') # TODO
            self.add_user_to_room(this_user.sock)
        elif header_obj.opcode == IRC_LEAVEROOM:
            print(f'received leave from {this_user.sock.getpeername()}') # TODO
        elif header_obj.opcode == IRC_LISTROOMS:
            print(f'received listrooms from {this_user.sock.getpeername()}') # TODO
        elif header_obj.opcode == IRC_LISTUSERS:
            print(f'received listusers from {this_user.sock.getpeername()}') # TODO
        else:
            print(f'WARNING! OPCODE NOT KNOWN TO SERVER\nreceived opcode {header_obj.opcode} from {this_user.sock.getpeername()};\nnot yet implemented!')
        #this_user.sock.recv(4096) # drain buffer

if __name__ == '__main__':
    Server().main()