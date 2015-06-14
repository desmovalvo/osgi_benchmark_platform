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
from pu_library import *
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
# initialization
#
############################################################

# defining a namespace
ns = "http://ns#"

# pu
pu_template = """INSERT { ?s <http://ns#nevermind> <http://ns#nevermind%s> } WHERE { ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://ns#Person> }"""

# defining default parameters
osib_ip = "localhost"
osib_port = 7701
block_size = 5
iterations = 5
multiplier = 10
nsubs = 0
sub = None
sub_list = []
d = str(datetime.datetime.now().strftime("%Y%m%d-%H%M"))
chart_filename = "test3_" + d + ".svg"
csv_filename = "test3_" + d + ".csv"
text_filename = "test3_" + d + ".txt"

# read command line arguments
try: 
    opts, args = getopt.getopt(sys.argv[1:], "o:i:b:m:s:", ["osib=", "iterations=", "block_size=", "multiplier=", "sub_block_size="])
    for opt, arg in opts:
        if opt in ("-o", "--osib"):
            osib_ip = arg.split(":")[0]
            osib_port = int(arg.split(":")[1])
            print colored("init> ", "blue", attrs=['bold']) + "Setting ip and port of OSGi SIB to " + str(arg)
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
    print colored("init> ", "red", attrs=["bold"]) + "Usage: python test2.py -o osib_ip:port -i iterations -b block_size -m multiplier -n nsubs -q subscription"
    sys.exit()

# instantiate a KP
conn_ok = False
while not conn_ok:
    try:
        print colored("init> ", "blue", attrs=["bold"]) + "connecting to the SIBs"
        kp = m3_kp_api(False, osib_ip, osib_port, "OSGi")
        conn_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=["bold"]) + e.__str__()
        print colored("init> ", "red", attrs=["bold"]) + "Retrying in a while..."

# clean the SIBs
clean_ok = False
print colored("init> ", "blue", attrs=["bold"]) + "cleaning the SIBs"
while not clean_ok:
    try:
        kp.load_rdf_remove([Triple(None, None, None)])
        clean_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=["bold"]) + e.__str__()
        print colored("init> ", "red", attrs=["bold"]) + "Error while cleaning the SIB, retrying in a while..."
        # time.sleep(3)

# initialize a dictionary with the results
results = {}

# generate the triple list
print colored("pre-test> ", "blue", attrs=["bold"]) + "Generating a triple list with %s elements" % (str(block_size))
triple_list = []
for k in range(block_size):
    triple_list.append(Triple(URI(ns + str(k)), URI(ns + str(k)), Literal(k)))


############################################################
#
# simulation
#
############################################################


# initialize the results for this kp
results[kp.__dict__["theSmartSpace"][0]] = {}

# increase the multiplier
for m in range(multiplier):

    # results
    res = []

    # iterate
    for iteration in range(iterations):

        # sleep
        time.sleep(1)

        # persistent update
        sub_list = []
        print colored("pre-test> ", "blue", attrs=["bold"]) + "Persistent update... %s " % (str(sub_block_size * (m+1)))
        for k in range(sub_block_size * (m+1)):
            # sub_list.append(kp.load_subscribe_RDF(Triple(URI(ns + "NOT" + str(k)), URI(ns + str(k)), Literal(k)), THandler()))
            pu = PU(pu_template % (k), osib_ip, osib_port)
            sub_list.append(pu)
            if not pu.send():
                print colored("test> ", "red", attrs=["bold"]) + "Failure during the persistent update"

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

        # close persistent updates
        print colored("post-test> ", "blue", attrs=["bold"]) + "Closing persistent updates..."
        for pu in sub_list:
            pu.close()

        # clean the SIB
        print colored("post-test> ", "blue", attrs=["bold"]) + "Cleaning the SIB"

        # elaborate results
        if not(m == 0 and iteration == 0):
            try:
                kp.load_rdf_remove([Triple(None, None, None)])
                res.append(elapsed_time * 1000)
            except:
                print colored("post-test> ", "red", attrs=["bold"]) + "Failure while cleaning the SIB"
                print traceback.print_exc()        

    # elaborate results
    sum = 0
    print res
    for r in res:
        sum += r
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
bar_chart = pygal.Bar(style=LightColorizedStyle, range=(0.0, 60.0), x_title="Active subscriptions (n)", y_title="Time (ms)")
bar_chart.title = """Time to insert %s triples 
with n active persistent updates""" % (str(block_size))

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
out_file.write("Number of persistent updates: " + str(nsubs) + "\n")
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
