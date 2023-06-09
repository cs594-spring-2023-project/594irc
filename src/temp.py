from sys import argv
from time import sleep
from conf import *
from socket import *
sock = socket(AF_INET, SOCK_STREAM)
sock2 = socket(AF_INET, SOCK_STREAM)

VALID_MESSAGES = ['', '1', 'testmsg', 'bigger message with other characters /.,?~!@#$%^&*()_+=-;\'":',
            b'this has a line break right here0x0D0x0A^See? This is the same string! ^'.decode('ascii'),
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
]

INVALID_MESSAGES = [' spaces in', 'bad places ', ' ']

VALID_LABELS = ['xX_ChickenWing_Xx', '123bunchanumbers890', ':)']

def send_hellos():
    # poke the server hellos
    global sock, sock2
    hello_packet = IrcPacketHello('Sarvesh')
    hello_bytes = hello_packet.to_bytes()
    sock.connect(('localhost', IRC_SERVER_PORT))
    sock.sendall(hello_bytes)

    hello_packet = IrcPacketHello('Amelia')
    hello_bytes = hello_packet.to_bytes()
    sock2.connect(('localhost', IRC_SERVER_PORT))
    sock2.sendall(hello_bytes)

def both_join():
    global sock, sock2
    join_packet = IrcPacketJoinRoom('test room')
    join_bytes = join_packet.to_bytes()
    sock.sendall(join_bytes)
    sock2.sendall(join_bytes)

def send_msg():
    # poke the server with a message (this should really mock the hello and join packets)
    global sock2
    msg_packet = IrcPacketSendMsg(payload='This is a test message from Amelia', target_room='test room')
    msg_bytes = msg_packet.to_bytes()
    sock2.sendall(msg_bytes)

def send_error():
    # tests server side err handling
    global sock2
    err_packet = IrcPacketErr(IRC_ERR_ILLEGAL_LABEL)
    err_bytes = err_packet.to_bytes()
    sock2.sendall(err_bytes)

def leave_room():
    global sock
    leave_packet = IrcPacketLeaveRoom('test room')
    leave_bytes = leave_packet.to_bytes()
    sock.sendall(leave_bytes)

def quit():
    sock.close()
    sock2.close()
    exit(0)

def main(interactive):
    while interactive:
        response = input('> ')
        if response == 'hellos':
            send_hellos()
        if response == 'msg':
            send_msg()
        if response == 'exit':
            quit()
    else:
        send_hellos()
        sleep(1)
        both_join()
        sleep(1)
        send_msg()
        sleep(1)
        send_error()
        sleep(1)
        leave_room()
        sleep(1)
        #sleep(8)
    if not interactive:
        sleep(10)
    quit()

if __name__ == '__main__':
    if len(argv) > 1:
        if argv[1] == '-i':
            main(True)
    main(False)