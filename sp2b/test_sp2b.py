#!/usr/bin/python

# requirements
import csv
import sys
import time
import pygal
import timeit
import getopt
import rdflib
import datetime
import traceback
from queries import *
from termcolor import *
from smart_m3.m3_kp_api import *


# initialization
osib_ip = "localhost"
osib_port = 10111
rsib_ip = "localhost"
rsib_port = 10010
iterations = 5
n3file = "sp2b.n3"
d = str(datetime.datetime.now().strftime("%Y%m%d-%H%M"))
chart_filename = "testSP2B_" + d + ".svg"
text_filename = "testSP2B_" + d + ".txt"
csv_filename = "testSP2B_" + d + ".csv"

# read command line parameters
try: 
    opts, args = getopt.getopt(sys.argv[1:], "o:r:i:n:", ["osib=", "rsib=", "iterations=", "n3file="])
    for opt, arg in opts:
        if opt in ("-o", "--osib"):
            osib_ip = arg.split(":")[0]
            osib_port = int(arg.split(":")[1])
        if opt in ("-r", "--rsib"):
            rsib_ip = arg.split(":")[0]
            rsib_port = int(arg.split(":")[1])
        elif opt in ("-i", "--iterations"):
            iterations = int(arg)
        elif opt in ("-n", "--n3file"):
            n3file = arg

except getopt.GetoptError:
    print colored("init> ", "red", attrs=["bold"]) + "Usage: python test2.py -o osib_ip:port -r rsib_ip:port -i iterations --n3file=n3file"
    sys.exit()


# connect to the SIBs
kp_list = []
conn_ok = False
while not conn_ok:
    try:
        print colored("init> ", "blue", attrs=['bold']) + "Connecting to the SIBs"
        kp_list.append(m3_kp_api(False, osib_ip, osib_port, "OSGi SIB"))
        kp_list.append(m3_kp_api(False, rsib_ip, rsib_port, "RedSIB"))
        conn_ok = True
    except Exception as e:
        print colored("init> ", "red", attrs=['bold']) + e.__str__()
        print colored("init> ", "red", attrs=['bold']) + "Retrying connection in a while..."


# extract triples from the n3 file
print colored("init> ", "blue", attrs=['bold']) + "Extracting triples from n3 file...",
g = rdflib.Graph()
res = g.parse(n3file, format='n3')
print "Done!"

# clean both the SIBs
for kp in kp_list:
    kp.load_rdf_remove([Triple(None, None, None)])

# insert the triples on both the SIBs
print colored("init> ", "blue", attrs=['bold']) + "Starting the insertion"
counter = 0
triple_list = []
for triple in res:

    s = []
    for t in triple:

        if type(t).__name__  == "URIRef":
            s.append( URI(t.toPython()) )
            
        elif type(t).__name__  == "Literal":
            s.append( Literal(t.toPython()) )

        elif type(t).__name__  == "BNode":
            s.append( bNode(t.toPython()) )

    ins_ok = False
    if len(s) == 3:
        counter += 1
        triple_list.append(Triple(s[0], s[1], s[2]))
        if counter % 100 == 0:            
            while ins_ok != True:
                try:
                    for kp in kp_list:
                        kp.load_rdf_insert(triple_list)                    
                    ins_ok = True
                    triple_list = []
                    print colored("init> ", "blue", attrs=["bold"]) + "Insertion of triple " + str(counter) + " completed"
                except:
                    print traceback.print_exc()
                    print colored("init> ", "red", attrs=['bold']) + e.__str__()
                    print colored("init> ", "red", attrs=['bold']) + "Retrying insert in a while..."
                    time.sleep(3)            

while ins_ok != True:
    try:
        for kp in kp_list:
            kp.load_rdf_insert(triple_list)                    
        ins_ok = True
        triple_list = []
        print colored("init> ", "blue", attrs=["bold"]) + "Insertion of triple " + str(counter) + " completed"
    except:
        print traceback.print_exc()
        print colored("init> ", "red", attrs=['bold']) + e.__str__()
        print colored("init> ", "red", attrs=['bold']) + "Retrying insert in a while..."
        time.sleep(3)            


# check about the number of triples
for kp in kp_list:
    kp.load_query_rdf(Triple(None, None, None))
    r = kp.result_rdf_query
    print colored("init> ", "blue", attrs=["bold"]) + "%s contains %s triples" % (kp.__dict__["theSmartSpace"][0], str(len(r)))
    if len(r) < counter:
        print colored("init> ", "blue", attrs=["bold"]) + "%s contains less than %s triples" % (kp.__dict__["theSmartSpace"][0], counter)
        sys.exit()
    

# iterate over kps
results = {}
for kp in kp_list:
    
    # iterate over queries
    results[kp.__dict__["theSmartSpace"][0]] = {}
    for q in queries:

        # iterate over iterations
        print colored("test> ", "blue", attrs=["bold"]) + "Query %s on kp %s" % (str(queries.index(q)), str(kp.__dict__["theSmartSpace"][0]))
        result = []
        for i in range(iterations):

            # perform the queries
            try:
                elapsed_time = timeit.timeit(lambda: kp.load_query_sparql(q), number = 1)
                result.append(elapsed_time)
                if i == 0:
                    print len(kp.result_sparql_query)
            except Exception as e:
                print colored("test> ", "red", attrs=["bold"]) + e.__str__()
            
        # elaborate the result
        sum = 0
        for r in result:
            sum += r
        results[kp.__dict__["theSmartSpace"][0]][queries.index(q)] = round(sum / len(result), 2)


# initialize a chart
bar_chart = pygal.Bar()
bar_chart.title = """Time to perform the SP2B benchmark queries"""

# initialize a csv file
csvfile = open(csv_filename, "w")
csvfile_writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

# iterate over results to plot a graph and save to csv file
for kp in results.keys():

    labels = []
    bars = []

    for k in sorted(results[kp].keys()):
        
        # debug output
        print colored("post-test> ", "blue", attrs=["bold"]) +  "[%s] query %s: %s ms" % (kp, str(k), str(results[kp][k]))

        # add data to the graph
        bars.append(results[kp][k])
        labels.append(str(k))

        # add data to csv file
        csvfile_writer.writerow([kp,k,results[kp][k]])

    bar_chart.add(kp, bars)
    bar_chart.x_labels = labels

# finalize the chart
bar_chart.render_to_file(chart_filename)

# finalize the csv file
csvfile.close()

# writing test information on a file
out_file = open(text_filename, "w")
out_file.write("Total triples: " + str(counter) + "\n")
out_file.write("Iterations: " + str(iterations) + "\n")
out_file.close()
