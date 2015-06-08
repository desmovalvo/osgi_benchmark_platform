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
# - multiplier (the number of subscriptions progressively increased up to sub_block_size * multiplier)
# - subscriptions block size


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
chart_filename = "test2_" + d + ".svg"
csv_filename = "test2_" + d + ".csv"
text_filename = "test2_" + d + ".txt"

# read command line arguments
try: 
    opts, args = getopt.getopt(sys.argv[1:], "o:r:i:b:m:s:", ["osib=", "rsib=", "iterations=", "block_size=", "multiplier=", "sub_block_size="])
    for opt, arg in opts:
        if opt in ("-o", "--osib"):
            osib_ip = arg.split(":")[0]
            osib_port = int(arg.split(":")[1])
            print colored("init> ", "blue", attrs=['bold']) + "Setting ip and port of OSGi SIB to " + str(arg)
        if opt in ("-r", "--rsib"):
            rsib_ip = arg.split(":")[0]
            rsib_port = int(arg.split(":")[1])
            print colored("init> ", "blue", attrs=['bold']) + "Setting ip and port of RedSIB to " + str(arg)
        elif opt in ("-i", "--iterations"):
            iterations = int(arg)
            print colored("init> ", "blue", attrs=['bold']) + "Setting iterations to " + str(arg)
        elif opt in ("-b", "--block_size"):
            block_size = int(arg)
            print colored("init> ", "blue", attrs=['bold']) + "Setting block size to " + str(arg)
        elif opt in ("-m", "--multiplier"):
            multiplier = int(arg)
            print colored("init> ", "blue", attrs=['bold']) + "Setting multiplier to " + str(arg)
        elif opt in ("-s", "--sub_block_size"):
            sub_block_size = int(arg)
            print colored("init> ", "blue", attrs=['bold']) + "Setting sub block size to " + str(arg)
        
except getopt.GetoptError:
    print colored("init> ", "red", attrs=["bold"]) + "Usage: python test2.py -o osib_ip:port -r rsib_ip:port -i iterations -b block_size -m multiplier -n nsubs -q subscription"
    sys.exit()

# instantiate a KP
conn_ok = False
while not conn_ok:
    try:
        kp_list = []
        print colored("init> ", "blue", attrs=["bold"]) + "connecting to the SIBs"
        kp_list.append(m3_kp_api(False, osib_ip, osib_port, "OSGi"))
        kp_list.append(m3_kp_api(False, rsib_ip, rsib_port, "RedSIB"))
        conn_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=["bold"]) + e.__str__()
        print colored("init> ", "red", attrs=["bold"]) + "Retrying in a while..."

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
    
        # generate the triple list
        print colored("pre-test> ", "blue", attrs=["bold"]) + "Generating a triple list with %s elements" % (str(block_size * (m+1)))
        triple_list = []
        for k in range(block_size):
            triple_list.append(Triple(URI(ns + str(k)), URI(ns + str(k)), Literal(k)))
    
        # results
        res = []
    
        # iterate
        for iteration in range(iterations):
    
            # sleep
            time.sleep(1)
    
            # subscribe
            sub_list = []
            print colored("pre-test> ", "blue", attrs=["bold"]) + "Subscribing to %s triples" % (str(sub_block_size * (m+1)))
            for k in range(sub_block_size * (m+1)):
                sub_list.append(kp.load_subscribe_RDF(Triple(URI(ns + "NOT" + str(k)), URI(ns + str(k)), Literal(k)), THandler()))

            # sleep
            time.sleep(1)

            # insert
            try:
                print colored("test> ", "blue", attrs=["bold"]) + "Insertion in progress (%s triples) - iteration %s" % (str(len(triple_list)), str(iteration))
                elapsed_time = timeit.timeit(lambda: kp.load_rdf_insert(triple_list), number = 1)
            except:
                print colored("test> ", "red", attrs=["bold"]) + "Failure during the insertion"

            # sleep
            time.sleep(1)

            # close subscriptions
            print colored("post-test> ", "blue", attrs=["bold"]) + "Closing subscriptions..."
            for s in sub_list:
                kp.load_unsubscribe(s)
    
            # clean the SIB
            print colored("post-test> ", "blue", attrs=["bold"]) + "Cleaning the SIB"
            try:
                kp.load_rdf_remove([Triple(None, None, None)])
                res.append(elapsed_time)
            except:
                print colored("post-test> ", "red", attrs=["bold"]) + "Failure while cleaning the SIB"
                print traceback.print_exc()
            
    
        # elaborate results
        sum = 0
        print res
        for r in range(len(res)):
            sum += elapsed_time
        results[kp.__dict__["theSmartSpace"][0]][(m+1) * sub_block_size] = round(sum / len(res), 3)
    

############################################################
#
# plot and save to csv
#
############################################################

# initialize the csv file
csvfile = open(csv_filename, "w")
csvfile_writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

# initialize the chart
bar_chart = pygal.Bar(style=LightColorizedStyle)
bar_chart.title = """Time to perform an Insert request varying the number of
subscriptions"""

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
