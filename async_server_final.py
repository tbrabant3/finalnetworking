"""async_server_final.py

Author:              Tyler Brabant
Class:               CSI-235
Assignment:          Final Project
Date Assigned:       two weeks prior to end date
Due Date:            4/27/2018 11:59 PM SKIP DAY ADDED

Description:
Chat server that receives messages and other information through a protocol defined already.
it bounces messages back to users who send the information

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
import ssl


USER_LIST = []  # Usernames
USER_LIST_OBJ = []  # User objs
MESSAGES = []  # message touples in storage


class ChatServer(asyncio.Protocol):
    def __init__(self):
        """
           Creates member variables
           returns default member variable values
        """
        self.buffer = b''
        self.data = b''
        self.length = 0
        self.username = ''

    def connection_made(self, transport):
        """
        Sets up the connection

        returns the connection transport for the server object to use
        """
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.data = b''
        print('Accepted connection from {}'.format(self.address))

    def data_received(self, data):
        """
        Recieves the sent from the client prefaced with the length to check out

         returns to the client the right messages/ information according to what is sent
         all in json format**
        """
        self.data += data
        if self.length == 0:
            if self.data[:4]:
                self.length = (struct.unpack('!L', self.data[:4]))[0]

        if len(self.data[4:].decode('UTF-8')) >= self.length:
            json_message = json.loads(self.data[4:self.length + 4].decode('UTF-8'))
            self.buffer = self.data[self.length + 4:]
        else:
            return

        if 'USERNAME' in json_message and json_message.get('USERNAME') not in USER_LIST:
            USER_LIST.append(json_message.get("USERNAME"))
            self.username = json_message.get("USERNAME")
            USER_LIST_OBJ.append(self)

            user_accept = json.dumps({"USERNAME_ACCEPTED": True,
                                      "INFO": "WELCOME TO THE SERVER",
                                      "USER_LIST": USER_LIST,
                                      "MESSAGES": MESSAGES}).encode('UTF-8')

            length = struct.pack('!L', len(user_accept))
            user_accept = length + user_accept
            self.transport.write(user_accept)

            # message all the users
            for user in USER_LIST_OBJ:
                user_join = json.dumps({"USERS_JOINED": [self.username]}).encode("UTF-8")
                length = struct.pack('!L', len(user_join))
                user_join = length + user_join
                user.transport.write(user_join)
            print(self.username, " has just joined.")  #lets the server know
        elif 'USERNAME' in json_message and json_message.get('USERNAME') in USER_LIST:
            user_no = json.dumps({"USERNAME_ACCEPTED": False,
                       "Info": "Sorry, Username exists or there is an error."}).encode('UTF-8')
            length = struct.pack('!L', len(user_no))
            user_no = length + user_no
            self.transport.write(user_no)

        elif 'USERNAME' in json_message:
            user_no = json.dumps({"USERNAME_ACCEPTED": False,
                       "Info": "Sorry, Username exists or there is an error."}).encode('UTF-8')
            length = struct.pack('!L', len(user_no))
            user_no = length + user_no
            self.transport.write(user_no)

        if json_message.get("MESSAGES"):
            messages = json_message.get("MESSAGES")
            for message in messages:
                # If the user is in the src
                if self.username == message[0] and message[1] == 'ALL' or message[1] in USER_LIST:
                    MESSAGES.append(message)
                    self.send_to_people(message)
                else:
                    error_code = json.dumps({"ERROR": "error in message format"}).encode("UTF-8")
                    length = struct.pack('!L', len(error_code))
                    error_code = length + error_code
                    self.transport.write(error_code)

        if self.buffer:
            self.data_received(self.buffer)
        self.buffer = b''
        self.data = b''
        self.length = 0

    def connection_lost(self, exc):
        """
        Connection lost handling
        Returns the connection lost and also sends to the users that the user left
        """
        if exc:
            print('Client {} error: {}'.format(self.address, exc))
        elif self.data:
            print('Client {} sent {} but then closed'
                  .format(self.address, self.data))
        else:
            print('Client {} closed socket'.format(self.address))

        # removes the user from the list and its obj self from the other list.
        USER_LIST_OBJ.remove(self)
        if self.username in USER_LIST:
            USER_LIST.remove(self.username)
        print(self.username, " has just left.")  # Server message just so it will know
        for user in USER_LIST_OBJ:
            user_left = json.dumps({"USERS_LEFT": [self.username]}).encode("UTF-8")
            length = struct.pack('!L', len(user_left))
            user_left = length + user_left
            user.transport.write(user_left)

    def send_to_people(self, message):
        """
        sends the message to all the users.
        message is a message in the correct format that is distributed to all users

        returns the correct message to all the right users.
        """
        if message[1] == "ALL":
            # sends to all
            for user in USER_LIST_OBJ:
                to_send = json.dumps({"MESSAGES": [message]}).encode('UTF-8')
                length = struct.pack('!L', len(to_send))
                to_send = length + to_send
                user.transport.write(to_send)
        else:
            # Sends to individuals
            for user in USER_LIST_OBJ:
                if message[1] == user.username:
                    to_send = json.dumps({"MESSAGES": [message]}).encode('UTF-8')
                    length = struct.pack('!L', len(to_send))
                    to_send = length + to_send
                    user.transport.write(to_send)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Example server')
    parser.add_argument('host', help='IP or hostname')
    parser.add_argument('-p', metavar='port', type=int, default=1060,
                        help='TCP port (default 1060)')
    parser.add_argument('pem', help='PEM file only')
    args = parser.parse_args()
    address = (args.host, args.p)

    # adds security to the server and the file must be added to opperate
    purpose = ssl.Purpose.CLIENT_AUTH
    context = ssl.create_default_context(purpose)
    context.load_cert_chain(args.pem)

    loop = asyncio.get_event_loop()
    coro = loop.create_server(ChatServer, *address, ssl=context)
    server = loop.run_until_complete(coro)
    print('Listening at {}'.format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
