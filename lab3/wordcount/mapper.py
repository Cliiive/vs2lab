#!/usr/bin/env python3
"""
Mapper for MapReduce Wordcount
- Connects PULL socket to receive sentences from splitter(s)
- Splits sentences into words
- Uses fixed schema to assign each word to a specific reducer
- Connects separate PUSH sockets to each reducer
"""

import sys
import zmq
import const
import threading
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MAPPER")

class WordCounterMapper(threading.Thread):
    def __init__(self, id, splitter_socket, reducer_sockets):
        threading.Thread.__init__(self)
        self.id = id
        self.splitter_socket = splitter_socket
        self.reducer_sockets = reducer_sockets
        self.counter = 0
        
    def run(self):
        logger.info(f"{self.id} started")  # important lifecycle
        while True:
            sentence = self.splitter_socket.recv_string()
            if sentence == const.DONE:
                logger.info(f"{self.id} received DONE signal. Exiting.")  # important lifecycle
                for r in self.reducer_sockets:
                    r.send_string(const.DONE)
                break
            logger.debug(f"{self.id} received sentence: {sentence}")  # routine flow

            # Normalize and split sentence
            words = sentence.lower().replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()

            # Send each tracked word to the appropriate reducer
            for word in words:
                if word in const.WORDS_TO_COUNT:
                    reducer_index = const.WORDS_TO_COUNT.index(word) % const.NUM_REDUCERS
                    self.reducer_sockets[reducer_index].send_string(word)
                    logger.debug(f"{self.id} sent word '{word}' to reducer {reducer_index}")  # routine flow

def main():
    # 1. Connect to splitter socket
    context = zmq.Context()
    splitter_address = "tcp://" + const.HOST + ":" + const.SPLITTER_PORT
    splitter_socket = context.socket(zmq.PULL)
    splitter_socket.connect(splitter_address)
    logger.info(f"Connected to splitter at {splitter_address}")  # important lifecycle

    # 2. Connect to reducer sockets
    reducer_sockets = []
    for i in range(const.NUM_REDUCERS):
        reducer_address = "tcp://" + const.HOST + ":" + str(int(const.REDUCER_PORT) + i)
        reducer_socket = context.socket(zmq.PUSH)
        reducer_socket.connect(reducer_address)
        reducer_sockets.append(reducer_socket)
        logger.info(f"Connected to reducer {i} at {reducer_address}")  # important lifecycle

    # 3. Start mapper threads
    mappers = []
    for i in range(const.NUM_MAPPERS):
        mapper = WordCounterMapper(f"Mapper-{i+1}", splitter_socket, reducer_sockets)
        mappers.append(mapper)
        mapper.start()

    # 4. Wait for all mappers to finish
    for mapper in mappers:
        mapper.join()

    logger.info("All mappers have finished processing.")  # important lifecycle

if __name__ == "__main__":
    main()


