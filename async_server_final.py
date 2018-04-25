import asyncio
import argparse
import json
import struct


USER_LIST = []
USER_LIST_OBJ = []
"""
Create dictionary username : ip get the ip address

"""
MESSAGES = []


class ChatServer(asyncio.Protocol):

    def __init__(self):
        self.buffer = b''
        self.data = b''
        self.length = 0
        self.username = ''

    def connection_made(self, transport):
        """
        Creates the connection
        :param transport:
        :return: Returns the accepted connection name and info
        """
        self.transport = transport
        self.address = transport.get_extra_info('peername')
        self.data = b''
        print('Accepted connection from {}'.format(self.address))

    def data_received(self, data):
        """
        Recieves the sent data which are in question delimiters
        :param data: string
        :return: writes back the answer
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
                MESSAGES.append(message)
                self.send_to_people(message)

        if self.buffer:
            self.data_received(self.buffer)
        self.buffer = b''
        self.data = b''
        self.length = 0

    def connection_lost(self, exc):
        """
        Connection lost handling
        :param exc:
        :return: Returns the closed socket
        """
        if exc:
            print('Client {} error: {}'.format(self.address, exc))
        elif self.data:
            print('Client {} sent {} but then closed'
                  .format(self.address, self.data))
        else:
            print('Client {} closed socket'.format(self.address))

        USER_LIST_OBJ.remove(self)
        if self.username in USER_LIST:
            USER_LIST.remove(self.username)
        print(self.username, " has just left.")


    def send_to_people(self, message):
        if message[1] == "ALL":
            for user in USER_LIST_OBJ:
                to_send = json.dumps({"MESSAGES": [message]}).encode('UTF-8')
                length = struct.pack('!L', len(to_send))
                to_send = length + to_send
                user.transport.write(to_send)
        else:
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
    args = parser.parse_args()
    address = (args.host, args.p)

    loop = asyncio.get_event_loop()
    coro = loop.create_server(ChatServer, *address)
    server = loop.run_until_complete(coro)
    print('Listening at {}'.format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
