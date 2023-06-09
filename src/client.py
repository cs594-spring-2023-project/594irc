''' client.py ~ Amelia Miner, Sarvesh Biradar
# '   Implements the client side of the chatroom as specified in RFC.pdf under /docs.
# '   ...
# '''
#
import socket
import sys
import threading
from time import sleep

from conf import *


#
# '''
# client should
#     take input from user,
#
#     encode it as bytes using str.encode('ascii') or int.to_bytes('big'),
#     construct a packet using a class from conf.py,
#     and send it to the server
# in addition to keepalives
# '''
#
# # it should take name as soon as it starts
# # check name - part of irchello
# #
#

class Client:

    def __init__(self):
        print('Starting Client')
        self.terminate_flag = False
        self.current_room = 'eee'

    def receive_from_server(self, sock):
        while True:
            try:
                header_bytes = sock.recv(IrcHeader.header_length)
                header_obj = IrcHeader().from_bytes(header_bytes)
                if not header_obj.opcode == 1:
                    print(header_obj.opcode)
                payload_bytes = sock.recv(header_obj.length)
                packet_bytes = header_bytes + payload_bytes
                # depending on opcode do stuff.
                # 0 - error
                if header_obj.opcode == IRC_ERR:
                    print('got error from server')
                    msg_obj = IrcPacketErr().from_bytes(packet_bytes)
                    print(msg_obj.payload)
                    close_on_err(sock, msg_obj.payload)
                # 1 - keepalive
                elif header_obj.opcode == IRC_KEEPALIVE:
                    # do nothing
                    pass
                # 8 - list of all rooms
                elif header_obj.opcode == IRC_LISTROOMS_RESP:
                    msg_obj = IrcPacketListRoomsResp().from_bytes(packet_bytes)
                    print(msg_obj.payload)
                # 9 - list of all clients
                elif header_obj.opcode == IRC_LISTUSERS_RESP:
                    msg_obj = IrcPacketListUsersResp().from_bytes(packet_bytes)
                    print(msg_obj.payload)
                # 10 - message
                elif header_obj.opcode == IRC_TELLMSG:
                    msg_obj = IrcPacketTellMsg().from_bytes(packet_bytes)
                    print(msg_obj.payload)
            except Exception as e:
                print('receive_from_server error')
                print(e)
                sock.close()
                sys.exit(-1)

    def send_keepalives(self, client_sock):
        while True:
            sleep(4)
            if self.terminate_flag:
                print('\nServer terminated; Exiting keepalive thread')  # DEBUG
                return
            try:
                client_sock.sendall(IrcPacketKeepalive().to_bytes())
            except socket.error as e:
                print(f'KEEPALIVE THREAD: connection to fd {client_sock} errored: {e}')  # ERR
                print('Closing the socket')
                client_sock.close()
                exit(-1)

    def list_all_Rooms(self, client_socket):
        packet = IrcPacketListRooms()
        client_socket.sendall(packet.to_bytes())

    def list_all_clients(self, client_socket):
        packet = IrcPacketListUsers()
        client_socket.sendall(packet.to_bytes())

    def main(self):
        server_address = ('', IRC_SERVER_PORT)
        self.client_name = input('Input your name > ')
        join_packet = IrcPacketHello(self.client_name)
        # todo add name validation
        join_bytes = join_packet.to_bytes()
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(server_address)
            client_socket.sendall(join_bytes)
            print(MAINMENU)

        except ConnectionRefusedError as e:
            print("Connection reused by server. Either can't find server, or server is not online")
            exit(-1)

        try:
            keep_alive_thread = threading.Thread(target=self.send_keepalives, args=[client_socket])
            keep_alive_thread.start()
        except OSError as e:
            print('keep alive error')

        try:
            receiving_thread = threading.Thread(target=self.receive_from_server, args=[client_socket])
            receiving_thread.start()
        except OSError as e:
            print('receiving thread error')

        packet = IrcPacketJoinRoom('eee')
        client_socket.sendall(packet.to_bytes());
        while True:
            user_input = input('GIVE INPUT')
            user_input = user_input.strip()
            try:
                # TODO differenciate between input commands and messages and do stuff accordingly
                if ':0' in user_input:
                    # list all rooms and clients
                    self.list_all_Rooms(client_socket)
                    self.list_all_clients(client_socket)
                elif ':1' in user_input:
                    # list already joined rooms?
                    self.list_all_clients(client_socket)
                elif ':2' in user_input:
                    # join or create room and set it in global room as context
                    room_name = user_input[2:]
                    packet = IrcPacketJoinRoom(room_name=room_name)
                    client_socket.sendall(packet.to_bytes());
                    self.current_room = room_name
                elif ':3' in user_input:
                    # switch room and change it in global room as well
                    # todo
                    pass
                elif ':4' in user_input:
                    # leave the current room, set global room as NULL
                    packet = IrcPacketLeaveRoom(room_name=self.current_room)
                    client_socket.sendall(packet.to_bytes());
                    self.current_room = None
                elif ':5' in user_input:
                    # send direct message. format = :5 <receiver_username> <message>
                    pass
                elif ':6' in user_input:
                    # send direct message to current room
                    message = 'heellloo'
                    packet = IrcPacketSendMsg(payload=message, target_room=self.current_room)
                    client_socket.sendall(packet.to_bytes());
                elif ':7' in user_input:
                    # send tel message?
                    pass
                elif ':8' in user_input:
                    print("this is the command")
                elif ':9' in user_input:
                    print("this is the command")

                else:
                    print("this is the message")

            # while exception
            except KeyboardInterrupt as kbi:
                self.terminate_flag = True  # terminate keepalive thread
                client_socket.close()
                exit(-1)


if __name__ == '__main__':
    Client().main()

# 1. Take client name from user
# 2. validate it (part of irchellopacket)
# 3. Send join message.
# 4. Keep listening for incoming messages.
# 5. send room join message ( server will create room if does not exist )
# 6. Leave the room
# 7. List all rooms
# 8. List all clients
# 9. direct message
# 10. message into a channel
# 11. message into multiple channel at once
# 12. Join multiple rooms at once
# 13. Client can gracefully handle server crashes ( how? )
#
#
