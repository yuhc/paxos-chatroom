#!/usr/bin/python3

import threading, sys, itertools, os, time

from threading import Thread, Lock
from ast import literal_eval

from network import Network

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
        self.uid = "Server#" +  str(node_id)
        self.num_nodes = num_nodes

        # Leaders
        self.is_leader = is_leader
        if is_leader:
            print(self.uid, "is leader")
        self.current_leader = -1

        # Replicas
        max_faulty = (num_nodes - 1) / 2
        if (node_id <= max_faulty):
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
        self.nt = Network(self.uid)
        try:
            self.t_recv = Thread(target=self.receive)
            self.t_recv.start()
        except:
            print(self.uid, "error: unable to start new thread")


    def exists_check_proposal(self, proposal, pair_set, compare):
        for (sn, p) in pair_set:
            if proposal == p:
                if (compare):
                    if (sn < self.slot_num):
                        return True
                else: 
                    return True
        return False

    
    def propose(self, proposal):
        if (!exists_check_proposal(proposal, self.decisions, False)):
            s = -1
            all_pairs = itertools.chain(proposals, decisions)
            sorted_all_pairs = sorted(all_pairs)
            if (next(all_pairs, None) != None):
                for sn, p in sorted_all_pairs:
                    if (sn == s + 1):
                        s = sn
                    else:
                        s = s + 1
                        break
                if s == sorted_all_pairs[-1][0]:
                    s = s + 1
            else:
                s = 0
            proposals.append((s, proposal))
            # TODO: Send to leader
            # send(leader, (propose, (s, p)))


    def perform(self, (kapa, cid, op)):
        if (exists_check_proposal((kapa, cid, op), self.decisions, True)):
            self.slot_num = self.slot_num + 1
        else:
            self.slot_num = self.slot_num + 1
            with open(self.log, 'a') as f:
                f.write(op)
            # TODO: send client response
            # send(kapa, (response, cid, "Done"))


    def broadcast_to_server(self, message):
        self.nt.broadcast(message)

    def send_to_server(self, dest_id, message):
        self.nt.send_to_server(dest_id, message)

    def send_to_client(self, dest_id, message):
        self.nt.send_to_client(dest_id, message)

    def receive(self):
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                # TODO: handle the received value
                print(self.uid, "handles", buf)


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

    def run(self):
        # TODO: for all acceptros send(a, ("p2a", self.node_id, pvalue))
        while(1):
            m = receive()
            triple = literal_eval(m)
            if (triple[0] == "p2b"):
                if (pvalue[2] == triple[2]):
                    self.waitfor.remove(triple[1])
                    if (len(self.waitfor) < num_nodes / 2):
                        # TODO: for all replicas send(p, ("decision", pvalue[1], pvalue[2]))
                        os._exit()



class Acceptor:
    def __init__(self):
        self.accepted = []
        self.ballot_num = -1;

    def run(self):
        while(1):
            # TODO: replace receive with actual receive
            m = receive()
            triple = literal_eval(m)

            if (triple[0] == "p1a"): 
                if triple[2] > self.ballot_num:
                    self.ballot_num = triple[2]
                # TODO: send(leader, ("p1b", self.node_id, self.ballot_num, "accepted"))
            elif (triple[0] == "p2a"):
                pvalue = triplep[2]
                if pvalue[0] >= self.ballot_num:
                    ballot_num = pvalue[0]
                    accepted.append(pvalue)
                # TODO: send(leader, ("p2b, self.node_id, self.ballot_num"))


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    is_leader = cmd[2] == "True"
    num_nodes = int(cmd[3])
    s = Server(node_id, is_leader, num_nodes)
    print(s.uid, "started")
    s.t_recv.join()
