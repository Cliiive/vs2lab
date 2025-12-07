import const
import time
import zmq
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SPLITTER")

def splitter():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)  # create a push socket

    address = "tcp://" + const.HOST + ":" + const.SPLITTER_PORT  # how and where to communicate
    sender.bind(address)  # bind socket to the address

    logger.info(f"Running at {address}")

    time.sleep(1) # wait to allow all clients to connect

    with open('text.txt', 'r') as file:
        contents = file.readlines() # read contents of a text file

    for line in contents:
        logging.debug("[SPLITTER] sending line")  # routine flow
        sender.send(line.encode())
        logger.debug(f"Sent line: {line.strip()}")

    # Send one DONE per mapper to allow all mapper threads to terminate
    logger.info("Sending DONE")
    for _ in range(const.NUM_MAPPERS):
        logging.debug("[SPLITTER] sending DONE")  # routine flow
        sender.send_string(const.DONE)

    time.sleep(1)