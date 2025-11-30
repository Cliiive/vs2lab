import pickle
import sys
import zmq
import threading
import logging

import const

class WordCountReducer(threading.Thread):
    def __init__(self, id, word, pull_socket):
        threading.Thread.__init__(self)
        self.id = id
        self.word = word
        self.pull_socket = pull_socket
        self.counter = 0

    def run(self):
        logging.info(f"{self.id} started counting {self.word}")
        while True:
            msg = self.pull_socket.recv_string()
            if msg == const.DONE:
                logging.info(f"{self.id} received all DONE signals. Exiting.")
                break

            logging.debug(f"{self.id}: received '{msg}'")
            if msg == self.word:
                self.counter += 1

def get_reducer_addresses(count):
    addresses = []
    for i in range(int(count)):
        addr = "tcp://" + const.HOST + ":" + str(int(const.REDUCER_PORT) + i)
        addresses.append(addr)
    return addresses

def configure_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
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
        logging.info(f"Binding reducer {i+1} PULL at {addr}")
        reducer = WordCountReducer(f"Reducer-{i+1}", const.WORDS_TO_COUNT[i], pull_socket)
        reducers.append(reducer)
        reducer.start()
    
    # 2. Wait for all reducers to finish
    for reducer in reducers:
        reducer.join()

    logging.info("All reducers have finished processing.")
    logging.info("Results collected:")
    
    # 3. Print results
    for reducer in reducers:
        logging.info(f"{reducer.id} processed {reducer.counter} items.")

    # Print final result for each word
    print("Final results:")
    for reducer in reducers:
        print(f"{reducer.word}: {reducer.counter}")

if __name__ == "__main__":
    main()
