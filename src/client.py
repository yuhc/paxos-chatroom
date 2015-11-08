#!/usr/bin/python3

import sys, time, threading
from threading import Thread, Lock

from network   import Network
from ast       import literal_eval

TERM_LOG   = False

class Client:

    REQUEST_TIME  = 3
    TIME_ALLCLEAR = 2

    '''
    @uid is used for printing the messages.
    '''
    def __init__(self, client_id, num_nodes):
        self.client_id = client_id
        self.command_id = 0
        self.num_nodes = num_nodes
        self.uid = "Client#" + str(client_id)
        self.chatlog = []
        self.queue   = []    # all waiting messages
        self.history = set() # all received messages
        self.leader_id = 0   # default leader is server#0

        # network controller
        self.nt = Network(self.uid, self.num_nodes)
        try:
            self.t_recv = Thread(target=self.receive)
            self.t_recv.start()
        except:
            print(self.uid, "error: unable to start new thread")

        # send requests periodically
        #self.period_request()

    def send(self, message):
        self.nt.broadcast_to_server(message)

    def send_request(self, triple):
        encode = "'request', " + str(triple)
        # broadcast to all replicas or servers
        self.send(encode)

    def period_request(self):
        for tp in self.queue:
            self.send_request(tp)
        #threading.Timer(self.REQUEST_TIME, self.period_request).start()

    def monitor_queue(self):
        while self.queue:
            time.sleep(self.TIME_ALLCLEAR)
        self.nt.send_to_master(str(("allCleared", self.client_id)))

    def receive(self):
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                # TODO: handle the received value
                buf = literal_eval(buf)
                # buf = buf.split()

                # send request to server (leader)
                # should we send requests to all replicas?
                if buf[0] == "sendMessage":
                    self.command_id = self.command_id + 1
                    triple = (self.client_id, self.command_id, buf[1])
                    self.queue.append(triple)
                    self.send_request(triple)

                # clear the message queue
                if buf[0] == "allClear":
                    threading.Timer(0, self.monitor_queue).start()

                # print chat log
                if buf[0] == "printChatLog":
                    if TERM_LOG:
                        print(self.uid, "prints chat log")
                    for l in self.chatlog:
                        # TODO: may need index_number instead of slot_num
                        if TERM_LOG:
                            print(self.uid, ">>", l[1]-1, l[0], l[2])
                        #else:
                            # print(l[1]-1, " ", l[0], ": ", l[2], sep='')
                        self.nt.send_to_master(str(("chatLog",
                            "{0} {1}: {2}".format(l[1]-1, l[0], l[2]))))

                # receive response from leader, send ask to master
                # format: (response, client_id, cid, (index, chat))
                if buf[0] == "response":
                    if buf[1] == self.client_id:
                        try:
                            # remove the message from self.queue
                            triple = next(x for x in self.queue
                                          if x[1] == buf[2])
                            self.queue.remove(triple)
                        except StopIteration:
                            pass
                    if not buf in self.history:
                        # add decision into self.chatlog
                        # log format: (client_id, slot_num, result)
                        self.chatlog.append((buf[1], buf[3][0], buf[3][1]))
                        self.history.add(buf)
                        if TERM_LOG:
                            print(self.uid, " logs <", buf[3], ">", sep="")

                if buf[0] == "leaderElected":
                    self.period_request()


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    num_nodes = int(cmd[2])
    c = Client(node_id, num_nodes)
    if TERM_LOG:
        print(c.uid, "started")
    time.sleep(3)    # this line is for debug
    c.t_recv.join()
