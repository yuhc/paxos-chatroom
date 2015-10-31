#! /usr/bin/python3

import fileinput
import subprocess, sys, os, signal, time

from network import Network

SLEEP_TIME = 5
uid = "Master#0"
counter = 0 # number of ack needed to be received from clients

def receive(self):
    while 1:
        buf = nt.receive()
        if len(buf) > 0:
            print(buf)
            if buf == "messageHasBeenLogged":
                counter = counter - 1


if __name__ == "__main__":
    # network controller
    nt = Network(uid)
    try:
        t_recv = Thread(target=receive)
        t_recv.start()
    except:
        print(uid, "error: unable to start new thread")

    nodes, clients, = [], []
    num_nodes, num_clients = 0, 0
    for line in fileinput.input():
        print("#", line.strip())
        line = line.split();
        # wait all sendMessage be handled
        while line[0] != "sendMessage" and counter > 0:
            time.sleep(0.1)

        if line[0] == 'start':
            num_nodes = int(line[1])
            num_clients = int(line[2])
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
                                      str(num_nodes)])
                nodes.append(p.pid)
                print("Server#", i, " pid:", p.pid, sep="")
            time.sleep(SLEEP_TIME) # ensure the establish of sockets

        if line[0] == 'sendMessage':
            client_index = int(line[1])
            message = ''.join(str(item) for item in line[2::])
            """ Instruct the client specified by client_index to send the message
                to the proper paxos node """
            nt.send_to_client(client_index, "sendMessage " + message)
            counter = counter + 1

        if line[0] == 'printChatLog':
            client_index = int(line[1])
            """ Print out the client specified by client_index's chat history
                in the format described on the handout """

        if line[0] == 'allClear':
            """ Ensure that this blocks until all messages that are going to
                come to consensus in PAXOS do, and that all clients have heard
                of them """

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
                                          len(nodes)])
                    nodes[node_index] = p.pid
                    print("Server#", i, " pid:", p.pid, sep="")
                else:
                    print("Server#", line[1], " is alive", sep="")
            else:
                print("Parameter <", line[1], "> is out of bound", sep="")
                time.sleep(SLEEP_TIME) # ensure the establish of sockets

        if line[0] == 'timeBombLeader':
            num_messages = int(line[1])
            """ Instruct the leader to crash after sending the number of paxos
                related messages specified by num_messages """


    # kill the remained nodes and clients
    for i in range(num_nodes):
        if nodes[i] != None:
            os.kill(nodes[i], signal.SIGKILL)
            print("Server#", i, " stopped", sep="")
    for i in range(num_clients):
        if clients[i] != None:
            os.kill(clients[i], signal.SIGKILL)
            print("Client#", i, " stopped", sep="")
