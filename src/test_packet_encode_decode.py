''' tests packet init, to_bytes and from_bytes methods, and validation functions
'   not quite unit tests, but close enough to be valuable
'   excludes tests for empty packet types (list rooms, etc.)
'''

from random import choice, shuffle
from sys import argv
from time import sleep
from conf import *
from socket import *
sock = socket(AF_INET, SOCK_STREAM)
sock2 = socket(AF_INET, SOCK_STREAM)

VALID_MESSAGES = ['1', 'testmsg', 'bigger message with other characters /.,?~!@#$%^&*()_+=-;\'":',
            b'0x0D0x0Athis has some line breaks 0x0D0x0A^See? This is the same string! ^'.decode('ascii'),
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'
]

INVALID_MESSAGES = [' spaces in', 'bad places ', ' ', '']

VALID_LABELS = ['xX_ChickenWing_Xx', '123bunchanumbers890', ':)']

INVALID_LABELS = [' more bad spaces ', ' ', '']

def test_header():
    print('test_header')
    header = IrcHeader(IRC_HELLO, 0)
    headerbytes = header.to_bytes()
    header2 = IrcHeader().from_bytes(headerbytes)
    assert header2.opcode == IRC_HELLO
    assert header2.length == 0
    print('test_header passed')

def test_err():
    print('test_err')
    errpacket = IrcPacketErr(IRC_ERR_ILLEGAL_LABEL)
    errbytes = errpacket.to_bytes()
    errpacket2 = IrcPacketErr().from_bytes(errbytes)
    assert errpacket2.payload == IRC_ERR_ILLEGAL_LABEL
    print('test_err passed')

def test_hello():
    print('test_hello')
    label = choice(VALID_LABELS)
    hellopacket = IrcPacketHello(label)
    hellobytes = hellopacket.to_bytes()
    hellopacket2 = IrcPacketHello().from_bytes(hellobytes)
    assert hellopacket2.payload == label
    print('test_hello passed')

def test_join_room():
    print('test_join_room')
    label = choice(VALID_LABELS)
    joinpacket = IrcPacketJoinRoom(label)
    joinbytes = joinpacket.to_bytes()
    joinpacket2 = IrcPacketJoinRoom().from_bytes(joinbytes)
    assert joinpacket2.payload == label
    print('test_join_room passed')

def test_leave_room():
    print('test_leave_room')
    label = choice(VALID_LABELS)
    leavepacket = IrcPacketLeaveRoom(label)
    leavebytes = leavepacket.to_bytes()
    leavepacket2 = IrcPacketLeaveRoom().from_bytes(leavebytes)
    assert leavepacket2.payload == label
    print('test_leave_room passed')

def test_list_users():
    print('test_list_users')
    label = choice(VALID_LABELS)
    listuserspacket = IrcPacketListUsers(label)
    listusersbytes = listuserspacket.to_bytes()
    listuserspacket2 = IrcPacketListUsers().from_bytes(listusersbytes)
    assert listuserspacket2.payload == label
    print('test_list_users passed')

def test_list_rooms_response():
    print('entering test_list_rooms_response')
    label1, label2 = choice(VALID_LABELS), choice(VALID_LABELS)
    listroomsresponsepacket = IrcPacketListRoomsResp([label1, label2])
    listroomsresponsebytes = listroomsresponsepacket.to_bytes()
    listroomsresponsepacket2 = IrcPacketListRoomsResp().from_bytes(listroomsresponsebytes)
    assert listroomsresponsepacket2.payload == [label1, label2]
    print('test_list_rooms_response passed')

def test_list_users_response():
    print('entering test_list_users_response')
    label1, label2, label3 = choice(VALID_LABELS), choice(VALID_LABELS), choice(VALID_LABELS)
    listusersresponsepacket = IrcPacketListUsersResp(payload=[label1, label2], identifier=label3)
    listusersresponsebytes = listusersresponsepacket.to_bytes()
    listusersresponsepacket2 = IrcPacketListUsersResp().from_bytes(listusersresponsebytes)
    assert listusersresponsepacket2.payload == [label1, label2]
    assert listusersresponsepacket2.identifier == label3
    print('test_list_users_response passed')

def test_send():
    print('entering test_send')
    payload = choice(VALID_MESSAGES)
    room = choice(VALID_LABELS)
    sendmsgtest = IrcPacketSendMsg(payload=payload, target_room=room)
    sendbytes = sendmsgtest.to_bytes()
    sendmsgtest2 = IrcPacketSendMsg().from_bytes(sendbytes)
    assert sendmsgtest2.payload == payload
    assert sendmsgtest2.target_room == room
    print('test_send passed')

def test_tell():
    print('entering test_tell')
    payload = choice(VALID_MESSAGES)
    room = choice(VALID_LABELS)
    usr = choice(VALID_LABELS)
    tellmsgtest = IrcPacketTellMsg(payload=payload, target_room=room, sending_user=usr)
    tellbytes = tellmsgtest.to_bytes()
    tellmsgtest2 = IrcPacketTellMsg().from_bytes(tellbytes)
    assert tellmsgtest2.payload == payload
    assert tellmsgtest2.target_room == room
    assert tellmsgtest2.sending_user == usr
    print('test_tell passed')

def test_all():
    print('entering test_all')
    # run every function in the namespace that starts with test_ except this one
    funcs = []
    for func in globals().values():
        if callable(func) and func.__name__[0:5] == 'test_' and func != test_all:
            funcs.append(func)
    shuffle(funcs)
    for func in  funcs:
        func()
    print('all tests passed')

if __name__ == '__main__':
    test_all()