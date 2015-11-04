#!/usr/bin/python3

import threading, sys, itertools, os, time

from threading import Thread, Lock
from ast import literal_eval

from network import Network

class Server:

    TIME_HEARTBEAT = 3

    '''
    @id: [0 .. num_nodes-1].
    @is_leader  is set to `True` when creating Server0, otherwise, to `False`.
    @is_replica is set to `True` if node_id is less than f+1
    @num_nodes  is used to identify the broadcast range.
    @uid        is used for printing the messages.
    @current_leader is updated when receiving heartbeat from the leader.
    Every server is a replica.
    '''
    def __init__(self, node_id, is_leader, num_nodes, num_clients):
        self.node_id = node_id
        self.uid = "Server#" +  str(node_id)
        self.num_nodes = num_nodes
        self.num_clients = num_clients

        # network controller
        self.nt = Network(self.uid, num_nodes, num_clients)
        try:
            self.t_recv = Thread(target=self.receive)
            self.t_recv.start()
        except:
            print(self.uid, "error: unable to start new thread")

        # Leaders
        self.is_leader = is_leader
        if is_leader:
            self.leader = Leader(node_id)
            print(self.uid, "is leader")
        self.current_leader = -1 # updated when receiving leader's heartbeat
                                 # remember to update replica.leader_id

        # Replicas
        max_faulty = (num_nodes - 1) / 2 # f in the paper
        if (node_id <= max_faulty):
            # f+1  servers are replicas
            # 2f+1 (all)  servers are acceptors
            self.is_replica = True
            self.replica = Replica(node_id, self.nt)
        else:
            self.is_replica = False

        # TODO: leader broadcasts heartbeat
        if is_leader:
            time.sleep(2) # wait for other servers to start
            self.send_heartbeat()

    def broadcast_to_server(self, message):
        self.nt.broadcast_to_server(message)

    def broadcast_to_client(self, message):
        self.nt.broadcast_to_client(message)

    def send_to_server(self, dest_id, message):
        self.nt.send_to_server(dest_id, message)

    def send_to_client(self, dest_id, message):
        self.nt.send_to_client(dest_id, message)

    def receive(self):
        while 1:
            buf = self.nt.receive()
            if len(buf) > 0:
                print(self.uid, "handles", buf)
                # TODO: handle the received value
                message = list(literal_eval(buf))

                # to replica
                if (message[0] in ['request', 'decision']):
                    self.replica_operation(message)
                # to leader
                if (message[0] == "propose"):
                    self.leader_operation(message)
                # to server
                if (message[0] == "heartbeat"):
                    self.receive_heartbeat(message)

    def replica_operation(self, message):
        # request from client:  ['request', (k, cid, message)]
        if (message[0] == "request"):
            self.replica.propose(message[1])
        # decision from leader: ['decision', (slot_num, proposal)]
        elif (message[0] == "decision"):
            self.replica.decide(message[1])

    def leader_operation(self, message):
        if (message[0] == "propose"):
            # TODO: handles proposal
            print(message)

    def send_heartbeat(self):
        self.broadcast_to_server("'heartbeat', " + str(self.node_id))
        threading.Timer(self.TIME_HEARTBEAT, self.send_heartbeat).start()

    def receive_heartbeat(self, message):
        # heartbeat from leader: ['heartbeat', leader_id]
        self.current_leader = int(message[1])
        if self.is_replica:
            self.replica.set_leader(int(message[1]))
        print("receive heartbeat from", message[1])
        # TODO: add timeout timer
        

class Replica:
    '''
    @state is trivial in this implementation
    '''
    def __init__(self, node_id, nt):
        self.node_id   = node_id
        self.log_name  = "server_" + str(node_id) + ".log"
        self.slot_num  = 1
        self.proposals = set()
        self.decisions = set()
        self.nt = nt

    def set_leader(self, leader_id):
        self.leader_id = leader_id

    def decide(self, decision):
        # dec = (slot_num, proposal)
        self.decisions.add(decision)
        flt1 = filter(lambda x: x[0] == self.slot_num, self.decisions)
        while flt1:
            p1 = flt1[0][1]
            flt2 = filter(lambda x: x in self.proposals and x[1] != p1, flt1)
            if flt2:
                self.propose(flt2[0][1]) # repropose
            self.perform(p1)
            flt1 = filter(lambda x: x[0] == self.slot_num, self.decisions)

    def propose(self, proposal):
        if (not self.is_in_set(proposal, self.decisions, False)):
            all_pairs = self.proposals.union(self.decisions)
            sorted_all_pairs = sorted(list(all_pairs), key=lambda x:x[0])
            s = 1 # new minimum available slot
            for (st, pt) in sorted_all_pairs:
                if (st == s):
                    continue
                s = s + 1
                if (st != s + 1):
                    break
            self.proposals.add((s, proposal))
            # send `propose, (s, p)` to leader
            self.send_to_server(self.leader_id,
                                str(("propose", s, proposal)))

    def perform(self, proposal):
        if (self.is_in_set(proposal, self.decisions, True)):
            self.slot_num = self.slot_num + 1
        else:
            self.slot_num = self.slot_num + 1
            # TODO: maybe not necessary to log
            with open(self.log_name, 'a') as f:
                f.write(proposal[3])
            # send `response, (cid, result)` to client
            self.broadcast_to_client(p[0], str(("response", p[1], "Done")))

    '''
    check whether there exists any <s, @proposal> in @pair_set
    @cmp_slot: True if need check s < @self.slot_num
    '''
    def is_in_set(self, proposal, pair_set, cmp_slot):
        if cmp_slot:
            flt = filter(lambda x: x[1] == proposal and x[0] < self.slot_num,
                         pair_set)
        else:
            flt = filter(lambda x: x[1] == proposal, pair_set)
        return bool(flt)


