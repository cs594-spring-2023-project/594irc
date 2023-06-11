''' client.py ~ Amelia Miner, Sarvesh Biradar
# '   Implements the client side of the chatroom as specified in RFC.pdf under /docs.
# '   ...
# '''
import socket
import sys
import threading
from time import sleep
import multiprocessing

from conf import *

CLIENT_MANUAL = """ 
CLIENT MANUAL
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
Command.    Functionality                                    
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
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
exit        To close the connection                                                        
"""


class Client:

    def __init__(self):
        print('Starting Client')
        self.client_name = None
        self.terminate_flag = False
        self.current_room = None
        self.silent_room_member_request = False
        self.silent_server_room_request = False
        # self.current_room_members = []
        self.room_members = dict()  # client joined room and its members
        self.client_socket = None
        self.clients_room_list = []
        self.server_room_list = []
        self.receiving_thread = None
        self.keep_alive_thread = None

    def receive_from_server(self):
        sock = self.client_socket
        while True:
            if self.event.is_set():
                print('Exiting receive_from_server thread')
                break
            else:
                try:
                    header_bytes = sock.recv(IrcHeader.header_length)
                    header_obj = IrcHeader().from_bytes(header_bytes)
                    payload_bytes = sock.recv(header_obj.length)
                    packet_bytes = header_bytes + payload_bytes

                    if not header_obj.opcode == 1:
                        # print(f'DEBUG {header_obj.opcode}')
                        pass

                    # depending on opcode do stuff.
                    # 0 - error
                    if header_obj.opcode == IRC_ERR:
                        print('got error from server')
                        msg_obj = IrcPacketErr().from_bytes(packet_bytes)
                        print(msg_obj.payload)
                        self.disconnect_and_close()

                    # 1 - keepalive
                    elif header_obj.opcode == IRC_KEEPALIVE:
                        # do nothing
                        pass

                    # 8 - list of all rooms
                    elif header_obj.opcode == IRC_LISTROOMS_RESP:
                        msg_obj = IrcPacketListRoomsResp().from_bytes(packet_bytes)
                        self.server_room_list = msg_obj.payload
                        if self.silent_server_room_request is False:
                            if len(self.server_room_list) != 0:
                                print('List of all rooms on server:')
                                for index, element in enumerate(self.server_room_list):
                                    print(f"{element}")
                            else:
                                print('No rooms created on server.')
                        else:
                            self.silent_server_room_request = False


                    # 9 - list of all clients
                    elif header_obj.opcode == IRC_LISTUSERS_RESP:
                        msg_obj = IrcPacketListUsersResp().from_bytes(packet_bytes)
                        # print(f'DEBUG IRC_LISTUSERS_RESP {msg_obj.payload}')
                        # print(f'DEBUG msg_obj.identifier {msg_obj.identifier}')
                        # print(f'DEBUG silent_room_member_request {self.silent_room_member_request}')
                        # print(f'DEBUG silent_room_member_request { self.room_members}')

                        if self.silent_room_member_request == True:
                            # client requested the list of current
                            self.room_members.update({msg_obj.identifier: msg_obj.payload})
                            self.silent_room_member_request = False
                            if self.client_name in msg_obj.payload:
                                print(f"Joined room '{msg_obj.identifier}'.")
                        else:
                            # someone joined the server
                            try:
                                old_room_members = self.room_members.get(msg_obj.identifier) if self.room_members.get(msg_obj.identifier) else set([])
                                new_user = list(set(msg_obj.payload) - old_room_members)
                                print('new_user')
                                print(new_user)
                                if len(new_user) <= 0:
                                    print('DEBUG outlier')
                                    print(msg_obj.payload)  # just catching outliers
                                else:
                                    self.room_members.update({msg_obj.identifier: msg_obj.payload})
                                    print(f"'{new_user[0]}' Joined '{msg_obj.identifier}'")
                            except KeyError as e:
                                print('error IRC_LISTUSERS_RESP');
                                print(e);
                                pass


                    # 10 - message
                    elif header_obj.opcode == IRC_TELLMSG:
                        msg_obj = IrcPacketTellMsg().from_bytes(packet_bytes)
                        if msg_obj.sending_user != self.client_name:
                            print(f'{msg_obj.sending_user} in room {msg_obj.target_room} : {msg_obj.payload}')
                        else:
                            print(f'You in room {msg_obj.target_room} : {msg_obj.payload}')

                except Exception as e:
                    self.event.set()
                    print('DEBUG - receive_from_server error')
                    self.disconnect_and_close()
                    sys.exit(-1)

    def send_keepalives(self):
        sock = self.client_socket
        while True:
            if self.event.is_set():
                print('Exiting send_keepalives thread')
                break
            else:
                try:
                    sock.sendall(IrcPacketKeepalive().to_bytes())
                    sleep(4)
                except socket.error as e:
                    print(f'KEEPALIVE THREAD: connection to fd {sock} errored: {e}')  # ERR
                    print('Closing the socket')
                    sock.close()
                    self.event.set()
                    exit()

    def list_all_rooms(self, is_silently):
        if is_silently:
            self.silent_server_room_request = True
        packet = IrcPacketListRooms()
        self.client_socket.sendall(packet.to_bytes())

    def list_all_clients(self):
        if self.current_room is None:
            print('Your are not in a room. Please join a room.')
        else:
            packet = IrcPacketListUsers(self.current_room)
            self.client_socket.sendall(packet.to_bytes())

    def request_all_room_clients_silently(self):
        self.silent_room_member_request = True
        packet = IrcPacketListUsers(self.current_room)
        self.client_socket.sendall(packet.to_bytes())

    def join_create_room(self, input_room=None):
        room_name = input_room
        if room_name is None:
            room_name = input('Enter room name > ')
        packet = IrcPacketJoinRoom(room_name=room_name)
        self.client_socket.sendall(packet.to_bytes())
        self.current_room = room_name
        self.request_all_room_clients_silently()
        if room_name not in self.clients_room_list:
            self.clients_room_list.append(room_name)

    def join_multiple_room(self):
        # get all room list from server, present it with numbers to user and ask to enter number of room to join
        room_list = list(set(self.server_room_list) - set(self.clients_room_list))
        for index, element in enumerate(room_list):
            print(f"[{index + 1}] {element}")
        if len(room_list) == 0:
            print('No rooms to join.')
            return
        input_str = input("Enter the indices separated by commas: ")
        indices = input_str.split(",")
        for index in indices:
            try:
                index_int = int(index.strip()) - 1
                if 0 <= index_int < len(room_list):
                    print(f"Joining {room_list[index_int]}")
                    self.join_create_room(input_room=room_list[index_int])
                else:
                    print(f"Invalid index: [{index_int}]")
            except ValueError as e:
                print(f"Invalid input : '{index}'")

    def switch_room(self):
        if len(self.server_room_list) == 0:
            print('No rooms joined to switch.')
            return
        if len(self.clients_room_list) == 0:
            print('No rooms joined to switch.')
            return
        print(self.clients_room_list)
        room_name = input('Enter room name you want to switch > ')
        if room_name not in self.clients_room_list:
            print('You have not joined this room yet. please join this room first')
        elif room_name in self.clients_room_list:
            self.current_room = room_name
            # self.request_all_room_clients_silently()

    def leave_room(self):
        if self.current_room is not None:
            print(f'Removing yourself from {self.current_room}')
            packet = IrcPacketLeaveRoom(room_name=self.current_room)
            self.client_socket.sendall(packet.to_bytes());
            self.clients_room_list.remove(self.current_room)
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
        for index, element in enumerate(self.clients_room_list):
            print(f"[{index + 1}] {element}")
        input_str = input("Enter the indices separated by commas: ")
        input_msg = input('Enter message to send')
        indices = input_str.split(",")
        try:
            for index in indices:
                index = int(index.strip()) - 1
                if 0 <= index < len(self.clients_room_list):
                    print(f"Sending message to {self.clients_room_list[index]}")
                    self.send_msg_to_room(input_room=self.clients_room_list[index], input_message=input_msg)
                else:
                    print(f"Invalid index: [{index}]")
        except ValueError as e:
            print(f"Invalid input : '{index}'")

    def create_connection(self):
        self.client_name = input('Input your name > ')
        server_address = ('', IRC_SERVER_PORT)

        try:
            join_packet = IrcPacketHello(self.client_name)
            join_bytes = join_packet.to_bytes()
        except IRCException as e:
            print('IRCException')
            self.event.set()
            print(e.err_code)
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(server_address)
            self.client_socket.sendall(join_bytes)
        except ConnectionRefusedError as e:
            # todo check for actual successful connection before printing manual
            print("Connection reused by server. Either can't find server, or server is not online")
            self.event.set()
            exit(-1)
        finally:
            if self.event.is_set():
                print('Exiting receive_from_server thread')
                exit()
            else:
                print(CLIENT_MANUAL)

    def start_receiving_thread(self):
        try:
            self.receiving_thread = threading.Thread(target=self.receive_from_server)
            self.receiving_thread.start()
        except OSError as e:
            print('receiving thread error')
            print(e)

    # keepalive
    def start_keep_alive_thread(self):
        try:
            self.keep_alive_thread = threading.Thread(target=self.send_keepalives)
            self.keep_alive_thread.start()
        except OSError as e:
            print('Keep alive error')
            print(e)

    def disconnect_and_close(self):
        self.event.set()
        print('Exiting...')
        if self.receiving_thread is not None:
            self.receiving_thread.join()
        if self.keep_alive_thread is not None:
            self.keep_alive_thread.join()
        print('Closing connection to server')
        if self.client_socket is not None:
            self.client_socket.close()


    def main_loop(self):
        while True:
            if self.event.is_set():
                self.disconnect_and_close()
                break
            else:
                try:
                    # get manually list of all server rooms for in case client presses #3
                    self.list_all_rooms(is_silently=True)
                    user_input = input('GIVE INPUT > ')
                    user_input = user_input.strip()
                    # 0 list all the available rooms ✅
                    if '#0' in user_input:
                        self.list_all_rooms(False)
                        sleep(0.3)

                    # 1 list all members of current room ✅
                    elif '#1' in user_input:
                        self.list_all_clients()
                        sleep(0.3)


                    # 2 join or create the room if it does not exist ✅
                    elif '#2' in user_input:
                        self.join_create_room()
                        sleep(0.3)


                    # 3 join multiple rooms at once ✅
                    elif '#3' in user_input:
                        self.join_multiple_room()
                        sleep(0.3)


                    # 4 switch room ✅
                    elif '#4' in user_input:
                        self.switch_room()
                        sleep(0.3)


                    # 5 leave current room ✅
                    elif '#5' in user_input:
                        self.leave_room()
                        sleep(0.3)


                    # 6 send a direct message to current room ✅
                    elif '#6' in user_input:
                        self.send_msg_to_room()
                        sleep(0.3)


                    # 7 send a direct message to multiple room
                    elif '#7' in user_input:
                        self.send_msg_to_multiple_rooms()
                        sleep(0.3)


                    # 8 send a direct message to other user
                    elif '#8' in user_input:
                        print("this is the command")
                        sleep(0.3)


                    # 9 print the manual
                    elif '#9' in user_input:
                        print(CLIENT_MANUAL)
                        sleep(0.3)


                    # 10 close the connection
                    elif 'exit' in user_input:
                        self.disconnect_and_close()
                        exit(0)


                # while exception
                except Exception as e:
                    print(e)
                    pass


    def main(self):
        try:

            self.event = threading.Event()

            self.create_connection()

            self.start_receiving_thread()

            self.start_keep_alive_thread()

            self.main_loop()

        except KeyboardInterrupt as i:
            print('Keyboard interrupt...')
            self.disconnect_and_close()
            exit(-1)


if __name__ == '__main__':
    Client().main()
