''' tests packet init, to_bytes and from_bytes methods, and validation functions
'   not quite unit tests, but close enough to be valuable
'   excludes tests for empty packet types (list rooms, etc.)
'''

from random import choice
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

INVALID_MESSAGES = [' spaces in', 'bad places ', ' ', '']

VALID_LABELS = ['xX_ChickenWing_Xx', '123bunchanumbers890', ':)']

INVALID_LABELS = [' more bad spaces ', ' ', '']

def test_header():
    header = IrcHeader(IRC_HELLO, 0)
    headerbytes = header.to_bytes()
    header2 = IrcHeader().from_bytes(headerbytes)
    assert header2.opcode == IRC_HELLO
    assert header2.length == 0

def test_err():
    errpacket = IrcPacketErr(IRC_ERR_ILLEGAL_LABEL)
    errbytes = errpacket.to_bytes()
    errpacket2 = IrcPacketErr().from_bytes(errbytes)
    assert errpacket2.payload == IRC_ERR_ILLEGAL_LABEL

def test_hello():
    label = choice(VALID_LABELS)
    hellopacket = IrcPacketHello(label)
    hellobytes = hellopacket.to_bytes()
    hellopacket2 = IrcPacketHello().from_bytes(hellobytes)
    assert hellopacket2.payload == label

def test_join_room():
    label = choice(VALID_LABELS)
    joinpacket = IrcPacketJoinRoom(label)
    joinbytes = joinpacket.to_bytes()
    joinpacket2 = IrcPacketJoinRoom().from_bytes(joinbytes)
    assert joinpacket2.payload == label

def test_leave_room():
    label = choice(VALID_LABELS)
    leavepacket = IrcPacketLeaveRoom(label)
    leavebytes = leavepacket.to_bytes()
    leavepacket2 = IrcPacketLeaveRoom().from_bytes(leavebytes)
    assert leavepacket2.payload == label

def test_list_users():
    label = choice(VALID_LABELS)
    listuserspacket = IrcPacketListUsers(label)
    listusersbytes = listuserspacket.to_bytes()
    listuserspacket2 = IrcPacketListUsers().from_bytes(listusersbytes)
    assert listuserspacket2.payload == label

def test_list_rooms_response():
    label1, label2 = choice(VALID_LABELS), choice(VALID_LABELS)
    listroomsresponsepacket = IrcPacketListRoomsResp([label1, label2])
    listroomsresponsebytes = listroomsresponsepacket.to_bytes()
    listroomsresponsepacket2 = IrcPacketListRoomsResp().from_bytes(listroomsresponsebytes)
    assert listroomsresponsepacket2.payload == [label1, label2]

def test_list_users_response():
    label1, label2, label3 = choice(VALID_LABELS), choice(VALID_LABELS), choice(VALID_LABELS)
    listusersresponsepacket = IrcPacketListUsersResp(payload=[label1, label2], identifier=label3)
    listusersresponsebytes = listusersresponsepacket.to_bytes()
    listusersresponsepacket2 = IrcPacketListUsersResp().from_bytes(listusersresponsebytes)
    assert listusersresponsepacket2.payload == [label1, label2]
    assert listusersresponsepacket2.identifier == label3

def test_send():
    sendmsgtest = IrcPacketSendMsg(payload='testmsg', target_room='testroom')
    sendbytes = sendmsgtest.to_bytes()
    sendmsgtest2 = IrcPacketSendMsg().from_bytes(sendbytes)
    assert sendmsgtest2.payload == 'testmsg'
    assert sendmsgtest2.target_room == 'testroom'

def test_tell():
    tellmsgtest = IrcPacketTellMsg(payload='testmsg', target_room='testroom', sending_user='testuser')
    tellbytes = tellmsgtest.to_bytes()
    tellmsgtest2 = IrcPacketTellMsg().from_bytes(tellbytes)
    assert tellmsgtest2.payload == 'testmsg'
    assert tellmsgtest2.target_room == 'testroom'
    assert tellmsgtest2.sending_user == 'testuser'

def test_all():
    # run every function in the file except this one
    for func in globals().values():
        if callable(func) and func.__name__[0:5] == 'test_' and func != test_all:
            func()

if __name__ == '__main__':
    test_all()