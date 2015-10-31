#!/usr/bin/python3

import sys, time
from threading import Thread, Lock

from network import Network

class Client:

    '''
    @uid is used for printing the messages.
    '''
    def __init__(self, client_id, num_nodes):
        self.client_id = client_id
        self.num_nodes = num_nodes
        self.uid = "Client#" + str(client_id)

        # network controller
        self.nt = Network(self.uid)
        try:
            self.t_recv = Thread(target=self.receive)
            self.t_recv.start()
        except:
            print(self.uid, "error: unable to start new thread")

    def send(self, dest_id, message):
        self.nt.send_to_server(dest_id, message)

    def receive(self):
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                # TODO: handle the received value
                print(buf)
                buf = buf.split()
                if buf[0] == "sendMessage":
                    # TODO: send message to leader
                    print(buf[0])
                    self.nt.send_to_master("messageHasBeenLogged")
                if buf[0] == "response":
                    self.nt.send_to_master("messageHasBeenLogged")
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
