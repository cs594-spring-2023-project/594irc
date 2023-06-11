''' conf.py ~ Amelia Miner
'   Contains common structures & global variables/config for both server.py and client.py.
'   as well as packet classes for now.
'   packet classes all have a to_bytes() and from_bytes() method for serialization into a socket and
'   deserialization out of a socket respectively.
'   packet classes also have a validate() method for validating the packet's fields.
'   this method should be called initially on to_bytes and toward the end of from_bytes to catch any
'   protocol violations.
'   validate raises an IRCException on protocol violations, which generally should lead to the detecting
'   party informing the other party of the error and closing the connection.
'''

from abc import ABC
import socket

# network config
IRC_SERVER_PORT = 7734
TIMEOUT = 5
LABEL_LENGTH = 32
MAX_MSG_LENGTH = 7999

# IRC version
IRC_VERSION = 0x1337

IRC_COMMAND_VALUES = [i for i in range(0x00, 0x0B)]  # for validation
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

IRC_ERR_VALUES = [i for i in range(0x10, 0x19)]  # for validation
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
    def __init__(self, code, msg=None):
        self.err_code = code
        self.err_msg = msg

# packet classes
# could be more DRY and better organized with different inheritance
# but this is simpler for now
# to_bytes packs packet contents into a bytestring;
# from_bytes unpacks a bytestring into the packet object
# validate should be run at beginning of to_bytes and at end of from_bytes

class IrcHeader:
    ''' holds the header of an IRC message
    '   opcode: IRC command
    '   length: length of associated message body in bytes
    '   version: IRC version in use by creator of message
    '''
    opcode_length = 1
    length_length = 4
    header_length = opcode_length + length_length

    def __init__(self, opcode=None, length=None):
        self.opcode = opcode  # should be 1 byte
        self.length = length  # should be 4 bytes

    def validate(self):
        ''' assumes that int.to_bytes and label_to_bytes are used in egress code '''
        if self.opcode not in IRC_COMMAND_VALUES:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE, f'Invalid opcode: {self.opcode}')

    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the header
        '''
        self.validate()
        opcode_bytes = self.opcode.to_bytes(1, 'big')
        length_bytes = self.length.to_bytes(4, 'big')
        return opcode_bytes + length_bytes

    def from_bytes(self, received_header):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcHeader object
        '   intended to consume the output of socket.recv()
        '''
        # define field boundaries
        opcode_bytes = received_header[0:IrcHeader.opcode_length]
        len_bytes = received_header[IrcHeader.opcode_length:IrcHeader.header_length]
        # construct and return self
        opcode = int.from_bytes(opcode_bytes, 'big')
        length = int.from_bytes(len_bytes, 'big')
        self.opcode = opcode
        self.length = length
        return self


class IrcPacketErr:
    ''' has a header, holds the body of an IRC error message
    '   header: irc_header object
    '   payload: error code
    '   may be nice to add a message field to err packets...
    '''
    errcode_length = 1
    payload_length = errcode_length
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, payload=None):
        self.header = IrcHeader(IRC_ERR, IrcPacketErr.payload_length)
        self.payload = payload  # should be an IRC_ERR_* code, 1 byte

    def validate(self):
        ''' assumes that int.to_bytes and label_to_bytes are used in egress code '''
        self.header.validate()
        if self.header.length != IrcPacketErr.payload_length:
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
        if self.payload not in IRC_ERR_VALUES:
            raise IRCException(IRC_ERR_ILLEGAL_MSG, f'Invalid error code: {self.payload}')

    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the packet
        '''
        self.validate()
        header_bytes = self.header.to_bytes()
        payload_bytes = self.payload.to_bytes(1, 'big')
        return header_bytes + payload_bytes

    def from_bytes(self, received_hello):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketErr object
        '   intended to consume the output of socket.recv()
        '  !!! DOES NOT call self.validate() !!!
        '   if we are parsing an err message, the connection has been terminated
        '''
        # define field boundaries - may be a better way to do this, remove bytes as they're parsed?
        # error code
        errcode_bytes = received_hello[IrcHeader.header_length: IrcHeader.header_length + IrcPacketErr.errcode_length]
        # parse bytes and do not validate (connection dead)
        errcode = int.from_bytes(errcode_bytes, 'big')
        # construct and return
        self.header = IrcHeader().from_bytes(received_hello[0:IrcHeader.header_length])
        self.payload = errcode
        return self


