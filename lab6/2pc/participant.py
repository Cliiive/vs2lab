import random
import logging

# coordinator messages
from const2PC import VOTE_REQUEST, GLOBAL_COMMIT, GLOBAL_ABORT, PREPARE_COMMIT
# participant decissions
from const2PC import LOCAL_SUCCESS, LOCAL_ABORT, READY_COMMIT
# participant messages
from const2PC import VOTE_COMMIT, VOTE_ABORT
# misc constants
from const2PC import TIMEOUT

import stablelog


class Participant:
    """
    Implements a three phase commit participant (3PC).
    """

    def __init__(self, chan):
        self.channel = chan
        self.participant = self.channel.join('participant')
        self.stable_log = stablelog.create_log(
            "participant-" + self.participant)
        self.logger = logging.getLogger("vs2lab.lab6.3pc.Participant")
        self.coordinator = {}
        self.all_participants = {}
        self.state = 'NEW'

    @staticmethod
    def _do_work():
        # Simulate local activities that may succeed or not
        return LOCAL_ABORT if random.random() > 2/3 else LOCAL_SUCCESS

    def _enter_state(self, state):
        self.stable_log.info(state)  # Write to recoverable persistant log file
        self.logger.info("Participant {} entered state {}."
                         .format(self.participant, state))
        self.state = state

    def init(self):
        self.channel.bind(self.participant)
        self.coordinator = self.channel.subgroup('coordinator')
        self.all_participants = self.channel.subgroup('participant')
        self._enter_state('INIT')  # Start in local INIT state.
        
    def _elect_new_coordinator(self):
        # Deterministic election: The participant with the lowest ID wins
        participants = sorted([p for p in list(self.all_participants)])
        return participants[0] if participants else self.participant

    def _be_helpful_coordinator(self, state):
        """
        Logic for the participant that becomes the new coordinator (Pk).
        According to README 3.2.2.b:
        1. Pk acts based on the state it was in when the old coordinator crashed.
        """
        self.logger.info(f"{self.participant} is the new coordinator! Taking over in state {state}.")
        
        self.channel.send_to(self.all_participants, self.state)
        
        # Case 1: Pk is in READY (The README calls this WAIT for Coords, but Participants are in READY here)
        # Logic: We voted YES, but we never got a PREPARE_COMMIT. We don't know if someone else voted NO.
        # Safe decision: ABORT
        if state == 'READY':
            self.logger.info(f"{self.participant} in READY -> Deciding GLOBAL_ABORT.")
            self.channel.send_to(self.all_participants, GLOBAL_ABORT)
            self._enter_state('ABORT')
            
        # Case 2: Pk is in PRECOMMIT
        # Logic: We received PREPARE_COMMIT. This proves the old coordinator got VOTE_COMMIT from everyone.
        # Safe decision: COMMIT
        elif state == 'PRECOMMIT':
            self.logger.info(f"{self.participant} in PRECOMMIT -> Deciding GLOBAL_COMMIT.")
            self.channel.send_to(self.all_participants, GLOBAL_COMMIT)
            self._enter_state('COMMIT')
            
        # Case 3: Pk is already in COMMIT or ABORT
        # Logic: Just ensure everyone else knows the final result.
        # elif state == 'COMMIT':
        #     self.channel.send_to(self.all_participants, GLOBAL_COMMIT)
        # elif state == 'ABORT':
        #     self.channel.send_to(self.all_participants, GLOBAL_ABORT)

    def _listen_to_new_coordinator(self):
        """
        Logic for participants waiting for the new coordinator.
        """
        self.logger.info(f"{self.participant} Waiting for decision from new coordinator...")
        
        # We assume the coordinator sends up to 2 messages:
        # 1. State Announcement (optional/sync)
        # 2. Final Decision (Global Commit/Abort)
        
        while True:
            msg = self.channel.receive_from(self.all_participants, TIMEOUT)
            
            if not msg:
                self.logger.error(f"{self.participant}: New coordinator timed out! Protocol failed.")
                return

            # Check if this is the Final Decision
            if msg == GLOBAL_ABORT:
                self.logger.info(f"{self.participant} Received GLOBAL_ABORT from new coordinator.")
                self._enter_state('ABORT')
                break # Exit loop, we are done
            elif msg == GLOBAL_COMMIT:
                self.logger.info(f"{self.participant} Received GLOBAL_COMMIT from new coordinator.")
                self._enter_state('COMMIT')
                break # Exit loop, we are done

    def run(self):
        # Wait for start of joint commit
        msg = self.channel.receive_from(self.coordinator, TIMEOUT)

        if not msg:  # Crashed coordinator - give up entirely
            # decide to locally abort (before doing anything)
            decision = LOCAL_ABORT
            self._enter_state('ABORT')

        else:  # Coordinator requested to vote, joint commit starts
            # Expecting tuple: (sender, VOTE_REQUEST)
            assert msg[1] == VOTE_REQUEST

            # Firstly, come to a local decision
            decision = self._do_work()  # proceed with local activities

            # If local decision is negative,
            # then vote for abort and quit directly
            if decision == LOCAL_ABORT:
                self.channel.send_to(self.coordinator, VOTE_ABORT)
                self._enter_state('ABORT')

            # If local decision is positive,
            # we are ready to proceed the joint commit
            else:
                assert decision == LOCAL_SUCCESS
                self._enter_state('READY')

                # Notify coordinator about local commit vote
                self.channel.send_to(self.coordinator, VOTE_COMMIT)

                # Wait for PREPARE_COMMIT or GLOBAL_ABORT
                msg = self.channel.receive_from(self.coordinator, TIMEOUT)

                if not msg:
                    # Coordinator crashed while participants in READY
                    self.logger.info(f"{self.participant}: Coordinator timeout in READY state. Starting election.")
                    new_coord = self._elect_new_coordinator()
                    if self.participant == new_coord:
                        self._be_helpful_coordinator('READY')
                    else:
                        self._listen_to_new_coordinator()
                else:
                    # FIX: Access msg[1] because msg is a tuple (sender, payload)
                    if msg[1] == PREPARE_COMMIT:
                        self._enter_state('PRECOMMIT')
                        
                        # Acknowledge PRECOMMIT to Coordinator
                        self.channel.send_to(self.coordinator, READY_COMMIT)
                        
                        # Wait for Final GLOBAL_COMMIT
                        msg = self.channel.receive_from(self.coordinator, TIMEOUT)
                        
                        if not msg:
                            # Coordinator crashed while participant in PRECOMMIT
                            self.logger.info(f"{self.participant}: Coordinator timeout in PRECOMMIT state. Starting election.")
                            new_coord = self._elect_new_coordinator()
                            if self.participant == new_coord:
                                self._be_helpful_coordinator('PRECOMMIT')
                            else:
                                self._listen_to_new_coordinator()
                        else:
                            # FIX: Access msg[1] here as well
                            if msg[1] == GLOBAL_COMMIT:
                                self._enter_state('COMMIT')
                            elif msg[1] == GLOBAL_ABORT:
                                self._enter_state('ABORT')
                    
                    # FIX: Access msg[1] here as well
                    elif msg[1] == GLOBAL_ABORT:
                         self._enter_state('ABORT')
                    else:
                        # Unexpected message
                        self._enter_state('ABORT')

        return "Participant {} terminated in state {} due to {}.".format(
            self.participant, self.state, decision)