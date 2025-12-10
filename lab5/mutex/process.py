import logging
import random
import time

from constMutex import ENTER, RELEASE, ALLOW, ACTIVE
from constMutex import HEARTBEAT


class Process:
    """
    Implements access management to a critical section (CS) via fully
    distributed mutual exclusion (MUTEX).

    Processes broadcast messages (ENTER, ALLOW, RELEASE) timestamped with
    logical (lamport) clocks. All messages are stored in local queues sorted by
    logical clock time.

    Processes follow different behavioral patterns. An ACTIVE process competes 
    with others for accessing the critical section. A PASSIVE process will never 
    request to enter the critical section itself but will allow others to do so.

    A process broadcasts an ENTER request if it wants to enter the CS. A process
    that doesn't want to ENTER replies with an ALLOW broadcast. A process that
    wants to ENTER and receives another ENTER request replies with an ALLOW
    broadcast (which is then later in time than its own ENTER request).

    A process enters the CS if a) its ENTER message is first in the queue (it is
    the oldest pending message) AND b) all other processes have sent messages
    that are younger (either ENTER or ALLOW). RELEASE requests purge
    corresponding ENTER requests from the top of the local queues.

    Message Format:

    <Message>: (Timestamp, Process_ID, <Request_Type>)

    <Request Type>: ENTER | ALLOW  | RELEASE

    """

    def __init__(self, chan):
        self.channel = chan  # Create ref to actual channel
        self.process_id = self.channel.join('proc')  # Find out who you are
        self.all_processes: list = []  # All procs in the proc group
        self.other_processes: list = []  # Needed to multicast to others
        self.queue = []  # The request queue list
        self.clock = 0  # The current logical clock
        self.peer_name = 'unassigned'  # The original peer name
        self.peer_type = 'unassigned'  # A flag indicating behavior pattern
        #######
        # track last seen time for peers to detect crashes
        self.last_seen = {}  # map: peer_id -> timestamp
        # how long (seconds) to wait until a peer is considered crashed
        self.peer_timeout = 5
        #######
        self.logger = logging.getLogger("vs2lab.lab5.mutex.process.Process")

    def __mapid(self, id='-1'):
        # format channel member address
        if id == '-1':
            id = self.process_id
        return 'Proc-'+str(id)

    def __cleanup_queue(self):
        if len(self.queue) > 0:
            # self.queue.sort(key = lambda tup: tup[0])
            self.queue.sort()
            # There should never be old ALLOW messages at the head of the queue
            while self.queue[0][2] == ALLOW:
                del (self.queue[0])
                if len(self.queue) == 0:
                    break

    def __request_to_enter(self):
        self.clock = self.clock + 1  # Increment clock value
        request_msg = (self.clock, self.process_id, ENTER)
        self.queue.append(request_msg)  # Append request to queue
        self.__cleanup_queue()  # Sort the queue
        self.channel.send_to(self.other_processes, request_msg)  # Send request

    def __allow_to_enter(self, requester):
        self.clock = self.clock + 1  # Increment clock value
        msg = (self.clock, self.process_id, ALLOW)
        self.channel.send_to([requester], msg)  # Permit other

    def __release(self):
        # need to be first in queue to issue a release
        assert self.queue[0][1] == self.process_id, 'State error: inconsistent local RELEASE'

        # construct new queue from later ENTER requests (removing all ALLOWS)
        tmp = [r for r in self.queue[1:] if r[2] == ENTER]
        self.queue = tmp  # and copy to new queue
        self.clock = self.clock + 1  # Increment clock value
        msg = (self.clock, self.process_id, RELEASE)
        # Multicast release notification
        self.channel.send_to(self.other_processes, msg)

    def __allowed_to_enter(self):
        # See who has sent a message (the set will hold at most one element per sender)
        processes_with_later_message = set([req[1] for req in self.queue[1:]])
        # Access granted if this process is first in queue and all others have answered (logically) later
        first_in_queue = self.queue[0][1] == self.process_id
        all_have_answered = len(self.other_processes) == len(
            processes_with_later_message)
        return first_in_queue and all_have_answered

    def __send_heartbeat(self):
        """Send periodic heartbeat to all peers (used for crash detection)."""
        self.clock = self.clock + 1
        msg = (self.clock, self.process_id, HEARTBEAT)
        try:
            self.channel.send_to(self.other_processes, msg)
        except AssertionError:
            # if a receiver is unknown the channel may raise; ignore here
            pass

    #######

    def __check_peer_timeouts(self):
        """Remove peers that did not send heartbeats recently."""
        now = time.time()
        removed = []
        for pid, ts in list(self.last_seen.items()):
            if pid == self.process_id:
                continue
            if now - ts > self.peer_timeout:
                # mark as removed
                removed.append(pid)

        if removed:
            for pid in removed:
                # remove from groups and queues
                if pid in self.all_processes:
                    self.all_processes.remove(pid)
                if pid in self.other_processes:
                    try:
                        self.other_processes.remove(pid)
                    except ValueError:
                        pass
                # purge any pending messages from removed peer
                self.queue = [r for r in self.queue if r[1] != pid]
                if pid in self.last_seen:
                    del self.last_seen[pid]
                self.logger.warning("Detected crashed peer {}. Removed from peer lists.".format(self.__mapid(pid)))
    #######

    def __receive(self):
        # Pick up any message
        _receive = self.channel.receive_from(self.other_processes, 3)
        if _receive:
            msg = _receive[1]

            self.clock = max(self.clock, msg[0])  # Adjust clock value...
            self.clock = self.clock + 1  # ...and increment

            # map message type to human readable label (include HEARTBEAT)
            msg_type = None
            if msg[2] == ENTER:
                msg_type = 'ENTER'
            elif msg[2] == ALLOW:
                msg_type = 'ALLOW'
            elif msg[2] == RELEASE:
                msg_type = 'RELEASE'
            elif msg[2] == HEARTBEAT:
                msg_type = 'HEARTBEAT'
            else:
                msg_type = str(msg[2])

            self.logger.debug("{} received {} from {}.".format(
                self.__mapid(), msg_type, self.__mapid(msg[1])))

            if msg[2] == ENTER:
                self.queue.append(msg)  # Append an ENTER request
                # and unconditionally allow (don't want to access CS oneself)
                self.__allow_to_enter(msg[1])
            #######
            elif msg[2] == HEARTBEAT:
                # update last seen time for heartbeat messages
                # (used for crash detection)
                self.last_seen[msg[1]] = time.time()
                # no queue entry required for heartbeat
            #######
            elif msg[2] == ALLOW:
                self.queue.append(msg)  # Append an ALLOW
            elif msg[2] == RELEASE:
                # assure release requester indeed has access (his ENTER is first in queue)
                assert self.queue[0][1] == msg[1] and self.queue[0][2] == ENTER, 'State error: inconsistent remote RELEASE'
                del (self.queue[0])  # Just remove first message

            self.__cleanup_queue()  # Finally sort and cleanup the queue
        else:
            self.logger.info("{} timed out on RECEIVE. Local queue: {}".
                             format(self.__mapid(),
                                    list(map(lambda msg: (
                                        'Clock '+str(msg[0]),
                                        self.__mapid(msg[1]),
                                        msg[2]), self.queue))))

    def init(self, peer_name, peer_type):
        self.channel.bind(self.process_id)

        self.all_processes = list(self.channel.subgroup('proc'))
        # sort string elements by numerical order
        self.all_processes.sort(key=lambda x: int(x))

        self.other_processes = list(self.channel.subgroup('proc'))
        self.other_processes.remove(self.process_id)

        # initialize last_seen timestamps for all known peers
        now = time.time()
        for pid in self.all_processes:
            self.last_seen[pid] = now

        self.peer_name = peer_name  # assign peer name
        self.peer_type = peer_type  # assign peer behavior

        self.logger.info("{} joined channel as {}.".format(
            peer_name, self.__mapid()))

    def run(self):
        #######
        # track last time we sent a heartbeat
        last_hb = 0

        while True:
            # Enter the critical section if
            # 1) there are more than one process left and
            # 2) this peer has active behavior and
            # 3) random is true
            if len(self.all_processes) > 1 and \
                    self.peer_type == ACTIVE and \
                    random.choice([True, False]):
                self.logger.debug("{} wants to ENTER CS at CLOCK {}."
                                  .format(self.__mapid(), self.clock))

                self.__request_to_enter()
                while not self.__allowed_to_enter():
                    self.__receive()
                    # periodically send heartbeats while waiting
                    if time.time() - last_hb > 1:
                        self.__send_heartbeat()
                        last_hb = time.time()

                # Stay in CS for some time ...
                sleep_time = random.randint(0, 2000)
                self.logger.debug("{} enters CS for {} milliseconds."
                                  .format(self.__mapid(), sleep_time))
                print(" CS <- {}".format(self.__mapid()))
                time.sleep(sleep_time/1000)

                # ... then leave CS
                print(" CS -> {}".format(self.__mapid()))
                self.__release()
                continue

            # Occasionally serve requests to enter and send heartbeat
            if random.choice([True, False]):
                self.__receive()

            # send periodic heartbeat to signal aliveness
            if time.time() - last_hb > 1:
                self.__send_heartbeat()
                last_hb = time.time()

            # check for peers that timed out and remove them
            self.__check_peer_timeouts()
        #######
