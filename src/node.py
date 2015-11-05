#!/usr/bin/python3

import threading, sys, itertools, os, time

from threading import Thread, Lock
from ast       import literal_eval

from network   import Network

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
            self.leader = Leader(node_id, self.num_nodes)
            print(self.uid, "is leader")
        self.current_leader = -1 # updated when receiving leader's heartbeat
                                 # remember to update replica.leader_id and leader
        self.view_num = 0 # the id of candidate leader

        # Replicas
        max_faulty = (num_nodes - 1) / 2 # f in the paper
        if (node_id <= max_faulty):
            # f+1  servers are replicas
            # 2f+1 (all)  servers are acceptors
            self.is_replica = True
            self.replica = Replica(node_id, self.nt)
        else:
            self.is_replica = False
        self.acceptor = Acceptor(self.node_id, self.nt)

        # TODO: leader broadcasts heartbeat
        self.rev_heartbeat = True # whether receive heartbeat in current period
        if is_leader:
            time.sleep(2) # wait for other servers to start
            self.broadcast_heartbeat()
        self.check_heartbeat()


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
                # TODO: handle the received value
                message = list(literal_eval(buf))

                # to replica
                if (message[0] in ['request', 'decision']):
                    self.replica_operation(message)
                # to leader
                if (message[0] in ['propose', 'adopted', 'preempted']):
                    self.leader_operation(message)
                # to scout
                if (message[0] == "p1b"):
                    self.scout_operation(message)
                # to commander
                if (message[0] == "p2b"):
                    self.commander_operation(message)
                # to acceptor
                if (message[0] in ['p1a', 'p2a']):
                    self.acceptor_operation(message)
                # to server
                if (message[0] == "heartbeat"):
                    self.receive_heartbeat(message)
                if (message[0] == "election"):
                    self.broadcast_to_server("'heartbeat', "+str(self.node_id))
                if (message[0] == "timeBombLeader"):
                    if (self.is_leader):
                        self.nt.set_remain_message(int(message[1]))

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

    def scout_operation(self, message):
        # p1b from acceptor: ['p1b', sender_id, ballot_num, accepted]
        self.scout.process_message(message)

    def commander_operation(self, message):
        # p2b from acceptor: ['p2b', sender_id, ballot_num]
        self.commander.process_message(message)

    def acceptor_operation(self, message):
        # request from scout: ['p1a', (sender_id, scout_id), ballot_num]
        if message[0] == 'p1a':
            self.acceptor.process_p1a(message)
        # request from commander:
        # ['p2a', (sender_id, commander_id), (ballot_num, slot_num, proposal)]
        elif message[0] == 'p2a':
            self.acceptor.process_p2a(message)


    def broadcast_heartbeat(self):
        if self.is_leader: # others may be elected
            self.broadcast_to_server("'heartbeat', "
                                     + str(self.node_id))
            threading.Timer(self.TIME_HEARTBEAT,
                            self.broadcast_heartbeat).start()

    def receive_heartbeat(self, message):
        # heartbeat from leader: ['heartbeat', leader_id]
        self.rev_heartbeat = True
        print(self.uid, "receive heartbeat from", message[1])

        candidate = int(message[1])
        if (self.current_leader < 0) or \
           (self.is_leader and candidate < self.node_id):
            self.current_leader = candidate
            self.view_num = candidate
            if self.current_leader != self.node_id:
                self.is_leader = False
                self.nt.set_remain_message()
            else:
                self.is_leader = True
                try:
                    self.leader
                except:
                    self.leader = Leader(self.node_id)
                print(self.uid, "starts heartbeat")
                self.broadcast_heartbeat()
            if self.is_replica:
                self.replica.set_leader(candidate)
            print(self.uid, " updates Server#", candidate, " as leader", sep="")

    '''
    Starts leader election whenever the leader's heartbeat
    timeouts.
    '''
    def check_heartbeat(self):
        if (not self.is_leader) and (not self.rev_heartbeat):
            # TODO: leader election
            print(self.uid, " starts election Server#",
                  self.view_num, sep="")
            self.current_leader = -1
            self.view_num = (self.view_num + 1) % self.num_nodes
            self.send_to_server(self.view_num,
                                "'election', "+str(self.view_num))
        self.rev_heartbeat = False
        threading.Timer(self.TIME_HEARTBEAT, self.check_heartbeat).start()


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
            self.nt.send_to_server(self.leader_id,
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
            self.nt.broadcast_to_client(p[0], str(("response", p[1], "Done")))

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
    def __init__(self, node_id, num_nodes):
        self.node_id    = node_id
        self.num_nodes  = num_nodes
        self.active     = False
        self.proposals  = set()
        self.ballot_num = 0
        self.commander_map = {}
        self.scout_map = {}
        self.commander_number = 0
        self.scout_number = 0
        self.scout_map[self.scout_number] = Scout(self.node_id, self.num_nodes,
                                                  self.ballot_num,
                                                  self.scout_number)
        self.scout_number = self.scout_number + 1

    def check_slot(sn):
        for (ss, pp) in self.proposals:
            if (sn == ss):
                return True
        return False

    def pmax():


    def process_message(self, m):
        triple = literal_eval(m)
        if (triple[0] == "propose"):
            if (not check_slot(triple[1][0])):
                proposals.add(triple[1])
                if (active):
                    self.commander_map[commander_numnber] =
                    Commander(self.node_id, self.num_nodes,
                              (self.ballot_num, triple[1][0], triple[1][1]),
                              self.commander_id)
                    self.commander_id = self.commander_id + 1
        elif (triple[0] == "adopted"):



class Scout:
    def __init__(self, leader_id, num_nodes, b, scout_id):
        self.leader_id  = leader_id
        self.ballot_num = b
        self.pvalues    = set()
        self.waitfor    = set(range(0, num_nodes))
        self.num_nodes  = num_nodes # number of acceptors
        self.nt         = nt
        self.scout_id   = scout_id
        # for all acceptors send ("p1a", self.scout_id, self.ballot_num) to a
        self.nt.broadcast_to_server(str("p1a", self.scout_id, self.ballot_num))


    def process_message(self, m):
        triple = literal_eval(m)
        if (triple[0] == "p1b"):
            if (triple[2] == self.ballot_num):
                for item in triple[3]:
                    self.pvalues.add(item)
                self.waitfor.remove(triple[1])
                if (len(self.waitfor) < num_nodes /2):
                    # send ("adopted", self.ballot_num, tuple(self.pvalues)) to leader
                    self.send_to_server(self.leader_id,
                                        str(("adopted", self.ballot_num, tuple(self.pvalues))))
            else:
                # send ("preempted", triple[2]) to leader
                self.nt.send_to_server(self.leader_id, str(("preempted", triple[2])))


class Commander:
    def __init__(self, leader_id, num_nodes, pvalue, commander_id):
        self.leader_id    = leader_id
        self.pvalue       = pvalue
        self.ballot_num   = pvalue[0]
        self.slot_num     = pvalue[1]
        self.proposal     = pvalue[2]
        self.waitfor      = set(range(0, num_nodes))
        self.nt           = nt
        self.commander_id = commander_id
        # for all acceptors send ("p2a", self.commander_id, pvalue) to a
        self.nt.broadcast_to_server(str(("p2a", self.commander_id, self.pvalue)))

    def process_message(self, m):
        triple = literal_eval(self.m)
        if (triple[0] == "p2b"):
            if (self.ballot_num == triple[2]):
                self.waitfor.remove(triple[1])
                if (len(self.waitfor) < num_nodes / 2):
                    # send 'decision', (self.slot_num, self.proposal) to all replicas
                    self.nt.broadcast_to_server("'decision', "+str((self.slot_num, self.proposal)))
            else:
                # send ("preempted, triple[2]") to leader
                self.nt.send_to_server(self.leader_id, str(("preempted", triple[2])))


class Acceptor:
    def __init__(self, node_id, nt):
        self.accepted   = set()
        self.ballot_num = -1
        self.node_id    = node_id
        self.nt         = nt

    ''' Process the request from scout.
        Message format: ['p1a', (sender_id, scout_id), ballot_num] '''
    def process_p1a(self, message):
        (sender_id, scout_id) = message[1]
        b = message[2]
        if b > self.ballot_num:
            self.ballot_num = b
        # send ('p1b', (self.node_id, scout_id), self.ballot_num, self.accepted)
        # to the corresponding leader
        self.nt.send_to_server(sender_id, str(("p1b", (self.node_id, scout_id),
            self.ballot_num, tuple(self.accepted)))

    ''' Process the request from commander.
        Message format: ['p2a', (sender_id, commander_id),
                         (ballot_num, slot_num, proposal)] '''
    def process_p2a(self, message):
        (sender_id, commander_id) = message[1]
        pvalue = message[2]
        b = pvalue[0]
        if b >= self.ballot_num:
            ballot_num = b
            self.accepted.add(pvalue)
        # send ("p2b, self.node_id, self.ballot_num") to leader
        self.nt.send_to_server(sender_id,
            str(("p2b", (self.node_id, commander_id), self.ballot_num)))


if __name__ == "__main__":
    cmd = sys.argv
    node_id = int(cmd[1])
    is_leader = cmd[2] == "True"
    num_nodes = int(cmd[3])
    num_clients = int(cmd[4])
    s = Server(node_id, is_leader, num_nodes, num_clients)
    print(s.uid, "started")
    s.t_recv.join()
