#!/usr/bin/python3

import sys, time, threading
from threading import Thread, Lock

from network import Network

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
        self.queue = []
        self.leader_id = 0 # default leader is server#0

        # network controller
        self.nt = Network(self.uid, self.num_nodes)
        try:
            self.t_recv = Thread(target=self.receive)
            self.t_recv.start()
        except:
            print(self.uid, "error: unable to start new thread")

        # send requests periodically
        self.period_request()

    def send(self, dest_id, message):
        self.nt.send_to_server(dest_id, message)

    def send_request(self, triple):
        encode = " ".join(triple)
        self.send(self.leader_id, encode)

    def period_request(self):
        for tp in self.queue:
            self.send_request(tp)
        threading.Timer(self.REQUEST_TIME, self.period_request).start()

    def receive(self):
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                # TODO: handle the received value
                print(self.uid, "handles", buf)
                buf = buf.split()

                # send request to server (leader)
                if buf[0] == "sendMessage":
                    self.command_id = self.command_id + 1
                    triple = [str(self.client_id), str(self.command_id), buf[1]]
                    self.queue.append(triple)
                    self.send_request(triple)

                # clear the message queue
                if buf[0] == "allClear":
                    self.queue[:] = []

                # print chat log
                if buf[0] == "printChatLog":
                    print(self.uid, "prints chat log")
                    for l in self.chatlog:
                        print(self.uid, ">>", l)

                # receive response from leader, send ask to master
                if buf[0] == "response":
                    # TODO: add decision into self.chatlog
                    # TODO: remove the message from self.queue
                    self.nt.send_to_master("messageHasBeenLogged")

                # receive heartbeat
                if buf[0] == "heartbeat":
                    # TODO: handle heartbeat
                    print(buf[0])


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    num_nodes = int(cmd[2])
    c = Client(node_id, num_nodes)
    print(c.uid, "started")
    time.sleep(3)    # this line is for debug
    c.send(0, 'aaa') # this line is for debug
    c.t_recv.join()
