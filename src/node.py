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

        # acceptor
        # acceptor must be started first
        self.acceptor = Acceptor(self.node_id, self.nt)

        # Leaders
        self.is_leader = is_leader
        if is_leader:
            time.sleep(2) # wait for other servers to start
            self.leader = Leader(node_id, self.num_nodes, self.nt)
            self.leader.init_scout()
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

        # TODO: leader broadcasts heartbeat
        self.rev_heartbeat = True # whether receive heartbeat in current period
        if is_leader:
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
                    self.leader.scout_operation(message)
                # to commander
                if (message[0] == "p2b"):
                    self.leader.commander_operation(message)
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
        # proposal from replica: ['propose', (slot_num, proposal)]
        if message[0] == 'propose':
            self.leader.process_propose(message)
        # adoption from scout: ['adopted', ballot_num, pvalue]
        elif message[0] == 'adopted':
            self.leader.process_adopted(message)
        # preemption from commander: ['preempted', ballot]
        elif message[0] == 'preempted':
            self.leader.process_preempted(message)

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
                    self.leader = Leader(self.node_id, self.num_nodes, self.nt)
                    self.leader.init_scout()
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
        # DB: print("Replica#", self.node_id, " sets leader to ", leader_id, sep="")

    def decide(self, decision):
        # dec = (slot_num, proposal)
        self.decisions.add(decision)
        flt1 = list(filter(lambda x: x[0] == self.slot_num, self.decisions))
        while flt1:
            p1 = flt1[0][1]
            flt2 = list(filter(lambda x: x in self.proposals and x[1] != p1,
                               flt1))
            if flt2:
                self.propose(flt2[0][1]) # repropose
            self.perform(p1)
            flt1 = list(filter(lambda x: x[0] == self.slot_num, self.decisions))

    def propose(self, proposal):
        # DB: print("Replica", self.node_id, str(proposal), str(self.decisions))
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
                                str(("propose", (s, proposal))))

    def perform(self, proposal):
        if (self.is_in_set(proposal, self.decisions, True)):
            self.slot_num = self.slot_num + 1
        else:
            self.slot_num = self.slot_num + 1
            # TODO: maybe not necessary to log
            #with open(self.log_name, 'a') as f:
            #    f.write(proposal[3])

            # send `response, (cid, result)` to client
            self.nt.broadcast_to_client(str(("response", proposal[1], "Done")))

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
        return bool(list(flt))


class Leader:
    '''
    @self.node_id:    self()
    @self.ballot_num: initially (0, self())
    @self.active:     initially false
    @self.proposals:  initially empty
    '''
    def __init__(self, node_id, num_nodes, nt):
        self.node_id    = node_id
        self.num_nodes  = num_nodes
        self.active     = False
        self.proposals  = {}
        self.ballot_num = 0
        self.commanders = {}
        self.scouts     = {}
        self.commander_id = 0
        self.scout_id   = 0
        self.nt = nt

    ''' must be splitted from __init__, so that Leader can be created before
        receving any messages like 'p1b' '''
    def init_scout(self):
        self.spawn_scout()

    def spawn_scout(self):
        self.scouts[self.scout_id] = Scout(self.node_id,
                                           self.num_nodes,
                                           self.ballot_num,
                                           self.scout_id, self.nt)
        self.scouts[self.scout_id].init_broadcast()
        self.scout_id = self.scout_id + 1

    def spawn_commander(self, slot_num, proposal):
        self.commanders[self.commander_id] = \
                        Commander(self.node_id, self.num_nodes,
                                  (self.ballot_num, slot_num, proposal),
                                  self.commander_id, self.nt)
        self.commander_id = self.commander_id + 1

    ''' Process proposal from replica.
        Message format: ['propose', (slot_num, proposal)] '''
    def process_propose(self, message):
        (slot_num, proposal) = message[1]
        if not (slot_num in self.proposals):
            self.proposals[slot_num] = message[1]
            if self.active:
                self.spawn_commander(slot_num, proposal)

    def pmax(self, pvals):
        # pvals: (b, s, p)
        result = set()
        if pvals:
            max_pval = max(pvals)

            for pval in pvals:
                if pval[0] == max_pval[0]:
                    set.add((pval[1], pval[2]))
        return result

    ''' Process adopted ballot_num from scout.
        Message format: ['adopted', ballot_num, pvalue].
        pvalue contains (b, s, p). '''
    def process_adopted(self, message):
        max_p = self.pmax(message[2]) # pmax(pvals)
        if max_p:
            for item in max_p:
                self.proposals[item[0]] = item[1]
        for (s, p) in self.proposals:
            self.spawn_commander(s, p)
        self.active = True

    ''' Process preempted ballot_num from Commander.
        Message format: ['preempted', ballot] '''
    def process_preempted(self, message):
        r = message[1]
        if r > self.ballot_num:
            self.active = False
            self.ballot_num = r + 1
            self.spawn_scout()

    def scout_operation(self, message):
        # p1b from acceptor:
        # ['p1b', (sender_id, scout_id), ballot_num, accepted]
        self.scouts[message[1][1]].process_p1b(message)

    def commander_operation(self, message):
        # p2b from acceptor:
        # ['p2b', (sender_id, commander_id), ballot_num]
        self.commanders[message[1][1]].process_p2b(message)


