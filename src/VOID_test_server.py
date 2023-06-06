''' basic tests for the server '''
from conf import *
import pytest
import asyncio
import socket
import server

# poke the server with a hello
@pytest.mark.asyncio
async def test_valid_hello():
    # start server with asyncio
    server_task = asyncio.create_task(server.main())
    hello_packet = IrcPacketHello('Sarvesh')
    hello_bytes = hello_packet.to_bytes()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect(('localhost', IRC_SERVER_PORT))
        sock.sendall(hello_bytes)
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass