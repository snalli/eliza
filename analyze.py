import gzip
import time
import os
import sys
import errno
import csv
import argparse
import traceback
import gc
import numpy as np

ttypes = (['ftrace', 'utrace'])
debugl = [1,2,3,4]

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-f', dest='tfile', required=True, help="Gzipped trace file")
parser.add_argument('-y', dest='ttype', help="Type of trace file", choices=ttypes)
parser.add_argument('-d', dest='debug', default = 0, help="Debug levels", choices=debugl)
parser.add_argument('-w', dest='workers', default = 1, help="Number of workers")
parser.add_argument('-b', dest='db', action='store_true', default=False, help="Create database")
parser.add_argument('-o', dest='flow', action='store_true', default=False, help="Get control flow of an epoch")
parser.add_argument('-nz', dest='anlz', action='store_false', default=True, help="Analyze and collect some stats")
parser.add_argument('-p', '--print', dest='pt', action='store_true', default=False, help="Print trace")
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")

try:
	args = parser.parse_args()
except:
	# parser.exit(status=0, message=parser.print_help())
	sys.exit(0)

tfile = args.tfile
w = int(args.workers)
nz = args.anlz
if nz is False:
	sys.exit(0)
buf = []
buflen = 0
tno = 0
tnull = 0

def insert(lst):
	
	global tno
	global buf
	global buflen
	global tnull

	eid = tno
	tno += 1
	etype = str(lst[0])
	if etype == 'null':
		tnull += 1
	esize  = float(lst[1])
	wsize  = float(lst[2])
	cwsize = float(lst[3])
	stime = float(lst[4])
	etime = float(lst[5])
	r1 = r2 = r3 = r4 = 0.0
	tid = lst[10]
		
	t =  (eid, etype, esize, wsize, cwsize,
	        stime, etime, r1, r2, r3 ,r4, tid)		
		
	buf.append(t) # Not buf += t
	buflen += 1;

def analyze():

	''' get 95-th percentile epoch size '''
	global buf
	global buflen
	global tfile
	a = np.array([t[3] for t in buf])
	a = a[a != 0.0]
	p95 = np.percentile(a, 95)
	p5  = np.percentile(a, 5)
	med = np.median(a)
	avg_s = np.mean(a)
	max_sz = np.amax(a)
	min_sz = np.amin(a) # amino
	tot = buflen
		
	''' get avg duration in secs '''
	d = np.array([t[6]-t[5] for t in buf])
	avg_d = np.mean(d)
		
	fname = 'stat/' + os.path.basename(tfile.split('.')[0]) + '.stat'
	f = open(fname, 'w')
	if f is not None :
		''' Better way of reporting stats ? '''
		f.write("DB                : "  + str(fname) + "\n")
		f.write("Total epochs      : "  + str(buflen) + "\n")
		f.write("Total null epochs : "  + str(tnull) + "\n")
		f.write("Average duration  : "  + str(avg_d) + " secs \n")
		f.write("95-tile epoch size: "  + str(p95)   + "\n")
		f.write("5-tile epoch size : "  + str(p5)    + "\n")
		f.write("Median epoch size : "  + str(med) + "\n")
		f.write("Average epoch sz  : "  + str(avg_s) + "\n")
		f.write("Max epoch size    : "  + str(max_sz) + "\n")
		f.write("Min epoch size    : "  + str(min_sz) + "\n")
		
		f.close()


for i in range(0,w):
	cq = '/dev/shm/.' + str(os.path.basename(tfile.split('.')[0])) + '_' + str(i) + '.q'
	f = open(cq, 'r')
	csvr = csv.reader(f)
	for row in csvr:
		insert(row)
	f.close()
		
analyze()