class Scout:
    def __init__(self, leader_id, num_nodes, b, scout_id, nt):
        self.leader_id  = leader_id
        self.ballot_num = b
        self.pvalues    = set()
        self.waitfor    = set(range(0, num_nodes))
        self.num_nodes  = num_nodes # number of acceptors
        self.nt         = nt
        self.scout_id   = scout_id

    ''' must be splitted from __init__ '''
    def init_broadcast(self):
        # send ("p1a", (leader_id, scout_id), self.ballot_num) to all acceptors
        self.nt.broadcast_to_server(str(("p1a", (self.leader_id, self.scout_id),
                                        self.ballot_num)))

    ''' Process p1b message from acceptor.
        Message format: ('p1b', (sender_id, scout_id), ballot_num, accepted) '''
    def process_p1b(self, message):
        sender_id = message[1][0]
        b = message[2] # received ballot_num, b'
        r = message[3] # received accepted pvalues

        if (b == self.ballot_num):
            for item in r:
                self.pvalues.add(item)
            self.waitfor.remove(sender_id)
            if (len(self.waitfor) < num_nodes/2):
                # send ("adopted", ballot_num, tuple(pvalues)) to leader
                self.nt.send_to_server(self.leader_id,
                    str(("adopted", self.ballot_num, tuple(self.pvalues))))
        else:
            # send ("preempted", b') to leader
            self.nt.send_to_server(self.leader_id,
                                   str(("preempted", message[2])))


class Commander:
    def __init__(self, leader_id, num_nodes, pvalue, commander_id, nt):
        self.leader_id    = leader_id
        self.pvalue       = pvalue
        self.ballot_num   = pvalue[0]
        self.slot_num     = pvalue[1]
        self.proposal     = pvalue[2]
        self.waitfor      = set(range(0, num_nodes))
        self.nt           = nt
        self.commander_id = commander_id
        # for all acceptors send ("p2a", self.commander_id, pvalue) to a
        self.nt.broadcast_to_server(str(("p2a", (self.leader_id, self.commander_id), self.pvalue)))

    ''' Process p2b message from acceptor.
        Message format: ('p2b', (sender_id, command_id), ballot_num") '''
    def process_p2b(self, message):
        b = message[2] # received ballot_num, b'
        sender_id = message[1][0]

        if (self.ballot_num == b):
            self.waitfor.remove(sender_id)
            if (len(self.waitfor) < num_nodes/2):
                # send 'decision', (slot_num, proposal) to all replicas
                self.nt.broadcast_to_server(
                    str(("decision", (self.slot_num, self.proposal))))
        else:
            # send ("preempted, b'") to leader
            self.nt.send_to_server(self.leader_id, str(("preempted", b)))


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
            self.ballot_num, tuple(self.accepted))))

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
        # send ("p2b, (self.node_id, command_id), self.ballot_num") to leader
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
