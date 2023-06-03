''' conf.py ~ Amelia Miner, Sarvesh Biradar
'   Contains common structures & global variables/config for both server.py and client.py.
'''

import sys

# network config
IRC_SERVER_PORT = 7734
TIMEOUT = 5

# IRC version
IRC_VERSION = 0x1337

IRC_COMMAND_VALUES = [i for i in range(0x00, 0x0B)] # for validation
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

IRC_ERR_VALUES = [i for i in range(0x10, 0x19)] # for validation
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

class IrcHeader:
    ''' holds the header of an IRC message
    '   opcode: IRC command
    '   len: length of associated message body in bytes
    '   version: IRC version in use by creator of message
    '''
    def __init__(self, opcode, length):
        self.opcode = opcode # should be 1 byte
        self.length = length # should be 4 bytes
    
    def construct_header(self):
        ''' returns a byte representation of the header '''
        opcode_bytes = self.header.opcode.to_bytes(1, 'big')
        length_bytes = self.header.length.to_bytes(4, 'big')
        return opcode_bytes + length_bytes


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

    def construct_packet(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if not validate_label(self.payload):
            raise ValueError(f"Invalid username: {self.payload}")
        # construct and return bytestring
        header_bytes = self.header.construct_header()
        payload_bytes = label_to_bytes(self.payload)
        version_bytes = self.version.to_bytes('big')
        return header_bytes + payload_bytes + version_bytes
        

class IrcPacketMsg:
    ''' has a header, holds the body of an IRC message
    '   header: irc_header object
    '   payload: message body
    '''
    def __init__(self, opcode, payload):
        self.header = IrcHeader(opcode, len(payload))
        self.payload = payload

    def construct_packet(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if self.header.opcode not in IRC_COMMAND_VALUES:
            raise ValueError(f"Invalid opcode: {self.header.opcode}")
        if self.header.length != len(self.payload):
            raise ValueError(f"Invalid length: {self.header.length}")
        # construct and return bytestring
        header_bytes = self.header.construct_header()
        payload_bytes = self.payload.encode('ascii')
        return header_bytes + payload_bytes


class IrcPktErr:
    ''' has a header, holds the body of an IRC error message
    '   header: irc_header object
    '   payload: error message body
    '''
    def __init__(self, payload):
        self.header = IrcHeader(IRC_ERR, 1)
        self.payload = payload # should be an IRC_ERR_* code, 1 byte

    def construct_packet(self):
        # validate fields
        if self.payload not in IRC_ERR_VALUES:
            raise ValueError(f"Invalid error code: {self.payload}")
        # construct and return bytestring
        opcode_bytes = self.header.opcode.to_bytes(1, 'big')
        length_bytes = self.header.length.to_bytes(4, 'big')
        payload_bytes = self.payload.to_bytes(1, 'big')
        return opcode_bytes + length_bytes + payload_bytes


class IrcPktKeepalive:
    ''' has a header, holds the body of an IRC keepalive message
    '   header: irc_header object
    '   version: IRC version in use by creator of message
    '''
    def __init__(self):
        self.header = IrcHeader(IRC_KEEPALIVE, 0)

    def construct_packet(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if self.header.opcode != IRC_KEEPALIVE:
            raise ValueError(f"Invalid opcode: {self.header.opcode}")
        # construct and return bytestring
        header_bytes = self.header.construct_header()
        return header_bytes

def close_on_err(sock, err_code, err_msg=None):
    ''' closes a socket and prints an error message
    '   sock: socket to close
    '   err_code: error code to send
    '   err_msg: error message to print
    '''
    print(err_msg)
    sock.send(IrcPktErr(err_code).construct_packet())
    sock.close()
    sys.exit(1)

def validate_string(string):
    ''' checks that all chars in a string are between ascii 0x20 and 0x7E (inclusive)
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
    ''' checks if a label is a valid string & valid length
    '   label: label to check
    '   returns: True if valid, False otherwise
    '''
    return len(label) <= 32 and validate_string(label)

def label_to_bytes(label):
    ''' converts a label to 32 byte null-padded bstring
    '   label: label to convert
    '   returns: byte representation of label
    '''
    return label.encode('ascii').ljust(32, b'\x00')