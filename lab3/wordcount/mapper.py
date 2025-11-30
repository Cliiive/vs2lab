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

context = zmq.Context()

# Socket to receive messages on (sentences from splitter)
# max 1
splitter = context.socket(zmq.PULL)
splitter.connect("tcp://"+ HOST +":" + str(int(const.SPLITTER_PORT)))
splitter.append(splitter)

# Create separate PUSH sockets for each reducer
# This allows us to control which reducer gets which word
# max 32
reducers = []
for i in range(const.NUM_REDUCERS):
    reducer = context.socket(zmq.PUSH)
    # Each reducer binds to REDUCER_PORT + i
    reducer.connect("tcp://"+ HOST +":" + str(int(const.REDUCER_PORT) + i))
    reducers.append(reducer)

# Process sentences forever
while True:


    # Receive sentence from splitter
    # sentence = splitters.recv_string()
    if sentence == const.DONE:
        # Propagate DONE signal to all reducers
        for reducer in reducers:
            reducer.send_string(const.DONE)
        break  # Exit the loop and end the mapper
    
    # Simple progress indicator
    sys.stdout.write('.')
    sys.stdout.flush()
    
    # Split sentence into words (remove punctuation and convert to lowercase)
    words = sentence.lower().replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
    
    # Send each word to the correct reducer using fixed schema (hash)
    # This ensures all instances of the same word go to the same reducer
    for word in words:
        # iterrate over WORDS_TO_COUNT to find the index of the word that matches the current word
        # if found then push to the reducer at index (index % NUM_REDUCERS)
        reducer_index = None
        for i in range(len(const.WORDS_TO_COUNT)):
            if word == const.WORDS_TO_COUNT[i]:
                reducer_index = const.NUM_REDUCERS + i;
                reducers[reducer_index].send_string(word)
                break