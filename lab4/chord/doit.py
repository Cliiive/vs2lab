""" 
Chord Application
- defines a DummyChordClient implementation
- sets up a ring of chord_node instances
- Starts up a DummyChordClient
- nodes and client run in separate processes
- multiprocessing should work on unix and windows
"""

import logging
import sys
import multiprocessing as mp
import random

import chordnode as chord_node
import constChord
from context import lab_channel, lab_logging

lab_logging.setup(stream_level=logging.INFO)


class DummyChordClient:
    """A chord client that performs recursive name resolution"""

    def __init__(self, channel):
        self.channel = channel
        self.node_id = channel.join('client')
        self.logger = logging.getLogger("vs2lab.lab4.doit.DummyChordClient")

    def enter(self):
        self.channel.bind(self.node_id)

    def run(self):
        # Get all nodes from the ring
        nodes = {i.decode() for i in list(self.channel.channel.smembers('node'))}
        
        if not nodes:
            print("[CLIENT] No nodes available in the ring")
            return
        
        nodes_list = sorted([int(n) for n in nodes])
        
        # Perform multiple lookups to demonstrate recursive resolution
        for lookup_count in range(5):
            # Pick a random key in the valid range
            key = random.randint(0, self.channel.MAXPROC - 1)
            
            # Pick a random node to start the lookup
            start_node = random.choice(nodes_list)
            
            self.logger.info(f"[CLIENT] LOOKUP {key:04n} starting from node {start_node:04n}")
            print(f"[CLIENT] LOOKUP {key:04n} starting from node {start_node:04n}")
            
            # Send LOOKUP request to starting node
            self.channel.send_to([str(start_node)], (constChord.LOOKUP_REQ, key))
            
            # Wait for the result
            message = self.channel.receive_from_any()
            sender = int(message[0])
            response = message[1]
            
            if response[0] == constChord.LOOKUP_REP:
                responsible_node = response[1]
                self.logger.info(f"[CLIENT] Key {key:04n} is handled by node {responsible_node:04n}")
                print(f"[CLIENT] Key {key:04n} is handled by node {responsible_node:04n}")
            else:
                print(f"[CLIENT] Unexpected response: {response}")
        
        # Send STOP signal to all nodes
        self.logger.info("[CLIENT] Sending STOP signal to all nodes")
        self.channel.send_to(nodes, constChord.STOP)


def create_and_run(num_bits, node_class, enter_bar, run_bar):
    """
    Create and run a node (server or client role)
    :param num_bits: address range of the channel
    :param node_class: class of node
    :param enter_bar: barrier syncing channel population 
    :param run_bar: barrier syncing node creation
    """
    chan = lab_channel.Channel(n_bits=num_bits)
    node = node_class(chan)
    enter_bar.wait()  # wait for all nodes to join the channel
    node.enter()  # do what is needed to enter the ring
    run_bar.wait()  # wait for all nodes to finish entering
    node.run()  # start operating the node


if __name__ == "__main__":  # if script is started from command line
    m = 6  # Number of bits for linear names
    n = 8  # Number of nodes in the chord ring

    # Check for command line parameters m, n.
    if len(sys.argv) > 2:
        m = int(sys.argv[1])
        n = int(sys.argv[2])

    # Flush communication channel
    chan = lab_channel.Channel()
    chan.channel.flushall()

    # we need to spawn processes for support of windows
    mp.set_start_method('spawn')

    # create barriers to synchronize bootstrapping
    bar1 = mp.Barrier(n+1)  # Wait for channel population to complete
    bar2 = mp.Barrier(n+1)  # Wait for ring construction to complete

    # start n chord nodes in separate processes
    children = []
    for i in range(n):
        nodeproc = mp.Process(
            target=create_and_run,
            name="ChordNode-" + str(i),
            args=(m, chord_node.ChordNode, bar1, bar2))
        children.append(nodeproc)
        nodeproc.start()

    # spawn client proc and wait for it to finish
    clientproc = mp.Process(
        target=create_and_run,
        name="ChordClient",
        args=(m, DummyChordClient, bar1, bar2))
    clientproc.start()
    clientproc.join()

    # wait for node processes to finish
    for nodeproc in children:
        nodeproc.join()