class IrcPacketHello:
    ''' has a header, holds the body of an IRC hello message
    '   header: irc_header object
    '   payload: username
    '   version: IRC version in use by creator of message
    '''
    version_length = 2
    payload_length = LABEL_LENGTH + version_length
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, username=None, version=IRC_VERSION, length=None):
        if length is None:
            length = IrcPacketHello.payload_length
        self.header = IrcHeader(IRC_HELLO, length)
        self.payload = username
        self.version = version

    def validate(self, native_labels=False):
        ''' assumes that int.to_bytes and label_to_bytes are used in egress code '''
        self.header.validate()
        if self.header.length != \
                len(label_to_bytes(self.payload)) \
                + len(self.version.to_bytes(IrcPacketHello.version_length, 'big')):
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
        if self.version != IRC_VERSION:
            raise IRCException(IRC_ERR_WRONG_VERSION, f'Invalid version: {self.version}')
        if native_labels:
            if not validate_label(label_to_bytes(self.payload)):
                raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid username: {self.payload}')
        elif not validate_label(self.payload):
            raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid username: {self.payload}')

    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the packet
        '''
        self.validate(native_labels=True)
        header_bytes = self.header.to_bytes()
        payload_bytes = label_to_bytes(self.payload)
        version_bytes = self.version.to_bytes(IrcPacketHello.version_length, 'big')
        return header_bytes + payload_bytes + version_bytes

    def from_bytes(self, received_hello):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketHello object
        '   intended to consume the output of socket.recv()
        '''
        # define field boundaries - may be a better way to do this, remove bytes as they're parsed?
        self.header = IrcHeader().from_bytes(received_hello[0:IrcHeader.header_length])
        name_bytes = received_hello[
                     IrcHeader.header_length: IrcHeader.header_length + LABEL_LENGTH
                     ]
        version_bytes = received_hello[IrcHeader.header_length + LABEL_LENGTH:]
        # parse bytes into self
        username_as_received = name_bytes.decode('ascii')
        self.payload = username_as_received  # keep as is for validation for now
        version = int.from_bytes(version_bytes, 'big')
        self.version = version
        # validate
        self.validate()
        # clean up and return
        self.payload = strip_null_bytes(username_as_received)
        return self


class IrcPacketRoomOp(ABC):
    ''' has a header, holds the body of an IRC join or leave message
    '   header: irc_header object
    '   payload: room name
    '''
    payload_length = LABEL_LENGTH
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, opcode, room_name=None):
        self.init_opcode = opcode
        length = IrcPacketRoomOp.payload_length
        self.header = IrcHeader(opcode, length)
        self.payload = room_name

    def validate(self, native_labels=False):
        ''' assumes that int.to_bytes and label_to_bytes are used in egress code '''
        self.header.validate()
        if self.header.length != len(label_to_bytes(self.payload)):
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
        if native_labels:
            if not validate_label(label_to_bytes(self.payload)):
                raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid room name: {self.payload}')
        elif not validate_label(self.payload):
            raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid room name: {self.payload}')

    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the packet
        '''
        self.validate(native_labels=True)
        header_bytes = self.header.to_bytes()
        payload_bytes = label_to_bytes(self.payload)
        return header_bytes + payload_bytes

    def from_bytes(self, received_hello):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketHello object
        '   intended to consume the output of socket.recv()
        '''
        # define field boundaries - may be a better way to do this, remove bytes as they're parsed?
        self.header = IrcHeader().from_bytes(received_hello[0:IrcHeader.header_length])
        room_name_bytes = received_hello[
                          IrcHeader.header_length: IrcHeader.header_length + LABEL_LENGTH
                          ]
        # parse bytes into self
        roomname_as_received = room_name_bytes.decode('ascii')
        self.payload = roomname_as_received  # keep as is for validation for now
        # validate
        self.validate()
        # clean up and return
        self.payload = strip_null_bytes(roomname_as_received)
        return self


class IrcPacketJoinRoom(IrcPacketRoomOp):
    ''' has a header, holds the body of an IRC join or leave message
    '   header: irc_header object
    '   payload: room name
    '''
    payload_length = LABEL_LENGTH
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, room_name=None):
        super().__init__(IRC_JOINROOM, room_name)


class IrcPacketLeaveRoom(IrcPacketRoomOp):
    ''' has a header, holds the body of an IRC join or leave message
    '   header: irc_header object
    '   payload: room name
    '''
    payload_length = LABEL_LENGTH
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, room_name=None):
        super().__init__(IRC_LEAVEROOM, room_name)


