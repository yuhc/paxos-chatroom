#!/usr/bin/python3

import threading, sys

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
        self.uid = "Server[" + str(node_id) + "]"
        self.num_nodes = num_nodes

        # Leaders
        self.is_leader = is_leader
        if is_leader:
            print(node_id, "is leader")
        self.current_leader = -1


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


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    is_leader = cmd[2] == "True"
    num_nodes = int(cmd[3])
    s = Server(node_id, is_leader, num_nodes)
    print(s.uid, "started")
