#!/usr/bin/python

# requirements
import random
import socket
from smart_m3.m3_kp_api import *

# PERSISTENT UPDATE TEMPLATE
pu_template = """<SSAP_message>
	<transaction_type>PERSISTENT_UPDATE</transaction_type>
	<message_type>REQUEST</message_type>
	<transaction_id>%s</transaction_id>
	<node_id>%s</node_id>
	<space_id>%s</space_id>
	<parameter name = "query" encoding = "SPARQL-UPDATE">%s</parameter>
	<parameter name = "confirm">TRUE</parameter>
</SSAP_message>"""

unpu_template = """<SSAP_message>
	<transaction_type>CANCEL_PERSISTENT_UPDATE</transaction_type>
	<message_type>REQUEST</message_type>
	<transaction_id>%s</transaction_id>
	<node_id>%s</node_id>
	<space_id>%s</space_id>
	<parameter name = "update_id">%s</parameter>
</SSAP_message>"""

class PU:

    def __init__(self, sparql, sib_ip, sib_port):

        # connection parameters
        self.sib_ip = sib_ip
        self.sib_port = sib_port

        # join
        self.kp = m3_kp_api(False, sib_ip, sib_port)

        # request parameters
        self.kp_id = self.kp.__dict__["theNode"].__dict__["node_id"]
        self.transaction_id = random.randint(1, 1000)
        self.space_id = "X"
        self.pu_id = None

        # sanitize sparql
        sparql = sparql.replace("<", "&lt;").replace(">", "&gt;")

        # create request message
        self.pu_request_msg = pu_template % (self.transaction_id, self.kp_id, self.space_id, sparql)
        

    def send(self):
        
        # open connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.sib_ip, int(self.sib_port)))

        # send message
        s.send(self.pu_request_msg)

        # wait for a reply
        reply_msg = s.recv(4096)

        # close connection
        s.close()

        # parse the reply
        if "m3:Success" in reply_msg:      
            self.pu_id = reply_msg[reply_msg.index('update_id">')+11: reply_msg.index('update_id">')+47]
            return True
        else:
            return False
            

    def close(self):
        
        # open connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.sib_ip, int(self.sib_port)))

        # build the message
        unpu_request_msg = unpu_template % (random.randint(1, 1000), self.kp_id, self.space_id, self.pu_id)

        # send message
        s.send(self.pu_request_msg)

        # wait for a reply
        reply_msg = s.recv(4096)

        # close connection
        s.close()

        # parse the reply
        if "m3:Success" in reply_msg:            
            return True
        else:
            return False
