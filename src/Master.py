#! /usr/bin/python3

import fileinput
import subprocess

if __name__ == "__main__":
    nodes, clients, = [], []
    num_nodes, num_clients = 0, 0
    for line in fileinput.input():
        line = line.split();
        if line[0] == 'start':
            num_nodes = int(line[1])
            num_clients = int(line[2])
            """ start up the right number of nodes and clients, and store the 
                connections to them for sending further commands """
            for i in range(num_clients):
                p = subprocess.Popen(["./client.py", str(i),str(num_nodes)])
                clients.append(p.pid)
                print("client pid:", p.pid)
            for i in range(num_nodes):
                p = subprocess.Popen(["./node.py", str(i), 
                                      str(True) if i == 0 else str(False),
                                      str(num_nodes)])
                nodes.append(p.pid)
                print("server pid:", p.pid)
        if line[0] == 'sendMessage':
            client_index = int(line[1])
            message = ''.join(str(item) for item in line[2::])
            """ Instruct the client specified by client_index to send the message
                to the proper paxos node """
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
            if (node_index < len(nodes)):
                if nodes[node_index] != None:
                    nodes[node_index] = None
                    os.kill(nodes[node_index])
                else:
                    print(line[1], "has been killed")
            else:
                print(line[1], "is out of bound")
        if line[0] == 'restartServer':
            node_index = int(line[1])
            """ Restart the server specified by node_index """
            if node_index < len(nodes):
                if nodes[node_index] == None:
                    p = subprocess.Popen(["./node.py", line[1], str(False),
                                          len(nodes)])
                    nodes[node_index] = p.pid
                else:
                    print(line[1], "is alive")
            else:
                print(line[1], "is out of bound")
        if line[0] == 'timeBombLeader':
            num_messages = int(line[1])
            """ Instruct the leader to crash after sending the number of paxos
                related messages specified by num_messages """

