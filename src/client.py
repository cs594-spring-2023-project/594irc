''' client.py ~ Amelia Miner, Sarvesh Biradar
# '   Implements the client side of the chatroom as specified in RFC.pdf under /docs.
# '   ...
# '''
#
import socket
import sys
import threading
from time import sleep
import multiprocessing

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
#6          To send a direct message to current room          
#7          To send a direct message to multiple room  
#8          To send a direct message to other user         
#9          To print menu again   
#10         To close the connection                                                        
"""


class Client:

    def __init__(self):
        print('Starting Client')
        self.client_name = None
        self.terminate_flag = False
        self.current_room = None
        self.client_socket = None
        self.room_list = []
        self.all_server_rooms = []

    def receive_from_server(self):
        sock = self.client_socket
        while True:
            try:
                header_bytes = sock.recv(IrcHeader.header_length)
                header_obj = IrcHeader().from_bytes(header_bytes)
                payload_bytes = sock.recv(header_obj.length)
                packet_bytes = header_bytes + payload_bytes

                if not header_obj.opcode == 1:
                    print(f'DEBUG {header_obj.opcode}')

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
                    self.all_server_rooms = msg_obj.payload
                    if len(self.all_server_rooms) != 0:
                        print('List of all rooms on server:')
                        for index, element in enumerate(self.all_server_rooms):
                            print(f"{element}")
                    else:
                        print('No rooms created on server.')


                # 9 - list of all clients
                elif header_obj.opcode == IRC_LISTUSERS_RESP:
                    msg_obj = IrcPacketListUsersResp().from_bytes(packet_bytes)
                    print(msg_obj.payload)
                    if len(msg_obj.payload) != 0:
                        print(f'List of users in {self.current_room}:')
                        for index, element in enumerate(msg_obj.payload):
                            print(f"{element}")



                # 10 - message
                elif header_obj.opcode == IRC_TELLMSG:
                    msg_obj = IrcPacketTellMsg().from_bytes(packet_bytes)
                    if msg_obj.sending_user != self.client_name:
                        print(f'{msg_obj.sending_user} in room {msg_obj.target_room} : {msg_obj.payload}')
                    else:
                        print(f'You in room {msg_obj.target_room} : {msg_obj.payload}')

            except Exception as e:
                print('DEBUG - receive_from_server error')
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
                exit()

    def list_all_rooms(self):
        packet = IrcPacketListRooms()
        self.client_socket.sendall(packet.to_bytes())

    def list_all_clients(self):
        if self.current_room is None:
            print('Your are not in a room. Please join a room.')
        else:
            packet = IrcPacketListUsers(self.current_room)
            self.client_socket.sendall(packet.to_bytes())

    def join_create_room(self, input_room=None):
        room_name = input_room
        if room_name is None:
            room_name = input('Enter room name > ')
        print(room_name)
        packet = IrcPacketJoinRoom(room_name=room_name)
        self.client_socket.sendall(packet.to_bytes())
        self.current_room = room_name
        if room_name not in self.room_list:
            self.room_list.append(room_name)

    def join_multiple_room(self):
        # get all room list from server, present it with numbers to user and ask to enter number of room to join
        for index, element in enumerate(self.all_server_rooms):
            print(f"[{index+1}] {element}")
        input_str = input("Enter the indices separated by commas: ")
        indices = input_str.split(",")
        for index in indices:
            index = int(index.strip())-1
            if 0 <= index < len(self.all_server_rooms):
                print(f"Joining {self.all_server_rooms[index]}")
                self.join_create_room(input_room=self.all_server_rooms[index])
            else:
                print(f"Invalid index: [{index}]")

    def switch_room(self):
        print(self.room_list)
        room_name = input('Enter room name you want to switch > ')
        if room_name not in self.room_list:
            print('You have not joined this room yet. please join this room first')
        elif room_name in self.room_list:
            self.current_room = room_name

    def leave_room(self):
        if self.current_room is not None:
            print(f'Removing yourself from {self.current_room}')
            packet = IrcPacketLeaveRoom(room_name=self.current_room)
            self.client_socket.sendall(packet.to_bytes());
            self.room_list.remove(self.current_room)
            self.current_room = None
        else:
            print('You are not in any room. Switch to or join room first')

    def send_msg_to_room(self, input_room=None, input_message=None):
        room = input_room
        message = input_message
        if room is None:
            room = self.current_room
        if message is None:
            print(f'Enter message you want to send to {room}')
            message = input()
        packet = IrcPacketSendMsg(payload=message, target_room=room)
        self.client_socket.sendall(packet.to_bytes());

    def send_msg_to_multiple_rooms(self):
        for index, element in enumerate(self.room_list):
            print(f"[{index+1}] {element}")
        input_str = input("Enter the indices separated by commas: ")
        input_msg = input('Enter message to send')
        indices = input_str.split(",")
        for index in indices:
            index = int(index.strip())-1
            if 0 <= index < len(self.room_list):
                print(f"Sending message to {self.room_list[index]}")
                self.send_msg_to_room(input_room=self.room_list[index], input_message=input_msg)
            else:
                print(f"Invalid index: [{index}]")
        pass

    def create_connection(self):
        self.client_name = input('Input your name > ')
        server_address = ('', IRC_SERVER_PORT)

        try:
            join_packet = IrcPacketHello(self.client_name)
            join_bytes = join_packet.to_bytes()
        except IRCException as e:
            print('IRCException')
            print(e.err_code)

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(server_address)
            self.client_socket.sendall(join_bytes)
        except ConnectionRefusedError as e:
            # todo check for actual successful connection before printing manual
            print("Connection reused by server. Either can't find server, or server is not online")
            exit(-1)
        finally:
            sleep(1)
            print(CLIENT_MANUAL)

    def start_receiving_thread(self):
        try:
            receiving_thread = threading.Thread(target=self.receive_from_server)
            receiving_thread.start()
        except OSError as e:
            print('receiving thread error')

    # keepalive
    def start_keep_alive_thread(self):
        try:
            keep_alive_thread = threading.Thread(target=self.send_keepalives)
            keep_alive_thread.start()
        except OSError as e:
            print('keep alive error')

    def main_loop(self):
        while True:
            user_input = input('GIVE INPUT> ')
            user_input = user_input.strip()
            try:
                # 0 list all the available rooms ✅
                if '#0' in user_input:
                    self.list_all_rooms()

                # 1 list all members of current room ✅
                # check if the current room is not none
                elif '#1' in user_input:
                    self.list_all_clients()

                # 2 join or create the room if it does not exist ✅
                elif '#2' in user_input:
                    self.join_create_room()

                # 3 join multiple rooms at once ✅
                elif '#3' in user_input:
                    self.join_multiple_room()

                # 4 switch room ✅
                elif '#4' in user_input:
                    self.switch_room()


                # 5 leave current room ✅
                elif '#5' in user_input:
                    self.leave_room()


                # 6 send a direct message to current room ✅
                elif '#6' in user_input:
                    self.send_msg_to_room()


                # 7 send a direct message to multiple room
                elif '#7' in user_input:
                    self.send_msg_to_multiple_rooms()

                # 8 send a direct message to other user
                # todo ask username and then message. both on separate line
                elif '#8' in user_input:
                    print("this is the command")

                # 9 print the manual
                elif '#9' in user_input:
                    print(CLIENT_MANUAL)

                # 10 close the connection
                else:
                    pass

            # while exception
            except KeyboardInterrupt as kbi:
                self.terminate_flag = True  # terminate keepalive thread
                self.client_socket.close()
                exit(-1)

    def main(self):

        self.create_connection()

        self.start_receiving_thread()

        self.start_keep_alive_thread()

        self.main_loop()


if __name__ == '__main__':
    Client().main()
