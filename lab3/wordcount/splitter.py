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

    line_count = 0
    for line in contents:
        line = line.strip()  # Remove whitespace/newlines
        if line:  # Only send non-empty lines
            logger.debug(f"Sending line: {line}")  # routine flow
            sender.send_string(line)  # Send as string, not bytes
            line_count += 1

    logger.info(f"Sent {line_count} lines")

    # Send one DONE per mapper to allow all mapper threads to terminate
    logger.info(f"Sending {const.NUM_MAPPERS} DONE signals")
    for i in range(const.NUM_MAPPERS):
        logger.debug(f"Sending DONE signal {i+1}/{const.NUM_MAPPERS}")  # routine flow
        sender.send_string(const.DONE)

    time.sleep(1)
    sender.close()
    context.term()