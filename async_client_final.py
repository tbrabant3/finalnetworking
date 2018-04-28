"""async_client

Champlain College CSI-235, Spring 2018
Prof. Josh Auerbach

Bare bones example of asynchronously receiving 
data from server and user input from stdin
"""
"""async_client_final.py

Author:              Tyler Brabant
Class:               CSI-235
Assignment:          Final Project
Date Assigned:       two weeks prior to end date
Due Date:            4/27/2018 11:59 PM SKIP DAY ADDED

Description:
Chat client that sends messages and other information through a protcol defined already.

This code has been adapted from that provided by Prof. Joshua Auerbach: see above

Champlain College CSI-235, Spring 2018
The following code was written by Tyler Brabant

Special thank you to TJ Leach who helped with the server side and the connection status section
I did not directly copy his code but he verbally walked me through the concepts of it.
"""
import asyncio
import argparse
import json
import struct
import time
import ssl


class ChatClient(asyncio.Protocol):
    def __init__(self):
        """
            Creates member variables
            returns default member variable values
        """
        self.buffer = b''
        self.data = b''
        self.length = 0
        self.username = ''
        self.status = 2
        # not connected == 0
        # awaiting == 2
        # Connected == 1
        # user provided == 3
        #Source TJ

    def data_received(self, data):
        """
        Receives data from the server and parses it displaying the correct information

        returns the correct information on the screen and shows messages in the order they come
        all in json format**
        """
        # contiuily grabs data
        self.data += data
        if self.length == 0:
            if self.data[:4]:
                self.length = (struct.unpack('!L', self.data[:4]))[0]

        # checks the length to make sure it is all there
        if len(self.data[4:].decode('UTF-8')) >= self.length:
            incoming_data = json.loads(self.data[4:self.length + 4].decode('UTF-8'))
            self.buffer = self.data[self.length + 4:]
        else:
            return

        # Section that checks the json and responds accordingly to the information

        if incoming_data.get("MESSAGES"):
            messages = incoming_data.get("MESSAGES")
            for message in messages:
                print(message[2],
                      message[0], ": ",
                      message[3])

        if incoming_data.get("USERNAME_ACCEPTED") == True:
            print("Username Accepted.")
            if incoming_data.get("INFO"):
                print(incoming_data.get("INFO"))
            self.status = 1

        elif incoming_data.get("USERNAME_ACCEPTED") == False:
            print("Username Error.")
            print(incoming_data)
            if incoming_data.get("INFO"):
                print(incoming_data.get("INFO"))
            self.status = 2

        if incoming_data.get("USER_LIST"):
            user_list = incoming_data.get("USER_LIST")
            print("Users on server: ", [user for user in user_list])

        if incoming_data.get("USERS_JOINED"):
            print("User ", incoming_data.get("USERS_JOINED")[0], " has joined.")

        if incoming_data.get("USERS_LEFT"):
            print("User ", incoming_data.get("USERS_LEFT")[0], " has left.")

        if incoming_data.get("ERROR"):
            print("ERROR: ", incoming_data.get("ERROR"))

        # if anything in the buffer keep going
        if self.buffer:
            self.data_received(self.buffer)
        self.buffer = b''
        self.data = b''
        self.length = 0

    def connection_made(self, transport):
        """
        Sets up the connection

        returns the connection transport for the client to use
        """
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.data = b''
        print('Accepted connection from {}'.format(self.address))

    def write_out(self, data):
        """
        sends out the data with the correct length

        returns the sent data to the server
        """
        length = struct.pack('!L', len(data))
        data = length + data
        self.transport.write(data)


@asyncio.coroutine
def handle_user_input(loop, client):
    """reads from stdin in separate thread
    
    if user inputs 'quit' stops the event loop
    otherwise sends the username and then the messages loop and quits when user wants
    """
    while client.status != 1:
        if client.status == 2:
            print("Please enter your username or quit to quit: ")
            client.username = yield from loop.run_in_executor(None, input, "> ")
            if client.username == "quit":
                loop.stop()
                return
            client.status = 3
            to_send = {"USERNAME": client.username}
            client.write_out(json.dumps(to_send).encode('ascii'))
            print("To send a private message, write the '@' sign first followed by the username"
                  "and a space to start the message.")
        else:
            yield

    while True:
        # sets up the 4 needed aspects of the message
        dest = 'ALL'
        src = client.username
        message = yield from loop.run_in_executor(None, input, "> ")
        timestamp = int(time.time())

        if message == "quit":  # stops the loop
            loop.stop()
            return

        if message != "" and message != "@":
            if message[0] == '@':
                user_to_send = message.split(" ", 1)
                dest = user_to_send[0][1:]
                final_message = {"MESSAGES": [(src, dest, timestamp, user_to_send[1])]}
            else:
                final_message = {"MESSAGES": [(src, dest, timestamp, message)]}
            client.write_out(json.dumps(final_message).encode('UTF-8'))  # Sends the message
        else:
            print("Please enter a message or follow '@' with a username")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example client')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=7000,
                        help='TCP port (default 7000)')
    parser.add_argument('-ca', help='CA file only', nargs='?', default=None)  # grabs the ca file if not specified
                                                                              # then it is blank and can connect to
                                                                              # class server
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    
    # we only need one client instance
    client = ChatClient()
    
    # the lambda client serves as a factory that just returns
    # the client instance we just created
    # ssl aspects are also here for the security
    purpose = ssl.Purpose.SERVER_AUTH
    context = ssl.create_default_context(purpose, cafile=args.ca)
    coro = loop.create_connection(lambda: client, args.host, args.p, ssl=context)
    
    loop.run_until_complete(coro)

    # Start a task which reads from standard input
    asyncio.async(handle_user_input(loop, client))

    try:
        loop.run_forever()
    finally:
        loop.close()   
