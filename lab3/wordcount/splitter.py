import const
import time
import zmq

def splitter():
    context = zmq.Context()
    sender = context.socket(zmq.PUSH)  # create a push socket

    address = "tcp://" + const.HOST + ":" + const.SPLITTER_PORT  # how and where to communicate
    sender.bind(address)  # bind socket to the address

    print(f"[SPLITTER] Running at {address}")

    time.sleep(1) # wait to allow all clients to connect

    with open('text.txt', 'r') as file:
        contents = file.readlines() # read contents of a text file

    for line in contents:
        sender.send(line.encode())

    time.sleep(1)