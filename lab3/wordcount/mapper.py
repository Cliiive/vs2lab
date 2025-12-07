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
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MAPPER")

class WordCounterMapper(threading.Thread):
    def __init__(self, id, context):
        threading.Thread.__init__(self)
        self.id = id
        self.context = context
        self.counter = 0
        
    def run(self):
        # Each mapper thread creates its own PULL socket
        splitter_address = "tcp://" + const.HOST + ":" + const.SPLITTER_PORT
        splitter_socket = self.context.socket(zmq.PULL)
        splitter_socket.connect(splitter_address)
        
        # Each mapper thread creates its own PUSH sockets to reducers
        reducer_sockets = []
        for i in range(const.NUM_REDUCERS):
            reducer_address = "tcp://" + const.HOST + ":" + str(int(const.REDUCER_PORT) + i)
            reducer_socket = self.context.socket(zmq.PUSH)
            reducer_socket.connect(reducer_address)
            reducer_sockets.append(reducer_socket)
        
        logger.info(f"{self.id} started and connected")  # important lifecycle
        
        while True:
            sentence = splitter_socket.recv_string()
            if sentence == const.DONE:
                logger.info(f"{self.id} received DONE signal. Forwarding to reducers.")  # important lifecycle
                # Send DONE to all reducers
                for r in reducer_sockets:
                    r.send_string(const.DONE)
                break
            
            logger.debug(f"{self.id} received sentence: {sentence}")  # routine flow

            # Normalize: lowercase and remove punctuation (keep only letters and spaces)
            sentence_normalized = re.sub(r'[^a-z\s]', ' ', sentence.lower())
            words = sentence_normalized.split()

            # Send each tracked word to the appropriate reducer
            for word in words:
                if word in const.WORDS_TO_COUNT:
                    # Use modulo to distribute words across reducers
                    reducer_index = const.WORDS_TO_COUNT.index(word) % const.NUM_REDUCERS
                    reducer_sockets[reducer_index].send_string(word)
                    self.counter += 1
                    logger.debug(f"{self.id} sent word '{word}' to reducer {reducer_index}")  # routine flow
        
        logger.info(f"{self.id} processed {self.counter} words total")
        
        # Close sockets
        splitter_socket.close()
        for r in reducer_sockets:
            r.close()

def main():
    # Create shared context
    context = zmq.Context()
    
    logger.info("Starting mapper threads...")  # important lifecycle

    # Start mapper threads - each will create its own sockets
    mappers = []
    for i in range(const.NUM_MAPPERS):
        mapper = WordCounterMapper(f"Mapper-{i+1}", context)
        mappers.append(mapper)
        mapper.start()

    # Wait for all mappers to finish
    for mapper in mappers:
        mapper.join()

    logger.info("All mappers have finished processing.")  # important lifecycle
    
    # Terminate context
    context.term()

if __name__ == "__main__":
    main()