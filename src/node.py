#!/usr/bin/python

import threading

from threading import Thread, Lock

class Server:

    '''
    @id: [0 .. num_servers-1].
    @is_leader is set to `True` when creating Server0, otherwise, to `False`.
    @num_servers is used to identify the broadcast range.
    @uid is used for printing the messages.
    @current_leader is updated when receiving heartbeat from the leader.
    Every server is a replica.
    '''
    def __int__(self, id, is_leader, total_num):
        self.id = id
        self.uid = "Server[" + str(id) + "]"
        self.num_servers = total_num

        # Leaders
        self.is_leader = is_leader
        self.current_leader = -1

class Scout:
    def __init__(self, leader_id, num_servers, b):
        self.leader_id = leader_id
        self.ballot_num = b
        self.pvalues = None
        self.waitfor = set(range(0, num_servers))

class Commander:
    def __init__(self, leader_id, num_servers, pvalue):
        self.leader_id = leader_id
        self.pvalue = pvalue
        self.ballot_num = pvalue[0]
        self.slot_num   = pvalue[1]
        self.proposal   = pvalue[2]
        self.waitfor = set(range(0, num_servers))

class Acceptor:

class Client:

    '''
    @uid is used for printing the messages.
    '''
    def __int__(self, id):
        self.id = id
        self.uid = "Client[" + str(id) + "]"
