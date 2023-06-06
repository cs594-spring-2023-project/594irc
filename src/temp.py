from conf import *
import socket

def main():
    # poke the server with a hello
    hello_packet = IrcPacketHello('Sarvesh')
    hello_bytes = hello_packet.to_bytes()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', IRC_SERVER_PORT))
    sock.sendall(hello_bytes)
    #sock.close()

    hello_packet = IrcPacketHello('Amelia')
    hello_bytes = hello_packet.to_bytes()
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock2.connect(('localhost', IRC_SERVER_PORT))
    sock2.sendall(hello_bytes)

    msg_packet = IrcPacketMsg(payload='This is a test message from Amelia', target='a room that doesn\'t exist')
    msg_bytes = msg_packet.to_bytes()
    sock2.sendall(msg_bytes)

    sock.close()
    sock2.close()

if __name__ == '__main__':
    main()