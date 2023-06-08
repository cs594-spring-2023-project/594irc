from sys import argv
from time import sleep
from conf import *
from socket import *
sock = socket(AF_INET, SOCK_STREAM)
sock2 = socket(AF_INET, SOCK_STREAM)

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

def send_msg():
    # poke the server with a message (this should really mock the hello and join packets)
    global sock2
    msg_packet = IrcPacketSendMsg(payload='This is a test message from Amelia', other='a room that doesn\'t exist')
    msg_bytes = msg_packet.to_bytes()
    sock2.sendall(msg_bytes)

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
        send_msg()
        #sleep(8)
    quit()

if __name__ == '__main__':
    if len(argv) > 1:
        if argv[1] == '-i':
            main(True)
    main(False)