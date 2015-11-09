#! /usr/bin/python3

import fileinput
import subprocess, sys, os, signal, time
from threading import Thread, Lock

from network   import Network
from ast       import literal_eval

TERM_LOG   = True
CMD_LOG    = True
CLEAR_TIME = 2

if __name__ == "__main__":
    uid = "Master#0"
    waitfor_clear   = set()
    waitfor_server  = set()
    waitfor_leader  = False
    waitfor_chatlog = False
    nodes, clients, = [], []
    num_nodes, num_clients = 0, 0

    # network controller
    nt = Network(uid)
    def receive():
        global nt
        global waitfor_clear
        global waitfor_leader
        global waitfor_chatlog
        global waitfor_server
        global waitfor_leader_resp
        global nodes
        while 1:
            buf = nt.receive()
            if len(buf) > 0:
                if TERM_LOG:
                    print(uid, "handles", buf)
                buf = literal_eval(buf)
                if buf[0] == 'allCleared':
                    waitfor_clear.remove(buf[1])

                if buf[0] == 'leaderAlive':
                    waitfor_leader_resp = False

                if buf[0] == 'leaderElected':
                    waitfor_leader = False
                    waitfor_leader_resp = False

                if buf[0] == 'leaderBombed':
                    waitfor_leader = True
                    nodes[buf[1]] = None

                if buf[0] == 'chatLog':
                    print(buf[1])
                    waitfor_chatlog = False

                if buf[0] == 'serverStarted':
                    waitfor_server.remove(buf[1])


    try:
        t_recv = Thread(target=receive)
        t_recv.daemon = True
        t_recv.start()
    except:
        print(uid, "error: unable to start new thread")

    for line in fileinput.input():
        if (TERM_LOG or CMD_LOG) and line.strip():
            print("#", line.strip())
        line = line.split();

        # ensure the election of new leader
        while waitfor_leader:
            pass

        if not line:
            break
        if line[0] == 'start':
            num_nodes = int(line[1])
            num_clients = int(line[2])
            nt.set_num_nodes(num_nodes)
            nt.set_num_clients(num_clients)
            """ start up the right number of nodes and clients, and store the
                connections to them for sending further commands """
            for i in range(num_clients):
                p = subprocess.Popen(["./src/client.py",
                                      str(i),
                                      str(num_nodes)])
                clients.append(p.pid)
                if TERM_LOG:
                    print("Client#", i, " pid:", p.pid, sep="")
            waitfor_server = set(range(num_nodes))
            for i in range(num_nodes):
                p = subprocess.Popen(["./src/node.py",
                                      str(i),
                                      str(True) if i == 0 else str(False),
                                      str(num_nodes), str(num_clients),
                                      str(False)])
                nodes.append(p.pid)
                leader_id = 0
                if TERM_LOG:
                    print("Server#", i, " pid:", p.pid, sep="")
            # ensure the establish of sockets
            while waitfor_server:
                pass

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
            waitfor_chatlog = True
            nt.send_to_client(client_index, str(("printChatLog", 0)))
            # ensure the log has been printed
            while waitfor_chatlog:
                pass

        if line[0] == 'allClear':
            """ Ensure that this blocks until all messages that are going to
                come to consensus in PAXOS do, and that all clients have heard
                of them """
            waitfor_clear = set(range(num_clients))
            waitfor_leader_resp = True
            nt.broadcast_to_client(str(("allClear", 0)))
            nt.broadcast_to_server(str(("leaderAlive", 0)))
            while waitfor_clear or waitfor_leader_resp:
                if TERM_LOG:
                    time.sleep(CLEAR_TIME)
                    print(uid, "waits for allClear")
                pass

        if line[0] == 'crashServer':
            node_index = int(line[1])
            """ Immediately crash the server specified by node_index """
            if node_index in range(num_nodes):
                if nodes[node_index] != None:
                    os.kill(nodes[node_index], signal.SIGKILL)
                    nodes[node_index] = None
                else:
                    if TERM_LOG:
                        print("Server#", line[1], " has been killed", sep="")
            else:
                if TERM_LOG:
                    print(line[1], "is out of bound")

        if line[0] == 'restartServer':
            node_index = int(line[1])
            """ Restart the server specified by node_index """

            if node_index in range(num_nodes):
                if nodes[node_index] == None:
                    waitfor_server = {node_index}
                    p = subprocess.Popen(["./src/node.py",
                                          line[1],
                                          str(False),
                                          str(len(nodes)), str(len(clients)),
                                          str(True)])
                    nodes[node_index] = p.pid
                    if TERM_LOG:
                        print("Server#", node_index, " pid:", p.pid, sep="")
                else:
                    if TERM_LOG:
                        print("Server#", line[1], " is alive", sep="")
            else:
                if TERM_LOG:
                    print("Parameter <", line[1], "> is out of bound", sep="")

            # ensure the establish of sockets
            while waitfor_server:
                pass

        if line[0] == 'timeBombLeader':
            num_messages = int(line[1])
            """ Instruct the leader to crash after sending the number of paxos
                related messages specified by num_messages """
            nt.broadcast_to_server(str(("timeBombLeader", line[1])))


    # kill the remained nodes and clients
    for i in range(num_nodes):
        if nodes[i] != None:
            os.kill(nodes[i], signal.SIGKILL)
            if TERM_LOG:
                print("Server#", i, " stopped", sep="")
    for i in range(num_clients):
        if clients[i] != None:
            os.kill(clients[i], signal.SIGKILL)
            if TERM_LOG:
                print("Client#", i, " stopped", sep="")
    sys.exit()
