''' server.py ~ Amelia Miner, Sarvesh Biradar
'   Implements the server side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

from conf import *

'''
server should
    receive packet from client,
    decode it as bytes using str.decode('ascii') or int.from_bytes('big'),
    perform some actions based on the opcode,
    and respond to the client
in addition to keepalives
'''