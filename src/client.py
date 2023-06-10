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

CLIENT_MANUAL = """ 

******************************  MANUAL  ********************************************
Command.    Functionality                                    
************************************************************************************
#0          To list all the available rooms                   
#1          To list all members of current room (client should be part of the room)                       
#2          To join or create the room if does not exist 
#3          To join multiple rooms at once           
#4          To switch room                                   
#5          To leave current room                             
#5          To send a direct message to current room          
#6          To send a direct message to multiple room  
#7          To send a direct message to other user         
#8          To print menu again   
#9          To close the connection                                                        

"""


class Client:

    def __init__(self):
        print('Starting Client')
        self.terminate_flag = False
        self.current_room = 'eee'
        self.client_socket = None

    def receive_from_server(self):
        sock = self.client_socket
        while True:
            try:
                header_bytes = sock.recv(IrcHeader.header_length)
                header_obj = IrcHeader().from_bytes(header_bytes)
                payload_bytes = sock.recv(header_obj.length)
                packet_bytes = header_bytes + payload_bytes

                if not header_obj.opcode == 1:
                    print(header_obj.opcode)

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

    def send_keepalives(self):
        sock = self.client_socket
        while True:
            sleep(4)
            if self.terminate_flag:
                print('\nServer terminated; Exiting keepalive thread')  # DEBUG
                return
            try:
                sock.sendall(IrcPacketKeepalive().to_bytes())
            except socket.error as e:
                print(f'KEEPALIVE THREAD: connection to fd {sock} errored: {e}')  # ERR
                print('Closing the socket')
                sock.close()
                exit(-1)

    def list_all_Rooms(self):
        packet = IrcPacketListRooms()
        self.client_socket.sendall(packet.to_bytes())

    def list_all_clients(self):
        packet = IrcPacketListUsers()
        self.client_socket.sendall(packet.to_bytes())

    def create_connection(self):
        server_address = ('', IRC_SERVER_PORT)
        join_packet = IrcPacketHello(self.client_name)
        join_bytes = join_packet.to_bytes()
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(server_address)
            self.client_socket.sendall(join_bytes)
        except ConnectionRefusedError as e:
            print("Connection reused by server. Either can't find server, or server is not online")
            exit(-1)
        finally:
            print(CLIENT_MANUAL)

    def main(self):

        self.client_name = input('Input your name > ')

        self.create_connection()

        # keepalive
        try:
            keep_alive_thread = threading.Thread(target=self.send_keepalives)
            keep_alive_thread.start()
        except OSError as e:
            print('keep alive error')

        # receive thread
        try:
            receiving_thread = threading.Thread(target=self.receive_from_server)
            receiving_thread.start()
        except OSError as e:
            print('receiving thread error')

        while True:
            user_input = input('GIVE INPUT> ')
            user_input = user_input.strip()
            try:
                # 0 list all the available rooms
                if '#0' in user_input:
                    self.list_all_Rooms()

                # 1 list all members of current room
                # check if the current room is not none
                elif '#1' in user_input:
                    self.list_all_clients()

                # 2 join or create the room if it does not exist
                elif '#2' in user_input:
                    room_name = input('enter room name')
                    print(room_name)
                    packet = IrcPacketJoinRoom(room_name=room_name)
                    self.client_socket.sendall(packet.to_bytes());
                    self.current_room = room_name

                # 3 join multiple rooms at once
                # todo give client list of room with number and ask to enter the nnumbers
                elif '#3' in user_input:
                    pass

                # 4 switch room
                # todo update current room
                elif '#4' in user_input:
                    packet = IrcPacketLeaveRoom(room_name=self.current_room)
                    self.client_socket.sendall(packet.to_bytes());
                    self.current_room = None

                # 5 leave current room
                # todo make current room None
                elif '#5' in user_input:
                    pass

                # 6 send a direct message to current room
                # todo ask for input and send message
                elif '#6' in user_input:
                    message = 'heellloo'
                    packet = IrcPacketSendMsg(payload=message, target_room=self.current_room)
                    self.client_socket.sendall(packet.to_bytes());

                # 7 send a direct message to multiple room
                # todo give list of rooms, ask to enter number with comma separated, and ask for messsage.
                elif '#7' in user_input:
                    pass

                # 7 send a direct message to other user
                # todo ask username and then message. both on separate line
                elif '#8' in user_input:
                    print("this is the command")

                # 8 print the manual
                elif '#9' in user_input:
                    print(CLIENT_MANUAL)

                # 9 close the connection
                else:
                    pass

            # while exception
            except KeyboardInterrupt as kbi:
                self.terminate_flag = True  # terminate keepalive thread
                self.client_socket.close()
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
