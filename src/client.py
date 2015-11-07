#!/usr/bin/python3

import sys, time, threading
from threading import Thread, Lock

from network   import Network
from ast       import literal_eval

class Client:

    REQUEST_TIME = 3

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
        self.period_request()

    def send(self, message):
        self.nt.broadcast_to_server(message)

    def send_request(self, triple):
        encode = "'request', " + str(triple)
        # broadcast to all replicas or servers
        self.send(encode)

    def period_request(self):
        for tp in self.queue:
            self.send_request(tp)
        threading.Timer(self.REQUEST_TIME, self.period_request).start()

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
                    while self.queue:
                        time.sleep(2)
                    self.nt.send_to_master(str(("allCleared", self.client_id)))

                # print chat log
                if buf[0] == "printChatLog":
                    print(self.uid, "prints chat log")
                    for l in self.chatlog:
                        # TODO: may need index_number instead of slot_num
                        print(self.uid, ">>", l[0], self.client_id, l[1])

                # receive response from leader, send ask to master
                # format: (response, client_id, cid, (index, chat))
                if buf[0] == "response":
                    # DB: self.nt.send_to_master("'messageHasBeenLogged'")
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
                        self.chatlog.append(buf[3])
                        self.history.add(buf)
                        print(self.uid, " logs <", buf[3], ">", sep="")


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    num_nodes = int(cmd[2])
    c = Client(node_id, num_nodes)
    print(c.uid, "started")
    time.sleep(3)    # this line is for debug
    c.t_recv.join()
