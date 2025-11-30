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
            msg: str = pickle.loads(self.pull_socket.recv())
            if msg[1] == const.DONE:
                logging.info(f"{self.id} received DONE signal. Exiting.")
                break
            logging.info("{}: received {} from {}".format(self.id, msg[1], msg[0]))
            self.counter += 1

def get_mapper_addresses(count):
    addresses = []
    for i in range(int(count)):
        addr = "tcp://" + const.HOST + ":" + str(int(const.MAPPER_PORT) + i)
        addresses.append(addr)
    return addresses

def configure_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

def main():
    configure_logging()
    
    "1. Connect to all mapper sockets"
    addresses = get_mapper_addresses(const.NUM_MAPPERS)
    context = zmq.Context()
    pull_socket = context.socket(zmq.PULL)  # create a pull socket
    for addr in addresses:
        pull_socket.connect(addr)  # connect to each mapper address

    "2. Start reducers for each word to count"
    reducers = []
    for i in range(len(const.WORDS_TO_COUNT)):
        reducer: WordCountReducer = WordCountReducer(f"Reducer-{i+1}", const.WORDS_TO_COUNT[i], pull_socket)
        reducers.append(reducer)
        reducer.start()
    
    "3. Wait for all reducers to finish"
    for reducer in reducers:
        reducer.join()

    logging.info("All reducers have finished processing.")
    logging.info("Results collected:")
    
    "4. Print results"
    for reducer in reducers:
        logging.info(f"{reducer.id} processed {reducer.counter} items.")

if __name__ == "__main__":
    main()
