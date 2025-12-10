import pickle
import sys
import zmq
import threading
import logging

import const

logger = logging.getLogger("REDUCER")

class WordCountReducer(threading.Thread):
    def __init__(self, id, pull_socket):
        threading.Thread.__init__(self)
        self.id = id
        self.pull_socket = pull_socket
        self.word_counts = {}  
        self.done_count = 0

    def run(self):
        logger.info(f"{self.id} started")
        
        # Expect one DONE signal per mapper
        expected_done_signals = const.NUM_MAPPERS
        
        while True:
            msg = self.pull_socket.recv_string()
            if msg == const.DONE:
                self.done_count += 1
                logger.info(f"{self.id} received DONE signal ({self.done_count}/{expected_done_signals})")
                if self.done_count >= expected_done_signals:
                    logger.info(f"{self.id} received all DONE signals. Exiting.")
                    break
            else:
                logger.debug(f"{self.id} received '{msg}'")
                # Count the word
                if msg in self.word_counts:
                    self.word_counts[msg] += 1
                else:
                    self.word_counts[msg] = 1

def get_reducer_addresses(count):
    addresses = []
    for i in range(int(count)):
        addr = "tcp://" + const.HOST + ":" + str(int(const.REDUCER_PORT) + i)
        addresses.append(addr)
    return addresses

def configure_logging():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                        datefmt='%Y-%m-%d %H:%M:%S')

def main():
    configure_logging()
    # 1. Bind reducer sockets (one per reducer)
    context = zmq.Context()
    addresses = get_reducer_addresses(const.NUM_REDUCERS)
    reducers = []
    for i, addr in enumerate(addresses):
        pull_socket = context.socket(zmq.PULL)
        pull_socket.bind(addr)
        logger.info(f"Reducer-{i+1} Binding PULL at {addr}") 
        reducer = WordCountReducer(f"Reducer-{i+1}", pull_socket)
        reducers.append(reducer)
        reducer.start()
    
    # 2. Wait for all reducers to finish
    for reducer in reducers:
        reducer.join()

    logger.info("All reducers have finished processing.") 
    
    # 3. Collect and aggregate results
    total_counts = {}
    for reducer in reducers:
        logger.info(f"{reducer.id} word counts: {reducer.word_counts}")
        for word, count in reducer.word_counts.items():
            if word in total_counts:
                total_counts[word] += count
            else:
                total_counts[word] = count
    
    # 4. Print final results
    print("\nFinal results:")
    for word in const.WORDS_TO_COUNT:
        count = total_counts.get(word, 0)
        print(f"{word}: {count}")

if __name__ == "__main__":
    main()