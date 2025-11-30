import sys
import zmq
import threading
import logging

import const

class WordCountReducer(threading.Thread):
    def __init__(self, id, message, subscriber):
        threading.Thread.__init__(self)
        self.id = id
        self.message = message
        self.subscriber = subscriber
        self.counter = 0
        
    def run(self):
        while True:
            self.subscriber.setsockopt(zmq.SUBSCRIBE, self.message)  # subscribe to messages
            logging.info(f"{self.id} started counting {self.message}")
            msg = self.subscriber.recv()  # receive a message
            logging.info(f"{self.id} received message: {msg}")
            self.counter += 1

def configure_logging():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

def main():
    configure_logging()
    
    address = "tcp://127.0.0.1:" + const.REDUCER_PORT
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(address)

    # Create 3 reducer threads
    reducers = []
    for i in range(3):
        reducer_id = f"Reducer-{i+1}"
        reducer = WordCountReducer(f"Reducer-{i+1}", "TESTMSG", subscriber)
        reducers.append(reducer)
        reducer.start()

    logging.info("All reducers started.")
        
    for reducer in reducers:
        reducer.join()

    logging.info("All reducers have finished processing.")
    logging.info("Results collected:")
    
    for reducer in reducers:
        logging.info(f"{reducer.id} processed {reducer.counter} items.")

if __name__ == "__main__":
    main()
