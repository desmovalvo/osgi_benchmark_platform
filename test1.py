#!/usr/bin/python

# requirements
import csv
import sys
import time
import pygal
import getopt
import timeit
import datetime
import traceback
from termcolor import *
from smart_m3.m3_kp_api import *
from pygal.style import LightColorizedStyle

# parameters
# - sib ip:port
# - iterations
# - block size (in triples)
# - multiplier (the block size is progressively increased up to block_size * multiplier)
# - number of active subscriptions
# - SPARQL subscription (None if the previous parameter is 0)


############################################################
#
# Subscription handler
#
############################################################

# Handler class
class THandler:

    # handle - empty method
    def handle(self, added, removed):
        pass


############################################################
#
# initialization
#
############################################################

# defining a namespace
ns = "http://ns#"

# defining default parameters
osib_ip = "localhost"
osib_port = 7701
rsib_ip = "localhost"
rsib_port = 10010
block_size = 5
iterations = 5
multiplier = 10
nsubs = 0
sub = None
sub_list = []
d = str(datetime.datetime.now().strftime("%Y%m%d-%H%M"))

# filenames
chart_filename = "test1_" + d + ".svg"
csv_filename = "test1_" + d + ".csv"
text_filename = "test1_" + d + ".txt"

# read command line arguments
try: 
    opts, args = getopt.getopt(sys.argv[1:], "o:r:i:b:m:n:q:", ["osib=", "rsib=", "iterations=", "block_size=", "multiplier=", "nsubs=", "sub="])
    for opt, arg in opts:
        if opt in ("-o", "--osib"):
            osib_ip = arg.split(":")[0]
            osib_port = int(arg.split(":")[1])
        if opt in ("-r", "--rsib"):
            rsib_ip = arg.split(":")[0]
            rsib_port = int(arg.split(":")[1])
        elif opt in ("-i", "--iterations"):
            iterations = int(arg)
        elif opt in ("-b", "--block_size"):
            block_size = int(arg)
        elif opt in ("-m", "--multiplier"):
            multiplier = int(arg)
        elif opt in ("-n", "--nsubs"):
            nsubs = int(arg)
        elif opt in ("-q", "--sub"):
            sub = arg

except getopt.GetoptError:
    print colored("init> ", "red", attrs=["bold"]) + "Usage: python test1.py -o osib_ip:port -r rsib_ip:port -i iterations -b block_size -m multiplier -n nsubs -q subscription"
    sys.exit()

# instantiate the KPs
kp_list = []
conn_ok = False
while not conn_ok:
    try:
        print colored("init> ", "blue", attrs=["bold"]) + "connecting to the SIBs"
        kp_list.append(m3_kp_api(False, osib_ip, osib_port, "OSGi"))
        kp_list.append(m3_kp_api(False, rsib_ip, rsib_port, "RedSIB"))
        conn_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=["bold"]) + e.__str__()
        print colored("init> ", "red", attrs=["bold"]) + "Error during connection, retrying in a while..."
        # time.sleep(3)

# clean the SIBs
clean_ok = False
print colored("init> ", "blue", attrs=["bold"]) + "cleaning the SIBs"
while not clean_ok:
    try:
        for kp in kp_list:
            kp.load_rdf_remove([Triple(None, None, None)])
        clean_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=["bold"]) + e.__str__()
        print colored("init> ", "red", attrs=["bold"]) + "Error while cleaning the SIB, retrying in a while..."
        # time.sleep(3)


# initialize a dictionary with the results
results = {}


############################################################
#
# simulation
#
############################################################

# iterate over the kps
for kp in kp_list:

    # initialize the results for this kp
    results[kp.__dict__["theSmartSpace"][0]] = {}

    # increase the multiplier
    for m in range(multiplier):
    
        # subscribe
        for subscription in range(nsubs):
            s.append(kp.load_subscription_sparql(sub, THandler))
    
        # generate the triple list
        print colored("pre-test> ", "blue", attrs=["bold"]) + "Generating a triple list with %s elements" % (str(block_size * (m+1)))
        triple_list = []
        for k in range(block_size * (m+1)):
            triple_list.append(Triple(URI(ns + "k"), URI(ns + "k"), Literal(k)))
    
        # results
        res = []
    
        # iterate
        for iteration in range(iterations):
    
            # debug info    
            print colored("test> ", "blue", attrs=["bold"]) + "Insertion in progress - iteration %s" % (str(iteration))
    
            # sleep
            # time.sleep(1)

            # insert
            try:
                elapsed_time = timeit.timeit(lambda: kp.load_rdf_insert(triple_list), number = 1)
            except:
                print colored("test> ", "red", attrs=["bold"]) + "Failure during the insertion"
    
            # clean the SIB
            print colored("post-test> ", "blue", attrs=["bold"]) + "Cleaning the SIB"
            try:
                kp.load_rdf_remove([Triple(None, None, None)])
                res.append(elapsed_time * 1000)
            except:
                print colored("post-test> ", "red", attrs=["bold"]) + "Failure while cleaning the SIB"
                print traceback.print_exc()
    
            # close subscriptions
            print colored("post-test> ", "green", attrs=["bold"]) + "Closing subscriptions..."
            for s in sub_list:
                kp.load_unsubscribe(s)
    
        # elaborate results
        sum = 0
        for r in res:
            sum += r
        results[kp.__dict__["theSmartSpace"][0]][(m+1) * block_size] = round(sum / len(res), 3)

print results    

############################################################
#
# plot and save to csv
#
############################################################

# initialize the csv file
csvfile = open(csv_filename, "w")
csvfile_writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

# initialize the chart
bar_chart = pygal.Bar(style=LightColorizedStyle, x_title="Block size (n)", y_title="Time (ms)")
bar_chart.title = """Time to insert n triples (%s active subscriptions)""" % (nsubs)

# draw the chart and fill the csv file
for kp in results.keys():
    labels = []
    bars = []
    for k in sorted(results[kp].keys()):

        # add data to the graph
        bars.append(results[kp][k])
        labels.append(str(k))

        # format of the csv file: kp, num_triples, time
        csvfile_writer.writerow([kp,k,results[kp][k]])

    bar_chart.add(kp, bars)
    bar_chart.x_labels = labels
bar_chart.render_to_file(chart_filename)


############################################################
#    
# Save test details to file
#
############################################################

# write on the file
out_file = open(text_filename, "w")
out_file.write("Number of subscriptions: " + str(nsubs) + "\n")
out_file.write("Subscriptions to: " + str(sub) + "\n")
out_file.write("Multiplier: " + str(multiplier) + "\n")
out_file.write("Block size: " + str(block_size) + "\n")
out_file.write("Iterations: " + str(iterations) + "\n")
out_file.close()


############################################################
#    
# EOT
#
############################################################

print colored("post-test> ", "green", attrs=["bold"]) + "Test ended"
