#!/usr/bin/python3

import threading, sys
import network

from threading import Thread, Lock

class Server:

    '''
    @id: [0 .. num_nodes-1].
    @is_leader is set to `True` when creating Server0, otherwise, to `False`.
    @num_nodes is used to identify the broadcast range.
    @uid is used for printing the messages.
    @current_leader is updated when receiving heartbeat from the leader.
    Every server is a replica.
    '''
    def __init__(self, node_id, is_leader, num_nodes):
        self.node_id = node_id
        self.uid = "Server " +  str(node_id)
        self.num_nodes = num_nodes

        # Leaders
        self.is_leader = is_leader
        if is_leader:
            print(self.uid, "is leader")
        self.current_leader = -1

        # Replicas
        max_faulty = (num_nodes - 1) / 2
        if (nod_id <= max_faulty):
            # f+1  servers are replicas
            # 2f+1 (all)  servers are acceptors
            self.is_replica = True
            self.log_name = "server_" + str(self.node_id) + ".log"
            self.slot_num = 1
            self.proposals = []
            self.decisions = []
        else:
            self.is_replica = False

        # network controller
        self.nt = Network(uid)
        try:
            thread.start_new_thread(receive)
        except:
            print("Error: unable to start new thread")

    def exists(proposal, pair_set):
        for (sn, p) in pair_set:
            if proposal == p:
                return slot_num
        return None

    def propose(proposal):
        if (exists(proposal, self.decisions) == None):
            # TODO: propose

    def broadcast_to_server(message):
        self.nt.broadcast(message)
        
    def send_to_server(dest_id, message):
        self.nt.send_to_server(dest_id, message)

    def send_to_client(dest_id, message):
        self.nt.send_to_client(dest_id, message)

    def receive():
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                # TODO: handle the received value


class Scout:
    def __init__(self, leader_id, num_nodes, b):
        self.leader_id = leader_id
        self.ballot_num = b
        self.pvalues = None
        self.waitfor = set(range(0, num_nodes))

class Commander:
    def __init__(self, leader_id, num_nodes, pvalue):
        self.leader_id = leader_id
        self.pvalue = pvalue
        self.ballot_num = pvalue[0]
        self.slot_num   = pvalue[1]
        self.proposal   = pvalue[2]
        self.waitfor = set(range(0, num_nodes))

class Acceptor:
    def __init__(self):
        self.accepted = []
        self.ballot_num = -1;

    def run():
        while(1):
            # TODO: replace receive with actual receive
            msg = receive();


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    is_leader = cmd[2] == "True"
    num_nodes = int(cmd[3])
    s = Server(node_id, is_leader, num_nodes)
    print(s.uid, "started")