class IrcPacketMsgOp(ABC):
    ''' has a header, holds the body of an IRC message. May be a send or a tell
    '   header: irc_header object
    '   payload: message body
    '   target_room: room name
    '   sending_user: username (only for tellmsg)
    '''

    def __init__(self, opcode, payload=None, target_room=None, sending_user=None):
        self.init_opcode = opcode
        self.header = None
        if payload is not None:
            if payload[-1] != '\0':
                payload += '\0'
            if target_room is not None:
                self.header = IrcHeader(opcode, len(payload)+LABEL_LENGTH)
        if opcode == IRC_TELLMSG: # tellmsg includes sending username
            if self.header is not None: # covers from_bytes case
                self.header.length += LABEL_LENGTH # high coupling but works in a time crunch...
        self.payload = payload
        self.sending_user = sending_user
        self.target_room = target_room

    def validate(self, native_labels=False, temp_msg=False):
        ''' assumes that int.to_bytes and label_to_bytes are used in egress code '''
        self.header.validate()
        if self.header.opcode != self.init_opcode:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE)
        expected_length = len(self.payload) + LABEL_LENGTH
        if self.sending_user is not None:
            expected_length += LABEL_LENGTH
        if self.header.length != expected_length:
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
        payload = self.payload
        target_room = self.target_room
        sending_user = self.sending_user
        if native_labels:
            target_room = label_to_bytes(target_room)
            sending_user = label_to_bytes(sending_user) if sending_user is not None else None
        if not validate_label(target_room):
            raise IRCException(IRC_ERR_ILLEGAL_LABEL)
        if not temp_msg and not validate_message(payload):
            raise IRCException(IRC_ERR_ILLEGAL_MSG)
        if sending_user is not None and not validate_label(sending_user):
            raise IRCException(IRC_ERR_ILLEGAL_LABEL)

    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the packet
        '''
        # validate fields
        self.validate(native_labels=True)
        # construct and return bytestring
        payload_bytes = self.payload.encode('ascii')
        if payload_bytes[-1] != 0:
            payload_bytes += 0
            self.header.length += 1 # for null byte
        header_bytes = self.header.to_bytes()
        room_bytes = label_to_bytes(self.target_room)
        sender_bytes = b''  # should be empty for sendmsg
        if self.sending_user is not None:
            sender_bytes = label_to_bytes(self.sending_user)
        # target room is last LABEL_LENGTH bytes for sendmsg
        # sender is last next-to-last LABEL_LENGTH bytes for tellmsg
        return header_bytes + payload_bytes + sender_bytes + room_bytes

    def from_bytes(self, received_msg, temp_msg=False):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketMsg object
        '   intended to consume the output of socket.recv()
        '   last LABEL_LENGTH bytes of message should be converted into sending_user for tell
        '''
        # define field boundaries - may be a better way to do this, remove bytes as they're parsed?
        self.header = IrcHeader().from_bytes(received_msg[0:IrcHeader.header_length])
        # message body
        payload_bytes = received_msg[IrcHeader.header_length: -LABEL_LENGTH]
        msg_body_as_received = payload_bytes.decode('ascii')
        # other label
        room_bytes = received_msg[-LABEL_LENGTH:]
        room_as_received = room_bytes.decode('ascii')
        # parse bytes and validate
        self.payload = msg_body_as_received
        self.target_room = room_as_received
        self.validate(temp_msg=temp_msg)
        # construct and return
        self.target_room = strip_null_bytes(room_as_received)
        if not temp_msg:
            self.payload = strip_null_bytes(self.payload)
        return self


class IrcPacketSendMsg(IrcPacketMsgOp):
    ''' has a header, holds the body of an IRC message. For client -> server messages
    '   header: irc_header object
    '   payload: message body
    '   other: recipient label
    '''

    def __init__(self, payload=None, target_room=None):
        super().__init__(IRC_SENDMSG, payload, target_room)
        # self.sending_user =


class IrcPacketTellMsg(IrcPacketMsgOp):
    ''' has a header, holds the body of an IRC message. For server -> client messages
    '   header: irc_header object
    '   payload: message body
    '   other: sender label
    '   target_name: room name
    '''

    def __init__(self, payload=None, target_room=None, sending_user=None):
        super().__init__(IRC_TELLMSG, payload=payload, target_room=target_room, sending_user=sending_user)
        # self.header.length += LABEL_LENGTH

    def from_bytes(self, received_msg):
        base_obj = super().from_bytes(received_msg, temp_msg=True) # sending_user in last LABEL_LENGTH bytes of msg
        base_msg = base_obj.payload
        self.sending_user = strip_null_bytes(base_msg[-LABEL_LENGTH:])
        self.payload = strip_null_bytes(base_msg[:-LABEL_LENGTH])
        return self

    # def to_bytes(self):
    # super().to_bytes() # debug


