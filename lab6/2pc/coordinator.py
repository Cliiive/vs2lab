import random
import logging

import stablelog

# coordinator messages
from const2PC import VOTE_REQUEST, GLOBAL_COMMIT, GLOBAL_ABORT, PREPARE_COMMIT
# participant messages
from const2PC import VOTE_COMMIT, VOTE_ABORT, READY_COMMIT
# misc constants
from const2PC import TIMEOUT


class Coordinator:
    """
    Implements a three phase commit coordinator.
    """

    def __init__(self, chan):
        self.channel = chan
        self.coordinator = self.channel.join('coordinator')
        self.participants = []  # list of all participants
        self.log = stablelog.create_log("coordinator-" + self.coordinator)
        self.stable_log = stablelog.create_log("coordinator-"
                                               + self.coordinator)
        self.logger = logging.getLogger("vs2lab.lab6.2pc.Coordinator")
        self.state = None

    def _enter_state(self, state):
        self.stable_log.info(state)  # Write to recoverable persistant log file
        self.logger.info("Coordinator {} entered state {}."
                         .format(self.coordinator, state))
        self.state = state

    def init(self):
        self.channel.bind(self.coordinator)
        self._enter_state('INIT')  # Start in INIT state.

        # Prepare participant information.
        self.participants = self.channel.subgroup('participant')

    def wait_for_participants(self, expected_msg):
        """
        Generic wait function for both VOTE and PRE-COMMIT phases.
        """
        yet_to_receive = list(self.participants)
        while len(yet_to_receive) > 0:
            # We wait for messages
            msg = self.channel.receive_from(self.participants, TIMEOUT - 1)

            if (not msg) or (msg[1] == VOTE_ABORT):
                # CASE: Timeout or Vote Abort
                if self.state == 'WAIT':
                    # Phase 1: If anyone fails/aborts, we must abort everyone.
                    reason = "timeout from participant" if not msg else "local_abort from " + msg[0]
                    self._enter_state('ABORT')
                    self.channel.send_to(self.participants, GLOBAL_ABORT)
                    return "Coordinator {} terminated in state ABORT. Reason: {}."\
                        .format(self.coordinator, reason)
                else:
                    # Phase 3 (PRECOMMIT):
                    # We are in PRECOMMIT. This means everyone already voted YES in Phase 1.
                    # If someone crashes now (timeout), we MUST proceed to COMMIT according to 3PC.
                    # We stop waiting for the crashed node and return success so 'run' proceeds.
                    
                    assert (self.state == 'PRECOMMIT')
                    assert (not msg) # VOTE_ABORT is impossible in this phase
                    
                    self.logger.warning("Participant crashed during PRECOMMIT. Proceeding to GLOBAL_COMMIT anyway.")
                    return None # Returning None means "Success/Continue" to the run loop

            else:
                # CASE: Success (Received the expected message)
                # [FIX] Compare against the argument, not hardcoded VOTE_COMMIT
                assert msg[1] == expected_msg 
                yet_to_receive.remove(msg[0])
        
        return None

    def run(self):
        # if random.random() > 3/4:  # simulate a crash
        #     return "Coordinator crashed in state INIT."

        # Request local votes from all participants
        self._enter_state('WAIT')
        self.channel.send_to(self.participants, VOTE_REQUEST)

        # if random.random() > 2/3:  # simulate a crash
        #     return "Coordinator crashed in state WAIT."

        # Collect votes from all participants
        # If this returns a string, it means we aborted.
        abort_reason = self.wait_for_participants(VOTE_COMMIT)
        if abort_reason:
            return abort_reason

        # --- PHASE 2: PRE-COMMIT ---
        # All participants voted commit. Enter PRECOMMIT.
        self._enter_state('PRECOMMIT')
        self.channel.send_to(self.participants, PREPARE_COMMIT)

        # Wait for the READY_COMMIT from all participants
        # If a participant crashes here, wait_for_participants returns None (success)
        # because we are in PRECOMMIT state.
        self.wait_for_participants(READY_COMMIT)
        
        # --- PHASE 3: GLOBAL COMMIT ---
        self._enter_state('COMMIT')
        self.channel.send_to(self.participants, GLOBAL_COMMIT)
        
        return "Coordinator {} terminated in state COMMIT."\
            .format(self.coordinator)