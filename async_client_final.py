"""async_client

Champlain College CSI-235, Spring 2018
Prof. Josh Auerbach

Bare bones example of asynchronously receiving 
data from server and user input from stdin
"""

import asyncio
import argparse
import json
import struct
import time

class ChatClient(asyncio.Protocol):
    def __init__(self):
        self.buffer = b''
        self.data = b''
        self.length = 0
        self.username = ''
        self.status = 2
        # not connected == 0
        # awaiting == 2
        #  Connected == 1
        # user provided == 3
        #Source TJ

    def data_received(self, data):
        # print(data)
        self.data += data
        if self.length == 0:
            if self.data[:4]:
                self.length = (struct.unpack('!L', self.data[:4]))[0]

        # print(self.length, len(self.data[4:].decode('UTF-8')))

        if len(self.data[4:].decode('UTF-8')) >= self.length:
            incoming_data = json.loads(self.data[4:self.length + 4].decode('UTF-8'))
            # print(incoming_data)
            self.buffer = self.data[self.length + 4:]
            # print("Buffer: ", self.buffer)
        else:
            return

        if incoming_data.get("USERNAME_ACCEPTED") == True:
            print("Username Accepted.")
            if incoming_data.get("INFO"):
                print(incoming_data.get("INFO"))
            self.status = 1

        elif incoming_data.get("USERNAME_ACCEPTED") == False:
            print("Username Error.")
            if incoming_data.get("INFO"):
                print(incoming_data.get("INFO"))
            self.status = 2

        if incoming_data.get("USER_LIST"):
            user_list = incoming_data.get("USER_LIST")
            print("Users on server: ", [user for user in user_list])

        if incoming_data.get("MESSAGES"):
            messages = incoming_data.get("MESSAGES")
            for message in messages:
                print(message[2],
                      message[0], ": ",
                      message[3])
        if incoming_data.get("USERS_JOINED"):
            print("User ", incoming_data.get("USERS_JOINED")[0], " has joined.")

        if incoming_data.get("USERS_LEFT"):
            print("User ", incoming_data.get("USERS_LEFT")[0], " has left.")

        print(incoming_data)
        # print("received: ", incoming_data)

        if self.buffer:
            self.data_received(self.buffer)
        self.buffer = b''
        self.data = b''
        self.length = 0

    def connection_made(self, transport):
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.data = b''
        print('Accepted connection from {}'.format(self.address))

    def write_out(self, data):
        length = struct.pack('!L', len(data))
        data = length + data
        self.transport.write(data)
        # print(data)
"""
    def send_username(self, uname_good):
        if not uname_good:
            self.username = input("Please enter your username: ")
            to_send = {"USERNAME": self.username}
            client.write_out(json.dumps(to_send).encode('ascii'))
            print("To send a private message, write the '@' sign first followed by the username"
                  "and a space to start the message.")
"""
@asyncio.coroutine
def handle_user_input(loop, client):
    """reads from stdin in separate thread
    
    if user inputs 'quit' stops the event loop
    otherwise just echos user input
    """
    while client.status != 1:
        if client.status == 2:
            print("Please enter your username: ")
            client.username = yield from loop.run_in_executor(None, input, "> ")
            client.status = 3
            to_send = {"USERNAME": client.username}
            client.write_out(json.dumps(to_send).encode('ascii'))
            print("To send a private message, write the '@' sign first followed by the username"
                  "and a space to start the message.")
        else:
            yield

    while True:
        dest = 'ALL'
        src = client.username

        message = yield from loop.run_in_executor(None, input, "> ")
        timestamp = int(time.time())
        if message == "quit":
            loop.stop()
            return

        if message[0] == '@':
            user_to_send = message.split(" ", 1)
            dest = user_to_send[0][1:]

        final_message = {"MESSAGES": [(src, dest, timestamp, message)]}
        # print(json.dumps(final_message).encode('UTF-8'))
        client.write_out(json.dumps(final_message).encode('UTF-8'))  # Sends the message


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example client')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=7000,
                        help='TCP port (default 7000)')

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    
    # we only need one client instance
    client = ChatClient()
    
    # the lambda client serves as a factory that just returns
    # the client instance we just created
    coro = loop.create_connection(lambda: client, args.host, args.p)
    
    loop.run_until_complete(coro)

    # Start a task which reads from standard input
    asyncio.async(handle_user_input(loop, client))

    try:
        loop.run_forever()
    finally:
        loop.close()   