class IrcPacketEmpty(ABC):
    ''' has a header, holds the body of an IRC message with no payload
    '   header: irc_header object
    '  !No need for a from_bytes method, keepalive messages are not parsed
    '''
    payload_length = 0
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, opcode):
        self.init_opcode = opcode
        self.header = IrcHeader(opcode, IrcPacketEmpty.payload_length)

    def to_bytes(self):
        ''' returns a byte representation of the packet
        '   validates fields
        '''
        if self.header.opcode != self.init_opcode:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE, f'Invalid opcode: {self.header.opcode}')
        header_bytes = self.header.to_bytes()
        return header_bytes


class IrcPacketKeepalive(IrcPacketEmpty):
    ''' has a header, holds the body of an IRC keepalive message
    '   header: irc_header object
    '  !No need for a from_bytes method, keepalive messages are not parsed
    '''
    payload_length = 0
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self):
        super().__init__(IRC_KEEPALIVE)


class IrcPacketListRooms(IrcPacketEmpty):
    ''' has a header, holds the body of an IRC list rooms message
    '   header: irc_header object
    '  !No need for a from_bytes method, keepalive messages are not parsed
    '''
    payload_length = 0
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self):
        super().__init__(IRC_LISTROOMS)


class IrcPacketListUsers():
    ''' has a header, holds the body of an IRC list users message
    '   header: irc_header object
    '  !No need for a from_bytes method, keepalive messages are not parsed
    '''
    payload_length = LABEL_LENGTH
    packet_length = IrcHeader.header_length + payload_length

    def __init__(self, room_name=None):
        self.header = IrcHeader(IRC_LISTUSERS, IrcPacketListUsers.payload_length)
        self.header.length = IrcPacketListUsers.payload_length
        self.payload = room_name
    
    def validate(self, native_labels=False, temp_payload=False):
        self.header.validate()
        if self.header.opcode != IRC_LISTUSERS:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE, f'Invalid opcode: {self.header.opcode}')
        if not temp_payload:
            if self.header.length != IrcPacketListUsers.payload_length:
                raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
            if not native_labels and not validate_label(self.payload):
                raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid payload: {self.payload}')

    def to_bytes(self):
        ''' returns a byte representation of the packet '''
        self.validate(native_labels=True)
        header_bytes = self.header.to_bytes()
        payload_bytes = label_to_bytes(self.payload)
        return header_bytes + payload_bytes
    
    def from_bytes(self, received_msg):
        self.header = IrcHeader().from_bytes(received_msg[0:IrcHeader.header_length])
        self.payload = received_msg[IrcHeader.header_length:].decode('ascii')
        self.validate()
        self.payload = strip_null_bytes(self.payload)
        return self



class IrcPacketListResp(ABC):
    ''' has a header, holds a response to a list request
    '   header: irc_header object
    '   payload: list of labels
    '   identifier: used for listusers, name of room to list users in
    '''

    def __init__(self, opcode, payload=None, identifier=None):
        self.init_opcode = opcode
        packet_length = 0
        if payload is not None:
            packet_length = len(payload) * LABEL_LENGTH
        if identifier is not None:
            packet_length += LABEL_LENGTH
        self.header = IrcHeader(opcode, packet_length)
        self.payload = payload
        self.identifier = identifier
    
    def validate(self, native_labels=False):
        ''' validates fields '''
        self.header.validate()
        if self.header.opcode != self.init_opcode:
            raise IRCException(IRC_ERR_ILLEGAL_OPCODE, f'Invalid opcode: {self.header.opcode}')
        if self.header.length != len(self.payload) * LABEL_LENGTH + LABEL_LENGTH if self.identifier is not None else 0:
            raise IRCException(IRC_ERR_ILLEGAL_LENGTH, f'Invalid length: {self.header.length}')
        if native_labels:
            if self.identifier is not None and not validate_label(label_to_bytes(self.identifier)):
                raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid label: {self.identifier}')
            for label in self.payload:
                if not validate_label(label_to_bytes(label)):
                    raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid label: {label}')
        else:
            if self.identifier is not None and not validate_label(self.identifier):
                raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid label: {self.identifier}')
            for label in self.payload:
                if not validate_label(label):
                    raise IRCException(IRC_ERR_ILLEGAL_LABEL, f'Invalid label: {label}')
    
    def to_bytes(self):
        ''' validates fields
        '   returns a byte representation of the packet
        '''
        self.validate(native_labels=True)
        header_bytes = self.header.to_bytes()
        payload_bytes = b''
        for label in self.payload:
            payload_bytes += label_to_bytes(label)
        if self.identifier is not None:
            payload_bytes += label_to_bytes(self.identifier)  # Last 32 bytes are always identifier for listusers
        return header_bytes + payload_bytes

    def from_bytes(self, packet_bytes):
        ''' parses a byte representation of the packet and validates the results
        '   returns an IrcPacketListResp object (will this be an issue in consuming code? Expecting subclass?)
        '   intended to consume the output of socket.recv()
        '''
        # define field boundaries - may be a better way to do this, remove bytes as they're parsed?
        self.header = IrcHeader().from_bytes(packet_bytes[0:IrcHeader.header_length])
        # message body
        payload_bytes = packet_bytes[IrcHeader.header_length:]
        # parse bytes and validate
        userlist = [payload_bytes[i:i + LABEL_LENGTH] for i in range(0, len(payload_bytes), LABEL_LENGTH)]
        userlist = [lbl.decode('ascii') for lbl in userlist]
        self.payload = userlist
        self.identifier = None  # will be updated in subclass if needed
        self.validate(native_labels=True)
        self.payload = [strip_null_bytes(lbl) for lbl in self.payload]
        return self


class IrcPacketListRoomsResp(IrcPacketListResp):
    ''' has a header, holds a response to a list rooms request
    '   header: irc_header object
    '   payload: list of labels
    '   identifier: used for listusers, name of room to list users in
    '''

    def __init__(self, payload=None):
        super().__init__(IRC_LISTROOMS_RESP, payload)


class IrcPacketListUsersResp(IrcPacketListResp):
    ''' has a header, holds a response to a list users request
    '   header: irc_header object
    '   payload: list of labels
    '   identifier: used for listusers, name of room to list users in
    '''

    def __init__(self, payload=None, identifier=None):
        super().__init__(IRC_LISTUSERS_RESP, payload, identifier)

    def from_bytes(self, packet_bytes):
        superclass_bytes = super().from_bytes(packet_bytes)
        # identifier is always last 32 bytes of payload
        self.identifier = self.payload[-1]
        self.payload = self.payload[:-1]
        return self


# globally useful functions

def close_on_err(sock, err_code, err_msg=None):
    ''' closes a socket and prints an error message
    '   sock: socket to close
    '   err_code: error code to send
    '   err_msg: error message to print
    '   sel: selector to remove socket from (if closing from server)
    '''
    if err_msg is not None:
        print(err_msg)
    if sock is not None and sock.fileno() != -1:
        try:
            print(f'closing {sock.getpeername()} due to error {err_code}')
            sock.send(IrcPacketErr(err_code).to_bytes())
            sock.close()
        except (socket.socket.error, KeyError, ValueError, OSError):
            pass # socket already closed


def validate_string(string):
    ''' checks that all chars in a string are between ascii 0x20 and 0x7E (inclusive)
    '   or are 0x0A or 0x0D
    '   called only within packet classes, not client or server code
    '''
    bytestring = type(string) is bytes
    if not bytestring:
        try:
            string.encode('ascii')
        except UnicodeEncodeError:
            return False
    for i, char in enumerate(string):
        if not bytestring:
            if ord(char) < 0x20 or ord(char) > 0x7E and (ord(char) != 0x0A or ord(char) != 0x0D):
                if ord(char) == 0x00 and i != 0:
                    break  # null terminator is allowed, but only if there's at least 1 char prior
                return False
        elif (char < 0x20 or char > 0x7E) and (char != 0x0A and char != 0x0D):
            if char == 0x00 and i != 0:
                break
            return False
    return True


def validate_label(label):
    ''' checks if a label is a valid string & valid length
    '   called only within packet classes, not client or server code
    '   label: label to check
    '   returns: True if valid, False otherwise
    '''
    if len(label) > 32 or len(label) < 1:
        return False
    if len(label) < 32 and label.find('\0') == -1:
        return False
    if label[0] == ' ' or label[-1] == ' ':
        return False
    if not validate_string(label):
        return False
    return True


def validate_message(message):
    ''' checks if a msg body conforms to the rfc
    '   called only within packet classes, not client or server code
    '''
    if message[-1] != '\0':
        return False
    if message[:-1].find('\0') != -1:
        return False
    if not validate_string(message):
        return False
    if not len(message) <= MAX_MSG_LENGTH:
        return False
    return True


def label_to_bytes(label):
    ''' converts a label to 32 byte null-padded bstring
    '   label: label to convert
    '   returns: byte representation of label
    '''
    return label.encode('ascii').ljust(32, b'\x00')


def strip_null_bytes(string):
    ''' strips null bytes from a string '''
    if type(string) is bytes:
        return string.rstrip(b'\x00')
    else:
        return string.rstrip('\x00')
