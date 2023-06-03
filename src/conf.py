''' conf.py ~ Amelia Miner, Sarvesh Biradar
'   Contains common structures & global variables/config for both server.py and client.py.
'''

import sys

# network config
IRC_SERVER_PORT = 7734
TIMEOUT = 5

# IRC version
IRC_VERSION = 0x1337

# IRC commands ~ client or server
IRC_ERR = 0x00
IRC_KEEPALIVE = 0x01
# IRC commands ~ client only
IRC_HELLO = 0x02
IRC_LISTROOMS = 0x03
IRC_LISTUSERS = 0x04
IRC_JOINROOM = 0x05
IRC_LEAVEROOM = 0x06
IRC_SENDMSG = 0x07
# IRC commands ~ server only
IRC_LISTROOMS_RESP = 0x08
IRC_LISTUSERS_RESP = 0x09
IRC_TELLMSG = 0x0A

# IRC error codes
IRC_ERR_UNKNOWN = 0x10
IRC_ERR_ILLEGAL_OPCODE = 0x11
IRC_ERR_ILLEGAL_LEN = 0x12
IRC_ERR_ILLEGAL_LABEL = 0x13
IRC_ERR_ILLEGAL_MSG = 0x14
IRC_ERR_WRONG_VER = 0x15
IRC_ERR_NAME_EXISTS = 0x16
IRC_ERR_TOO_MANY_USERS = 0x17
IRC_ERR_TOO_MANY_ROOMS = 0x18

# generic message format
class IrcHeader:
    ''' holds the header of an IRC message
    '   opcode: IRC command
    '   len: length of associated message body in bytes
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, opcode, length):
        self.version = version
        self.opcode = opcode
        self.length = length

class IrcPacketHello:
    ''' has a header, holds the body of an IRC hello message
    '   header: irc_header object
    '   payload: username
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, username, version=IRC_VERSION):
        self.header = IrcHeader(IRC_HELLO, 32 + 2)
        self.payload = username # should be 32 bytes
        self.version = version # should be 2 bytes

class IrcPacketMsg:
    ''' has a header, holds the body of an IRC message
    '   header: irc_header object
    '   payload: message body
    '''
    def __init__(self, opcode, payload):
        self.header = IrcHeader(opcode, len(payload))
        self.payload = payload

class IrcPktErr:
    ''' has a header, holds the body of an IRC error message
    '   header: irc_header object
    '   payload: error message body
    '''
    def __init__(self, payload):
        self.header = IrcHeader(IRC_ERR, 1)
        self.payload = payload # should be an IRC_ERR_* code

class IrcPktKeepalive:
    ''' has a header, holds the body of an IRC keepalive message
    '   header: irc_header object
    '   version: IRC version in use by creator of message
    '''
    def __init__(self):
        self.header = IrcHeader(IRC_KEEPALIVE, 0)

def close_on_err(sock, err):
    ''' closes a socket and prints an error message
    '   sock: socket to close
    '   err: error message to print
    '''
    print(err)
    sock.close()
    sys.exit(1)

def validate_string(string):
    ''' checks that all chars in a string are between 0x20 and 0x7E (inclusive)
    '   or are 0x0A or 0x0D
    '   string: string to check
    '   returns: True if valid, False otherwise
    '''
    try:
        string.encode('ascii')
    except UnicodeEncodeError:
        return False
    for char in string:
        if ord(char) < 0x20 or ord(char) > 0x7E and (ord(char) != 0x0A or ord(char) != 0x0D):
            return False
    return True

def validate_label(label):
    ''' checks if a label is valid
    '   label: label to check
    '   returns: True if valid, False otherwise
    '''
    return len(label) <= 32 and validate_string(label)