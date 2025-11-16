import constRPC
import threading
from context import lab_channel


class DBList:
    def __init__(self, basic_list):
        self.value = list(basic_list)

    def append(self, data):
        self.value = self.value + [data]
        return self

class AsyncAppend(threading.Thread):
    def __init__(self, chan, server, msglst, callback):
        threading.Thread.__init__(self)
        self.chan = chan
        self.server = server
        self.msglst = msglst
        self.callback = callback

    def run(self):
        self.chan.send_to(self.server, self.msglst)  # send msg to server
        msgrcv = self.chan.receive_from(self.server)  # wait for response
        if self.callback:
            self.callback(msgrcv[1])  # pass it to caller

class Client():
    def __init__(self, asyncAppend):
        self.chan = lab_channel.Channel()
        self.client = self.chan.join('client')
        self.server = None
        self.asyncAppend = False
        self.asyncThread = None

    def run(self):
        self.chan.bind(self.client)
        self.server = self.chan.subgroup('server')

    def stop(self):
        if self.asyncThread and self.asyncThread.is_alive():
            self.asyncThread.join()
            self.asyncThread = None
        self.chan.leave('client')

    def append(self, data, db_list, callback=None):
        assert isinstance(db_list, DBList)
        msglst = (constRPC.APPEND, data, db_list)  # message payload
        self.chan.send_to(self.server, msglst)  # send msg to server
        
        if self.asyncThread and self.asyncThread.is_alive():
            self.asyncThread.join()
            self.asyncThread = None

        if self.asyncAppend:
            self.asyncThread = AsyncAppend(self.chan, self.server, msglst, callback)
            self.asyncThread.start()
            return None  # async call, no immediate result
        else:
            msgrcv = self.chan.receive_from(self.server)  # wait for response
            
        return msgrcv[1]  # pass it to caller


class Server:
    def __init__(self):
        self.chan = lab_channel.Channel()
        self.server = self.chan.join('server')
        self.timeout = 3

    @staticmethod
    def append(data, db_list):
        assert isinstance(db_list, DBList)  # - Make sure we have a list
        return db_list.append(data)

    def run(self):
        self.chan.bind(self.server)
        while True:
            msgreq = self.chan.receive_from_any(self.timeout)  # wait for any request
            if msgreq is not None:
                client = msgreq[0]  # see who is the caller
                msgrpc = msgreq[1]  # fetch call & parameters
                if constRPC.APPEND == msgrpc[0]:  # check what is being requested
                    result = self.append(msgrpc[1], msgrpc[2])  # do local call
                    self.chan.send_to({client}, result)  # return response
                else:
                    pass  # unsupported request, simply ignore
