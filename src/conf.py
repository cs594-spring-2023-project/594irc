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
IRC_ERR_ILLEGAL_LENGTH = 0x12
IRC_ERR_ILLEGAL_LABEL = 0x13
IRC_ERR_ILLEGAL_MSG = 0x14
IRC_ERR_WRONG_VERSION = 0x15
IRC_ERR_NAME_EXISTS = 0x16
IRC_ERR_TOO_MANY_USERS = 0x17
IRC_ERR_TOO_MANY_ROOMS = 0x18

class IRCException(Exception):
    def __init__(self, code):
        self.irc_err_code = code

# packet classes
# could be more DRY and better organized with inheritance but this is simpler for now
# construct_* packs packet contents into a bytestring;
# parse_* may be a good idea, and would unpack a bytestring into a packet object

class IrcHeader:
    ''' holds the header of an IRC message
    '   opcode: IRC command
    '   length: length of associated message body in bytes
    '   version: IRC version in use by creator of message
    '''
    opcode_length = 1
    length_length = 4
    header_length = opcode_length + length_length
    def __init__(self, opcode, length):
        self.opcode = opcode # should be 1 byte
        self.length = length # should be 4 bytes
    
    def to_bytes(self):
        ''' returns a byte representation of the header '''
        opcode_bytes = self.opcode.to_bytes(1, 'big')
        length_bytes = self.length.to_bytes(4, 'big')
        return opcode_bytes + length_bytes


class IrcPacketHello:
    ''' has a header, holds the body of an IRC hello message
    '   header: irc_header object
    '   payload: username
    '   version: IRC version in use by creator of message
    '''
    name_length = 32
    version_length = 2
    payload_length = name_length + version_length
    packet_length = IrcHeader.header_length + payload_length
    def __init__(self, username=None, version=IRC_VERSION, length=None):
        if length is None:
            length = IrcPacketHello.payload_length
        self.header = IrcHeader(IRC_HELLO, length)
        self.payload = username
        self.version = version

    def to_bytes(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if not validate_label(self.payload):
            raise ValueError(f"Invalid username: {self.payload}")
        # construct and return bytestring
        header_bytes = self.header.to_bytes()
        payload_bytes = label_to_bytes(self.payload)
        version_bytes = self.version.to_bytes(IrcPacketHello.version_length, 'big')
        return header_bytes + payload_bytes + version_bytes
        
    def from_bytes(self, received_hello):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketHello object
        '   intended to consume the output of socket.recv()
        '''
        # define field boundaries
        len_bytes = received_hello[1:IrcHeader.length_length+1]
        name_bytes = received_hello[
            IrcHeader.header_length : IrcHeader.header_length + IrcPacketHello.name_length
        ]
        version_bytes = received_hello[IrcHeader.header_length + IrcPacketHello.name_length:]
        # parse bytes and validate
        if received_hello[0] != IRC_HELLO:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE)
        if int.from_bytes(len_bytes, 'big') != IrcPacketHello.payload_length:
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH)
        username_as_received = name_bytes.decode('ascii')
        if not validate_label(username_as_received):
            raise IRCException(IRC_ERR_ILLEGAL_LABEL)
        username = strip_null_bytes(username_as_received)
        version = int.from_bytes(version_bytes, 'big')
        if version != IRC_VERSION:
            raise IRCException(IRC_ERR_WRONG_VERSION)
        # construct and return
        self.header = IrcHeader(IRC_HELLO, IrcPacketHello.payload_length)
        self.payload = username
        self.version = version
        return self

class IrcPacketMsg:
    ''' has a header, holds the body of an IRC message
    '   header: irc_header object
    '   payload: message body
    '''
    def __init__(self, opcode, payload):
        self.header = IrcHeader(opcode, len(payload))
        self.payload = payload

    def to_bytes(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if self.header.opcode not in IRC_COMMAND_VALUES:
            raise ValueError(f"Invalid opcode: {self.header.opcode}")
        if self.header.length != len(self.payload):
            raise ValueError(f"Invalid length: {self.header.length}")
        # construct and return bytestring
        header_bytes = self.header.to_bytes()
        payload_bytes = self.payload.encode('ascii')
        return header_bytes + payload_bytes


class IrcPktErr:
    ''' has a header, holds the body of an IRC error message
    '   header: irc_header object
    '   payload: error message body
    '   may be nice to add a message field to err packets...
    '''
    errcode_length = 1
    payload_length = errcode_length
    packet_length = IrcHeader.header_length + payload_length
    def __init__(self, payload):
        self.header = IrcHeader(IRC_ERR, IrcPktErr.payload_length)
        self.payload = payload # should be an IRC_ERR_* code, 1 byte

    def to_bytes(self):
        ''' returns a byte representation of the packet
        currently does not use message from  close_on_err...
        '''
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
    payload_length = 0
    packet_length = IrcHeader.header_length + payload_length
    def __init__(self):
        self.header = IrcHeader(IRC_KEEPALIVE, IrcPktKeepalive.payload_length)

    def to_bytes(self):
        ''' returns a byte representation of the packet '''
        # validate fields
        if self.header.opcode != IRC_KEEPALIVE:
            raise ValueError(f"Invalid opcode: {self.header.opcode}")
        # construct and return bytestring
        header_bytes = self.header.to_bytes()
        return header_bytes

# globally useful functions

def close_on_err(sock, err_code, err_msg=None):
    ''' closes a socket and prints an error message
    '   sock: socket to close
    '   err_code: error code to send
    '   err_msg: error message to print
    '''
    print(err_msg)
    sock.send(IrcPktErr(err_code).to_bytes())
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
    for i, char in enumerate(string):
        if ord(char) < 0x20 or ord(char) > 0x7E and (ord(char) != 0x0A or ord(char) != 0x0D):
            if ord(char) == 0x00 and i != 0:
                break # null terminator is allowed, but only if there's at least 1 char prior
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

def strip_null_bytes(string):
    ''' strips null bytes from a string '''
    return string.rstrip('\x00')