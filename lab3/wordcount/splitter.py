import const
import time
import zmq
import logging

def splitter():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)  # create a push socket

    address = "tcp://" + const.HOST + ":" + const.SPLITTER_PORT  # how and where to communicate
    sender.bind(address)  # bind socket to the address

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    logging.info(f"[SPLITTER] Running at {address}")  # important lifecycle

    time.sleep(1) # wait to allow all clients to connect

    with open('text.txt', 'r') as file:
        contents = file.readlines() # read contents of a text file

    for line in contents:
        logging.debug("[SPLITTER] sending line")  # routine flow
        sender.send(line.encode())

    # Send one DONE per mapper to allow all mapper threads to terminate
    for _ in range(const.NUM_MAPPERS):
        logging.debug("[SPLITTER] sending DONE")  # routine flow
        sender.send_string(const.DONE)

    time.sleep(1)