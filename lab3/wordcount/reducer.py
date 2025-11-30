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
            work = pickle.loads(self.pull_socket.recv())  # receive work from a source
            logging.info("{} received {} from {}".format(self.id, work[1], work[0]))
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
    addresses = get_mapper_addresses(const.NUM_MAPPERS)
    configure_logging()
    
    context = zmq.Context()
    pull_socket = context.socket(zmq.PULL)  # create a pull socket

    for addr in addresses:
        pull_socket.connect(addr)  # connect to each mapper address

    # Create 3 reducer threads
    reducers = []
    for i in range(len(const.WORDS_TO_COUNT)):
        reducer: WordCountReducer = WordCountReducer(f"Reducer-{i+1}", const.WORDS_TO_COUNT[i], pull_socket)
        reducers.append(reducer)
        reducer.start()
        
    for reducer in reducers:
        reducer.join()

    logging.info("All reducers have finished processing.")
    logging.info("Results collected:")
    
    for reducer in reducers:
        logging.info(f"{reducer.id} processed {reducer.counter} items.")

if __name__ == "__main__":
    main()
