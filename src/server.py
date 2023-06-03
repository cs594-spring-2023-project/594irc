''' server.py ~ Amelia Miner, Sarvesh Biradar
'   Implements the server side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

from conf import *
import socket
import selectors

'''
server should
    receive packet from client,
    decode it as bytes using str.decode('ascii') or int.from_bytes('big'),
    perform some actions based on the opcode,
    and respond to the client
in addition to keepalives
'''

def accept_new_user(sock, users, selector):
    ''' accepts a new user and adds them to the users list '''
    try:
        client_sock, client_tcpip_tuple = sock.accept()
        client_sock.settimeout(TIMEOUT)
        received_hello_bytes = client_sock.recv(IrcPacketHello.packet_length)
        username = IrcPacketHello().from_bytes(received_hello_bytes).payload
        if username in users:
            close_on_err(client_sock, IRC_ERR_NAME_EXISTS)
        users.append(username)
        selector.register(client_sock, selectors.EVENT_READ)
        print(f"received hello from {username} at {client_tcpip_tuple}")
    except IRCException as e:
        close_on_err(client_sock, e.err_code)

def add_user_to_room(sock, users, rooms, selector):
    pass # TODO

def remove_user_from_room(sock, users, rooms, selector):
    pass # TODO

def send_list(sock, users, rooms, selector):
    pass # TODO

def send_msg(sock, users, rooms, selector):
    pass # TODO

def react_to_client_err(sock, users, rooms, selector):
    pass # TODO

def main():
    ''' creates a socket to listen on, initializes rooms and users lists, and enters a loop '''
    rooms = []
    users = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as main_sock:
        sel = selectors.DefaultSelector()
        sel.register(main_sock, selectors.EVENT_READ)
        main_sock.settimeout(TIMEOUT)
        main_sock.bind(('', IRC_SERVER_PORT))
        print("listening")
        main_sock.listen()
        print("looping")
        while True:
            events = sel.select(timeout=TIMEOUT)
            for key, _ in events:
                if key.fileobj == main_sock: # new client (this should be a hello pkt)
                    accept_new_user(main_sock, users, sel)
                else: # established client
                    # (this should be a keepalive, msg, err, join, leave, or list pkt)
                    client_sock = key.fileobj
                    header_bytes = client_sock.recv(IrcHeader.header_length)
                    header_obj = IrcHeader().from_bytes(header_bytes)
                    # Determine what kind of packet this is and how much more to recv
                    # recv the rest of the packet and process it
                    # TODO

if __name__ == '__main__':
    main()