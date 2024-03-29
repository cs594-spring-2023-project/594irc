''' server.py ~ Amelia Miner
'   Implements the server side of the chatroom as specified in RFC.pdf
'   under /docs.
'''

import selectors
import socket
import threading
from time import sleep

from conf import *


class User:
    ''' represents a user with a username and a socket '''

    def __init__(self, username, sock):
        self.username = username
        self.sock = sock

# should really have written a room class but too far along now
# just access room lists via self.rooms[room_name]

class Server:
    ''' represents the server with users, rooms, a selector,
    '   and a flag that tells child processes to terminate
    '''

    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.users = []
        self.rooms = {}
        self.terminate_flag = False

    def close_and_clean(self, sock=None, err_code=IRC_ERR_UNKNOWN):
        ''' closes a socket and cleans up the userlist and selector 
        '   if sock is None, closes all sockets and cleans up all users
        '''
        if sock is None:  # disconnect all users
            for user in self.users:
                self.close_and_clean(user.sock, err_code)
            return
        close_on_err(sock, err_code)
        try:
            self.sel.unregister(sock)
        except (KeyError, ValueError, OSError):
            pass  # socket already unregistered
        self.clean_userlist(sock)

    def accept_new_user(self, sock):
        ''' accepts a new user and adds them to the users list '''
        try:
            client_sock = None
            username = ''
            client_sock, client_tcpip_tuple = sock.accept()
            client_sock.settimeout(TIMEOUT)
            new_user = User(username, client_sock)
            rcvd_hello_bytes = client_sock.recv(IrcPacketHello.packet_length)
            username = IrcPacketHello().from_bytes(rcvd_hello_bytes).payload
            new_user.username = username
            if username in [user.username for user in self.users]:
                self.close_and_clean(client_sock, IRC_ERR_NAME_EXISTS)
                return
            self.users.append(new_user)
            self.sel.register(client_sock, selectors.EVENT_READ)
            print(f'added {username} at {client_tcpip_tuple} ',
                  f'(fd {client_sock.fileno()}) to server')  # DEBUG
        except IRCException as e:
            self.close_and_clean(client_sock, e.err_code)
        except ValueError as e:
            print('client connection at addr/port already exists')  # ERR
            self.close_and_clean(client_sock, IRC_ERR_UNKNOWN)

    def add_user_to_room(self, user, join_msg):
        ''' adds a user to a room and sends the user list to all users in the
        '   room
        '''
        # create room if it doesn't exist
        room_name = join_msg.payload
        if room_name not in self.rooms.keys():
            self.rooms[room_name] = []
        this_room = self.rooms[room_name]
        # add user to room
        this_room.append(user)
        # send list of users to all users in room
        for other_user in self.rooms[room_name]:
            try:
                self.send_user_list(other_user, room_name)
            except IRCException as e:
                self.close_and_clean(user.sock, e.err_code)

    def user_requests_user_list(self, user, list_users_msg):
        ''' receives a request for a list of users in a room 
        '   and sends it to the user
        '''
        room_name = list_users_msg.payload
        bad_room_name = False
        if room_name not in self.rooms.keys():
            bad_room_name = True  # will return empty list
        try:
            self.send_user_list(user, room_name, bad_room_name)
        except IRCException as e:
            self.close_and_clean(user.sock, e.err_code)

    def send_user_list(self, user, room_name, bad_room_name=False):
        ''' sends a list of users in a room to a user '''
        if bad_room_name:
            payload = []
        else:
            this_room = self.rooms[room_name]
            payload = [u.username for u in this_room]
        try:
            list_users_packet = IrcPacketListUsersResp(
                payload=payload,
                identifier=room_name
            )
            list_users_packet_bytes = list_users_packet.to_bytes()
            user.sock.sendall(list_users_packet_bytes)
        except IRCException as e:
            print(f'ERROR: encountered protocol error while '
                      + f'sending user list to {user.username}', e)
            self.close_and_clean(user.sock, e.err_code)
        except socket.timeout:
            print(f'connection to {user.sock} timed out while '
                      + f'sending user list')  # ERR
        except OSError:
            print(f'connection to {user.sock} errored while '
                      + f'sending user list')  # ERR

    def send_room_list(self, user):
        try:
            room_list = [room for room in self.rooms.keys()]
            room_list_packet = IrcPacketListRoomsResp(payload=room_list)
            room_list_packet_bytes = room_list_packet.to_bytes()
            print(f'sending room list {room_list} to {user.username}')  # DEBUG
            user.sock.sendall(room_list_packet_bytes)
        except IRCException as e:
            self.close_and_clean(user.sock, e.err_code)

    def send_msg(self, user, msg):
        print(f'relaying "{msg.payload}" from {user.username} '
                      + f'to {msg.target_label}')  # DEBUG
        if msg.target_label in self.rooms.keys():
            try:
                tell_msg = IrcPacketTellMsg(
                    payload=msg.payload,
                    target_label=msg.target_label,
                    sending_user=user.username
                )
                tell_msg_bytes = tell_msg.to_bytes()
            except IRCException as e:
                print(f'ERROR: encountered protocol error while sending '
                      + f'msg to {user.username}')
                self.close_and_clean(user.sock, e.err_code)
            for user in self.rooms[msg.target_label]:
                try:
                    user.sock.sendall(tell_msg_bytes)
                    print(f'told "{msg.payload}" to {user.username} in '
                      + f'{msg.target_label}')  # DEBUG
                except socket.timeout:
                    print(f'connection to {user.sock.getpeername()} timed out '
                      + f'while telling msg')  # ERR
                    self.close_and_clean(user.sock, IRC_ERR)
                except OSError:
                    print(f'connection to {user.sock.getpeername()} errored '
                      + f'while telling msg')  # ERR
                    self.close_and_clean(user.sock, IRC_ERR)
        else:  # behavior not defined in RFC!
            print(f'no room named "{msg.target_label}" exists... '
                      + f'silently ignoring send for now')  # DEBUG

    def send_priv_msg(self, user, msg):
        print(f'relaying "{msg.payload}" from {user.username} to {msg.target_label}')  # DEBUG
        if msg.target_label in [u.username for u in self.users]:
            try:
                target_user = [u for u in self.users if u.username == msg.target_label][0]
                tell_msg = IrcPacketTellPrivMsg(
                    payload=msg.payload,
                    target_label=msg.target_label,
                    sending_user=user.username
                )
                tell_msg_bytes = tell_msg.to_bytes()
            except IRCException as e:
                print(f'ERROR: encountered protocol error while '
                      + f'telling msg to {msg.target_label}')
                self.close_and_clean(user.sock, e.err_code)
            try:
                target_user.sock.sendall(tell_msg_bytes)
                print(f'told "{msg.payload}" to {msg.target_label}')  # DEBUG
            except socket.timeout:
                print(f'connection to {user.sock.getpeername()} '
                      + f'timed out while telling msg')  # ERR
                self.close_and_clean(user.sock, IRC_ERR)
            except OSError:
                print(f'connection to {user.sock.getpeername()} '
                      + f'errored while telling msg')  # ERR
                self.close_and_clean(user.sock, IRC_ERR)
        else:  # behavior not defined in RFC!
            print(f'No user named "{msg.target_label}" exists... '
                      + f'silently ignoring send for now')  # DEBUG

    def react_to_client_err(self, user, err_msg):
        print(f'closed on by {user.sock.getpeername()} '
                      + f'due to error {err_msg.payload}')  # ERR
        print(f'removing {user.username} from server')  # ERR
        self.close_and_clean(user.sock, err_msg.payload)

    def clean_userlist(self, bad_sock=None):
        ''' Removes user from server's user list and all rooms '''
        # find bad user using socket
        bad_user = None
        for user in self.users:
            if user.sock == bad_sock:
                bad_user = user
                break
        if bad_user in self.users:
            self.users.remove(bad_user)
        # self.users = [user for user in self.users \
        # if user.sock != bad_sock and user.sock.fileno() != -1]
        if bad_user is not None:
            self.remove_user_from_room(bad_user)

    def remove_user_from_room(self, user, room_to_leave=None):
        ''' if room_to_leave is None, removes user from all rooms
        '   also removes dead connections
        '''
        bad_sock = user.sock
        for room in self.rooms:
            if room is not None and room != room_to_leave:
                continue
            print(f'removing {user.username} from {room}')  # DEBUG
            self.rooms[room] = [u for u in self.rooms[room] if \
                                u.sock != bad_sock and u.sock.fileno() != -1]

    def send_keepalive(self, sock):
        ''' sends a keepalive packet to the given socket '''
        try:
            sock.sendall(IrcPacketKeepalive().to_bytes())
        except IRCException as e:
            print(f'KEEPALIVE THREAD: encountered protocol error '
                  + f'while sending keepalive to {sock}')
            self.close_and_clean(sock, e.err_code)
        except socket.timeout:
            print(f'connection to {sock.getpeername()} timed out')  # ERR
            sock.close()
        except (socket.error, BrokenPipeError, OSError) as e:
            print(f'KEEPALIVE THREAD: connection to fd {sock} errored: {e}')  # ERR
            self.close_and_clean(sock, IRC_ERR_UNKNOWN)  # timeout err?
            sock.close()

    def send_keepalives(self, main_sock):
        ''' Should be its own thread '''
        while True:
            sleep(4)
            if self.terminate_flag:
                print('\nServer terminated; Exiting keepalive thread')  # DEBUG
                return
            clients = [val.fileobj for val in self.sel.get_map().values() \
                       if val.fileobj != main_sock]
            for client in clients:
                self.send_keepalive(client)

    def setup_err(self, e=None):
        if e is not None:
            print(e)
        retry = input('retry? (y/n): ')
        if retry == 'y':
            return self.main()
        elif retry == 'n':
            exit(0)
        else:
            print('invalid input')
            return self.setup_err(e)

    def main(self):
        ''' creates a socket to listen on and enters a loop '''
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as main_sock:
            self.sel.register(main_sock, selectors.EVENT_READ)
            main_sock.settimeout(TIMEOUT)
            try:
                main_sock.bind(('', IRC_SERVER_PORT))
            except OSError as e:
                return self.setup_err(e)
            print("listening")  # DEBUG
            main_sock.listen()
            print("looping")  # DEBUG
            try:
                keepalive_thread = threading.Thread(
                    target=self.send_keepalives, args=[main_sock]
                )
                keepalive_thread.start()
            except OSError as e:
                return self.setup_err(e)
            self.mainloop(main_sock)

    def mainloop(self, main_sock):
        try:
            while True:
                events = self.sel.select(timeout=TIMEOUT)
                for key, _ in events:
                    if key.fileobj == main_sock:  # new client
                        self.accept_new_user(main_sock)
                    else:  # established client
                        # (keepalive, msg, err, join, leave, or list pkt)
                        client_sock = key.fileobj
                        this_user = None
                        for user in self.users:
                            if user.sock == client_sock:
                                this_user = user
                                break
                        if this_user is None:
                            print(f'ERROR: could not find user '
                                  + f'with socket {client_sock}')  # ERR
                            continue
                        self.receive_from_client(this_user)
        except KeyboardInterrupt as kbi:
            self.terminate_flag = True  # terminate keepalive thread
            self.close_and_clean()  # close all connections
            main_sock.close()
            exit(0)

    def receive_from_client(self, this_user):
        ''' receives a packet from the given socket and reacts to it '''
        try:
            header_bytes = this_user.sock.recv(IrcHeader.header_length)
            if header_bytes == b'':
                # print(f'received nothing from {this_user.sock.getpeername()}')
                return  # not sure why this happens...
                # if there's no inbound traffic why does the FD get selected?
            header_obj = IrcHeader().from_bytes(header_bytes)
            payload_bytes = this_user.sock.recv(header_obj.length)
            packet_bytes = header_bytes + payload_bytes
            msg_obj = None

            if header_obj.opcode == IRC_KEEPALIVE:
                print(f'received keepalive from '
                      + f'{this_user.sock.getpeername()}') # DEBUG
                # RFC does not specify that we have to do anything here
                # only that we MUST send keepalives and SHOULD receive them

            elif header_obj.opcode == IRC_SENDMSG:
                msg_obj = IrcPacketSendMsg().from_bytes(packet_bytes)
                print(f'received sendmsg from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                self.send_msg(this_user, msg_obj)

            elif header_obj.opcode == IRC_SENDPRIVMSG:
                msg_obj = IrcPacketSendPrivMsg().from_bytes(packet_bytes)
                print(f'received send priv msg from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                self.send_priv_msg(this_user, msg_obj)

            elif header_obj.opcode == IRC_ERR:
                print(f'received err from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                msg_obj = IrcPacketErr().from_bytes(packet_bytes)
                self.react_to_client_err(this_user, msg_obj)

            elif header_obj.opcode == IRC_JOINROOM:
                print(f'received join from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                msg_obj = IrcPacketJoinRoom().from_bytes(packet_bytes)
                self.add_user_to_room(this_user, msg_obj)

            elif header_obj.opcode == IRC_LEAVEROOM:
                print(f'received leave from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                msg_obj = IrcPacketLeaveRoom().from_bytes(packet_bytes)
                self.remove_user_from_room(this_user, msg_obj.payload)

            elif header_obj.opcode == IRC_LISTROOMS:
                print(f'received listrooms from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                self.send_room_list(this_user)

            elif header_obj.opcode == IRC_LISTUSERS:
                print(f'received listusers from '
                      + f'{this_user.sock.getpeername()}')  # DEBUG
                msg_obj = IrcPacketListUsers().from_bytes(packet_bytes)
                self.user_requests_user_list(this_user, msg_obj)

            else:
                print(f'WARNING! OPCODE NOT KNOWN TO SERVER\nreceived opcode '
                      + f'{header_obj.opcode} from {this_user.sock.getpeername()};'
                        + f'\nnot yet implemented!')  # DEBUG

        except IRCException as e:
            print('ERROR: receive_from_client() caught an IRCException - '
                  + f'malformed client packet?')  # ERR
            self.close_and_clean(this_user.sock)
        except OSError as e:  # tried to read from a dead connection
            if this_user.sock.fileno() != -1:
                print(f'Lost connection to {this_user.sock}; '
                      + f'removing from server')  # DEBUG
                self.sel.unregister(this_user.sock)
            self.clean_userlist(this_user.sock)
            this_user.sock.close()
            return


if __name__ == '__main__':
    Server().main()
