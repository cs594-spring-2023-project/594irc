''' server.py ~ Amelia Miner, Sarvesh Biradar
'   Implements the server side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

from conf import *
import socket

'''
server should
    receive packet from client,
    decode it as bytes using str.decode('ascii') or int.from_bytes('big'),
    perform some actions based on the opcode,
    and respond to the client
in addition to keepalives
'''

def receive_hello(client_sock):
    ''' receives a hello packet from the client, parses and validates it,
    '   returns the username
    '   should we encode the field lengths in the packet classes...?
    '''
    received_hello = client_sock.recv(IrcHeader.header_length + IrcPacketHello.packet_length)
    # parse from bytes
    if received_hello[0] != IRC_HELLO:
        close_on_err(client_sock, IRC_ERR_ILLEGAL_OPCODE)
    if int.from_bytes(received_hello[1:IrcHeader.length_length+1], 'big') != IrcPacketHello.packet_length:
        close_on_err(client_sock, IRC_ERR_ILLEGAL_LENGTH)
    username = received_hello[5:37].decode('ascii')
    # validate new username - better here or in consuming code?
    if not validate_label(username):
        close_on_err(client_sock, IRC_ERR_ILLEGAL_LABEL)
    version = int.from_bytes(received_hello[37:39], 'big')
    if version != IRC_VERSION:
        close_on_err(client_sock, IRC_ERR_WRONG_VERSION)
    return username

def main():
    ''' creates a socket to listen on, initializes rooms and users lists, and enters a loop '''
    rooms = []
    users = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(TIMEOUT)
        sock.bind(('', IRC_SERVER_PORT))
        print("listening")
        sock.listen()
        print("looping")
        while True:
            client_sock, client_addr = sock.accept()
            client_sock.settimeout(TIMEOUT)
            username = receive_hello(client_sock)
            if username in users:
                close_on_err(client_sock, IRC_ERR_NAME_EXISTS)
            users.append(username)
            print(f"received hello from {username}")


if __name__ == '__main__':
    main()