class Leader:
    '''
    @self.node_id:    self()
    @self.ballot_num: initially (0, self())
    @self.active:     initially false
    @self.proposals:  initially empty
    '''
    def __init__(self, node_id):
        self.node_id    = node_id
        self.active     = False
        self.proposals  = []
        self.ballot_num = 0


class Scout:
    def __init__(self, leader_id, num_nodes, b, m):
        self.leader_id  = leader_id
        self.ballot_num = b
        self.pvalues    = set()
        self.waitfor    = set(range(0, num_nodes))
        self.m          = m
        self.num_nodes  = num_nodes

    def run(self):
        # TODO: for all acceptors send(a, ("p1a", self.node_id, self.ballot_num))
        triple = literal_eval(self.m)
        if (triple[0] == "p1b"):
            if (triple[2] == self.ballot_num):
                for item in triple[3]:
                    self.pvalues.add(item)
                self.waitfor.remove(triple[1])
                if (len(self.waitfor) < num_nodes /2):
                    # TODO: send(leader, ("adopted", self.ballot_num, str(self.pvalues)))
                    self.send_to_server(self.leader_id,
                                        str(("adopted", self.ballot_num, self.pvalues)))
                    os._exit()
            else:
                # TODO: send(leader, ("preempted", str(triple[2])))
                self.send_to_server(self.leader_id, str(("preempted", triple[2])))
                os._exit()


class Commander:
    def __init__(self, leader_id, num_nodes, pvalue, m):
        self.leader_id = leader_id
        self.pvalue = pvalue
        self.ballot_num = pvalue[0]
        self.slot_num   = pvalue[1]
        self.proposal   = pvalue[2]
        self.waitfor = set(range(0, num_nodes))
        self.m = m

    def run(self):
        # TODO: for all acceptors send(a, ("p2a", self.node_id, pvalue))
        triple = literal_eval(self.m)
        if (triple[0] == "p2b"):
            if (self.ballot_num == triple[2]):
                self.waitfor.remove(triple[1])
                if (len(self.waitfor) < num_nodes / 2):
                    # TODO: for all replicas send(p, ("decision", self.slot_num, self.proposal))
                    self.broadcast_to_server("'decision', "+str((self.slot_num, self.proposal)))
                    os._exit()
            else:
                # TODO: send(leader, ("preempted, triple[2]"))
                self.send_to_server(self.leader_id, str(("preempted, triple[2]")))
                os._exit()


class Acceptor:
    def __init__(self, m):
        self.accepted = set()
        self.ballot_num = -1;
        self.m = m

    def run(self):
        triple = literal_eval(self.m)

        if (triple[0] == "p1a"):
            if triple[2] > self.ballot_num:
                self.ballot_num = triple[2]
            # TODO: send(leader, ("p1b", self.node_id, self.ballot_num, self.accepted))
            self.send_to_server(self.leader_id, str(("p1b", self.node_id, self.ballot_num, tuple(self.accepted))))
        elif (triple[0] == "p2a"):
            pvalue = triplep[2]
            if pvalue[0] >= self.ballot_num:
                ballot_num = pvalue[0]
                accepted.add(pvalue)
            # TODO: send(leader, ("p2b, self.node_id, self.ballot_num"))
            self.send_to_server(self.leader_id, str(("p2b", self.node_id, self.ballot_num)))


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    is_leader = cmd[2] == "True"
    num_nodes = int(cmd[3])
    num_clients = int(cmd[4])
    s = Server(node_id, is_leader, num_nodes, num_clients)
    print(s.uid, "started")
    s.t_recv.join()
