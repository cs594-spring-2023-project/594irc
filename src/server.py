''' server.py ~ Amelia Miner
'   Implements the server side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

import selectors
import socket
import threading
from time import sleep

from conf import *

# using globals to share data between threads
sel = selectors.DefaultSelector()
users = []

class User:
    ''' represents a user with a username and a socket '''
    def __init__(self, username, sock):
        self.username = username
        self.sock = sock

def accept_new_user(sock):
    ''' accepts a new user and adds them to the users list '''
    global sel, users
    try:
        client_sock = None
        client_sock, client_tcpip_tuple = sock.accept()
        client_sock.settimeout(TIMEOUT)
        received_hello_bytes = client_sock.recv(IrcPacketHello.packet_length)
        username = IrcPacketHello().from_bytes(received_hello_bytes).payload
        if username in [user.username for user in users]:
            users = close_on_err(client_sock, IRC_ERR_NAME_EXISTS, sel=sel, users=users)
            return
        users.append(User(username, client_sock))
        sel.register(client_sock, selectors.EVENT_READ)
        print(f'received hello from {username} at {client_tcpip_tuple} (fd {client_sock.fileno()})')
    except IRCException as e:
        users = close_on_err(client_sock, e.err_code, sel=sel, users=users)
        return
    except ValueError as e:
        print('client connection at addr/port already exists')
        users = close_on_err(client_sock, IRC_ERR, sel=sel, users=users)

def add_user_to_room(sock, join_msg, users, rooms, sel):
    try:
        # create room if it doesn't exist
        if join_msg.other not in rooms.keys():
            rooms[join_msg.other] = []
        # add user to room
        rooms[join_msg.other].append(sock)
        # send list of users to all users in room
        list_users_packet = IrcPacketList(users=rooms[join_msg.other])
        for room in rooms.keys():
            for user in rooms[room]:
                #user.sendall(join_msg.to_bytes())
                pass # TODO write and use a listusers packet
    except IRCException as e:
        users = close_on_err(sock, e.err_code, sel=sel, users=users)
        return

def remove_user_from_room(sock, users, rooms, sel):
    pass # TODO

def send_list(sock, users, rooms, sel):
    pass # TODO

def send_msg(sock, msg, rooms):
    global sel, users
    print(f'received "{msg}" from {sock.getpeername()}') # TODO
    if msg.other in rooms.keys():
        for user in rooms[msg.other]:
            #user.sendall(msg.to_bytes())
            pass # TODO write and use a tellmsg packet

def react_to_client_err(sock, users, rooms, sel):
    pass # TODO

def send_keepalive(sock):
    global sel, users
    ''' sends a keepalive packet to the given socket '''
    try:
        sock.sendall(IrcPacketKeepalive().to_bytes())
    except socket.timeout:
        print(f'connection to {sock.getpeername()} timed out')
        sock.close()
    except socket.error as e:
        print(f'KEEPALIVE THREAD: connection to fd {sock} errored: {e}')
        sel.unregister(sock)
        users = clean_userlist(users, sock)
        sock.close()

def send_keepalives(main_sock):
    ''' Should be its own thread '''
    global sel, users
    while True:
        sleep(4)
        clients = [val.fileobj for val in sel.get_map().values() if val.fileobj != main_sock]
        users = clean_userlist(users)
        for client in clients:
            send_keepalive(client)

def main():
    ''' creates a socket to listen on, initializes rooms and users lists, and enters a loop '''
    global sel
    global users
    rooms = {}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as main_sock:
        sel.register(main_sock, selectors.EVENT_READ)
        main_sock.settimeout(TIMEOUT)
        main_sock.bind(('', IRC_SERVER_PORT))
        print("listening")
        main_sock.listen()
        print("looping")
        mainloop(main_sock, users, rooms, sel)

def mainloop(main_sock, users, rooms, sel):
    keepalive_thread = threading.Thread(target=send_keepalives, args=[main_sock])
    keepalive_thread.start() # TODO handle OS errors gracefully
    while True:
        events = sel.select(timeout=TIMEOUT)
        for key, _ in events:
            if key.fileobj == main_sock: # new client (this should be a hello pkt)
                accept_new_user(main_sock)
            else: # established client
                # (this should be a keepalive, msg, err, join, leave, or list pkt)
                client_sock = key.fileobj
                receive_from_client(client_sock, users, rooms, sel)

def receive_from_client(client_sock, users, rooms, sel):
    ''' receives a packet from the given socket and reacts to it '''
    try:
        header_bytes = client_sock.recv(IrcHeader.header_length)
    except OSError as e: # tried to read from a dead connection
        if client_sock.fileno() != -1:
            sel.unregister(client_sock)
        users = clean_userlist(users, client_sock)
        client_sock.close()
        return 
    if header_bytes == b'':
        #print(f'received nothing from {client_sock.getpeername()}')
        return # not sure why this happens...
        # if there's no inbound traffic why does the FD get selected?
    header_obj = IrcHeader().from_bytes(header_bytes)
    if header_obj.opcode == IRC_KEEPALIVE:
        print(f'received keepalive from {client_sock.getpeername()}') # TODO
    elif header_obj.opcode == IRC_SENDMSG:
        packet_bytes = header_bytes + client_sock.recv(header_obj.length)
        msg_obj = IrcPacketSendMsg().from_bytes(packet_bytes)
        send_msg(client_sock, msg_obj, rooms)
    elif header_obj.opcode == IRC_ERR:
        print(f'received err from {client_sock.getpeername()}') # TODO
    elif header_obj.opcode == IRC_JOINROOM:
        print(f'received join from {client_sock.getpeername()}') # TODO
        add_user_to_room(client_sock, rooms)
    elif header_obj.opcode == IRC_LEAVEROOM:
        print(f'received leave from {client_sock.getpeername()}') # TODO
    elif header_obj.opcode == IRC_LISTROOMS:
        print(f'received listrooms from {client_sock.getpeername()}') # TODO
    elif header_obj.opcode == IRC_LISTUSERS:
        print(f'received listusers from {client_sock.getpeername()}') # TODO
    else:
        print(f'WARNING! OPCODE NOT KNOWN TO SERVER\nreceived opcode {header_obj.opcode} from {client_sock.getpeername()};\nnot yet implemented!')
    #client_sock.recv(4096) # drain buffer

if __name__ == '__main__':
    main()