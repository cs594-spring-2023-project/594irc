''' client.py ~ Amelia Miner, Sarvesh Biradar
'   Implements the client side of the chatroom as specified in RFC.pdf under /docs.
'   ...
'''

from conf import *

'''
client should
    take input from user,
    encode it as bytes using str.encode('ascii') or int.to_bytes('big'),
    construct a packet using a class from conf.py,
    and send it to the server
in addition to keepalives
'''