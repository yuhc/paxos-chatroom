#! /usr/bin/python3

import fileinput
import subprocess, sys, os, signal, time
from threading import Thread, Lock

from network import Network

SLEEP_TIME = 5
PAUSE_TIME = 0.5
CLEAR_TIME = 10

if __name__ == "__main__":
    uid = "Master#0"

    # network controller
    nt = Network(uid)
    def receive():
        global nt
        global leader_id
        while 1:
            buf = nt.receive()
            if len(buf) > 0:
                print(uid, "handles", buf)

    try:
        t_recv = Thread(target=receive)
        t_recv.daemon = True
        t_recv.start()
    except:
        print(uid, "error: unable to start new thread")

    nodes, clients, = [], []
    num_nodes, num_clients = 0, 0
    for line in fileinput.input():
        print("#", line.strip())
        line = line.split();

        if line[0] == 'start':
            num_nodes = int(line[1])
            num_clients = int(line[2])
            nt.set_num_nodes(num_nodes)
            nt.set_num_clients(num_clients)
            """ start up the right number of nodes and clients, and store the
                connections to them for sending further commands """
            for i in range(num_clients):
                p = subprocess.Popen(["./client.py",
                                      str(i),
                                      str(num_nodes)])
                clients.append(p.pid)
                print("Client#", i, " pid:", p.pid, sep="")
            for i in range(num_nodes):
                p = subprocess.Popen(["./node.py",
                                      str(i),
                                      str(True) if i == 0 else str(False),
                                      str(num_nodes), str(num_clients)])
                nodes.append(p.pid)
                leader_id = 0
                print("Server#", i, " pid:", p.pid, sep="")
            time.sleep(SLEEP_TIME) # ensure the establish of sockets

        if line[0] == 'sendMessage':
            client_index = int(line[1])
            message = ''.join(str(item) for item in line[2::])
            """ Instruct the client specified by client_index to send the message
                to the proper paxos node """
            nt.send_to_client(client_index, str(("sendMessage", message)))

        if line[0] == 'printChatLog':
            client_index = int(line[1])
            """ Print out the client specified by client_index's chat history
                in the format described on the handout """
            nt.send_to_client(client_index, str(("printChatLog", 0)))
            time.sleep(PAUSE_TIME) # ensure the log has been printed

        if line[0] == 'allClear':
            """ Ensure that this blocks until all messages that are going to
                come to consensus in PAXOS do, and that all clients have heard
                of them """
            nt.broadcast_to_client(str(("allClear", 0)))
            time.sleep(CLEAR_TIME)

        if line[0] == 'crashServer':
            node_index = int(line[1])
            """ Immediately crash the server specified by node_index """
            if node_index in range(num_nodes):
                if nodes[node_index] != None:
                    os.kill(nodes[node_index], signal.SIGKILL)
                    nodes[node_index] = None
                else:
                    print("Server#", line[1], " has been killed", sep="")
            else:
                print(line[1], "is out of bound")

        if line[0] == 'restartServer':
            node_index = int(line[1])
            """ Restart the server specified by node_index """
            if node_index in range(num_nodes):
                if nodes[node_index] == None:
                    p = subprocess.Popen(["./node.py",
                                          line[1],
                                          str(False),
                                          str(len(nodes)), str(len(clients))])
                    nodes[node_index] = p.pid
                    print("Server#", node_index, " pid:", p.pid, sep="")
                else:
                    print("Server#", line[1], " is alive", sep="")
            else:
                print("Parameter <", line[1], "> is out of bound", sep="")
                time.sleep(SLEEP_TIME) # ensure the establish of sockets

        if line[0] == 'timeBombLeader':
            num_messages = int(line[1])
            """ Instruct the leader to crash after sending the number of paxos
                related messages specified by num_messages """
            nt.broadcast_to_server(str(("timeBombLeader", line[1])))


    # kill the remained nodes and clients
    time.sleep(10)
    for i in range(num_nodes):
        if nodes[i] != None:
            os.kill(nodes[i], signal.SIGKILL)
            print("Server#", i, " stopped", sep="")
    for i in range(num_clients):
        if clients[i] != None:
            os.kill(clients[i], signal.SIGKILL)
            print("Client#", i, " stopped", sep="")
    sys.exit()
