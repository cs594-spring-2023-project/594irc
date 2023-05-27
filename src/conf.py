''' conf.py ~ Amelia Miner, Sarvesh Biradar
'   Contains common structures & global variables/config for both server.py and client.py.
'''

# network config
IRC_SERVER_PORT = 7734
TIMEOUT = 5

# IRC version
IRC_VERSION = 0x1337

# IRC commands ~ client or server
IRC_ERR = 0X00
IRC_KEEPALIVE = 0X01
# IRC commands ~ client only
IRC_HELLO = 0X02
IRC_LISTROOMS = 0X03
IRC_LISTUSERS = 0X04
IRC_JOINROOM = 0X05
IRC_LEAVEROOM = 0X06
IRC_SENDMSG = 0X07
# IRC commands ~ server only
IRC_LISTROOMS_RESP = 0X08
IRC_LISTUSERS_RESP = 0X09
IRC_TELLMSG = 0X0A

# IRC error codes
IRC_ERR_UNKNOWN = 0X10
IRC_ERR_ILLEGAL_OPCODE = 0X11
IRC_ERR_ILLEGAL_LEN = 0X12
IRC_ERR_ILLEGAL_LABEL = 0X13
IRC_ERR_ILLEGAL_MSG = 0X14
IRC_ERR_WRONG_VER = 0X15
IRC_ERR_NAME_EXISTS = 0X16
IRC_ERR_TOO_MANY_USERS = 0X17
IRC_ERR_TOO_MANY_ROOMS = 0X18

# generic message format
class IrcHeader:
    ''' holds the header of an IRC message
    '   opcode: IRC command
    '   len: length of associated message body in bytes
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, opcode, length, version=IRC_VERSION):
        self.version = version
        self.opcode = opcode
        self.length = length

class IrcPacketMsg:
    ''' has a header, holds the body of an IRC message
    '   header: irc_header object
    '   payload: message body
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, opcode, payload, version=IRC_VERSION):
        self.header = IrcHeader(opcode, len(payload), version)
        self.payload = payload

class IrcPktErr:
    ''' has a header, holds the body of an IRC error message
    '   header: irc_header object
    '   payload: error message body
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, payload, version=IRC_VERSION):
        self.header = IrcHeader(IRC_ERR, 1, version)
        self.payload = payload # should be an IRC_ERR_* code

class IrcPktKeepalive:
    ''' has a header, holds the body of an IRC keepalive message
    '   header: irc_header object
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, version=IRC_VERSION):
        self.header = IrcHeader(IRC_KEEPALIVE, 0, version)