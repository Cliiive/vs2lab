"""
Client and server using classes
"""

import logging
import socket

import const_cs
from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)  # init loging channels for the lab

# pylint: disable=logging-not-lazy, line-too-long

class Server:

    #  The server.

    # Protocol (text-based):
    #   - "GET name"    -> server returns number or "NOTFOUND"
    #   - "GETALL"      -> server returns all entries as lines "name:number"
    #   - anything else  -> echo (original behaviour) -> returns data + '*'

    _logger = logging.getLogger("vs2lab.lab1.clientserver.Server")
    _serving = True

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # prevents errors due to "addresses in use"
        self.sock.bind((const_cs.HOST, const_cs.PORT))
        self.sock.settimeout(3)  # time out in order not to block forever
        self._logger.info("Server bound to socket " + str(self.sock))
        self.data_store =  {
        "Anna Mueller": "+49 151 2345678",
        "Ben Schneider": "+49 176 9876543",
        "Clara Fischer": "+49 160 3456789",
        "David Weber": "+49 157 5678901",
        "Ella Hoffmann": "+49 152 6789012",
        "Felix Wagner": "+49 171 7890123",
        "Greta Becker": "+49 173 8901234",
        "Hannes Schaefer": "+49 175 9012345",
        "Isabel Koch": "+49 178 1234567",
        "Jonas Bauer": "+49 179 2345678",
        "Klara Richter": "+49 170 3456789",
        "Leon Vogel": "+49 162 4567890",
        "Marie Winkler": "+49 163 5678901",
        "Nico Peters": "+49 174 6789012",
        "Olivia Klein": "+49 155 7890123",
        "Paul Neumann": "+49 177 8901234",
        "Rosa Lehmann": "+49 159 9012345",
        "Sophia Keller": "+49 172 1234567",
        "Tim Braun": "+49 158 2345678",
        "Viktor Schroeder": "+49 156 3456789"
        }

    def serve(self):
        """ Serve echo """
        self.sock.listen(1)
        while self._serving:  # as long as _serving (checked after connections or socket timeouts)
            try:
                # pylint: disable=unused-variable
                (connection, address) = self.sock.accept()  # returns new socket and address of client
                while True:  # forever
                    self._logger.info("Server waiting for data...")
                    data = connection.recv(1024)  # receive data from client
                    if not data:
                        break  # stop if client stopped
                    # connection.send(data + "*".encode('ascii'))  # return sent data plus an "*"
                    self._logger.info("Server received data: " + str(data))
                    msg = data.decode('ascii')
                    if msg.startswith("GETALL"):
                        self._logger.info("Server processing GETALL request")
                        response = "\n".join(f"{name}:{number}" for name, number in self.data_store.items())
                        connection.send(response.encode('ascii'))
                    elif msg.startswith("GET "):
                        self._logger.info("Server processing GET request")
                        name = msg[4:]
                        self._logger.info(f"Server looking up name: {name}")
                        response = self.data_store.get(name, "NOTFOUND")
                        connection.send(response.encode('ascii'))
                connection.close()  # close the connection
            except socket.timeout:
                pass  # ignore timeouts
        self.sock.close()
        self._logger.info("Server down.")


class Client:
    """ The client """
    logger = logging.getLogger("vs2lab.a1_layers.clientserver.Client")

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((const_cs.HOST, const_cs.PORT))
        self.logger.info("Client connected to socket " + str(self.sock))

    def call(self, msg_in="Hello, world"):
        """ Call server """
        self.sock.send(msg_in.encode('ascii'))  # send encoded string as data
        data = self.sock.recv(1024)  # receive the response
        msg_out = data.decode('ascii')
        print(msg_out)  # print the result
        self.sock.close()  # close the connection
        self.logger.info("Client down.")
        return msg_out

    def get(self, name: str) -> str:
        """ Get entry from server """
        self.logger.info(f"Client sending GET request for name: {name}")
        self.sock.send(f"GET {name}".encode('ascii'))
        self.logger.info(f"Client sent GET request for name: {name}")
        data = self.sock.recv(1024)
        self.logger.info(f"Client received data: {data}")
        return data.decode('ascii')
    
    def get_all(self) -> str:
        """ Get all entries from server """
        self.logger.info("Client sending GETALL request")
        self.sock.send("GETALL".encode('ascii'))
        self.logger.info("Client sent GETALL request")
        data = self.sock.recv(4096)
        self.logger.info(f"Client received data: {data}")
        return data.decode('ascii')
    
    def close(self):
        """ Close socket """
        self.sock.close()
