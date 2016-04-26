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
from pylab import *

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

	'''
		t =  (etype, esize, wsize, cwsize,
		        stime, etime, r1, r2, r3 ,r4, tid)
	'''
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
	r1 = float(lst[6])
	r2 = r3 = r4 = 0.0
	tid = lst[10]
		
	t =  (etype, esize, wsize, cwsize,
	        stime, etime, r1, r2, r3 ,r4, tid, eid)		
		
	buf.append(t) # Not buf += t
	buflen += 1;

def cdf(arr, fname):
	m = {}
	mx = max(arr)
	l = len(arr)
	fl = float(l)
	
	''' 
		Divide the array into buckets 
		or calculate histogram !
	'''
	# np.histogram
	for v in arr:
		# Ugly hack to draw a graph for 2mrw
		if v != mx:
			if v not in m:
				m[v] = 0
			m[v] = m[v] + 1

	skeys = sorted(m.keys())
	
	X = [x for x in skeys]
	Y = np.cumsum([100*float(m[x])/fl for x in skeys])

	''' 
		State machine interface 
		Consider using OO interface later
	'''
	# xticks(np.arange(0.0, 200, 5.0))
	# yticks(np.arange(0.0, 120.0, 5.0))
	ylabel('Percentage')
	xlabel('Epoch sizes in terms of 64B cache-lines')
	title('CDF of epoch sizes (' + fname + ')')
	plot(X,Y)
	
	''' Automate this saving ''' 
	fig = gcf()
	fig.set_size_inches(24,12.75)
	''' Graphs are saved in png/ in eliza '''
	savefig('png/' + os.path.basename(fname).split('.')[0] + '.png', format='png', dpi=100)

	
def analyze():

	''' get 95-th percentile epoch size '''
	global buf
	global buflen
	global tfile
	''' Stats are saved in stat/ in eliza '''
	fname = 'stat/' + os.path.basename(tfile.split('.')[0]) + '_' + str(time.strftime("%d%b%H%M%S")).lower()  + '.stat'

	'''
		t =  ((0) etype, (1) esize, (2) wsize, (3) cwsize,
		        (4) stime, (5) etime, (6) r1, (7) r2, (8) r3 ,(9) r4, 
		        (10) tid)
	'''

	tt = [t[2] for t in buf]
	cdf(tt, fname)

	a = np.array(tt)
	a = a[a != 0.0]
	p95 = np.percentile(a, 95)
	p99 = np.percentile(a, 99)
	p5  = np.percentile(a, 5)
	med = np.median(a)
	avg_s = np.mean(a)
	max_sz = np.amax(a)
	min_sz = np.amin(a) # amino
	tot = buflen
	nlpcnt = float(tnull)/float(buflen) * 100
		
	''' get avg duration in secs '''
	d = np.array([t[5]-t[4] for t in buf])
	avg_d = np.mean(d)
		
	''' get 95-th percentile page span '''
	psa = np.array([t[6] for t in buf])
	psa95 = np.percentile(psa, 95)
	max_psa = np.amax(psa)
	
	tid_m = {}
	for t in buf:
		tid_m[t[10]] = 0
	

	print "Stat file :", fname
	f = open(fname, 'w')
	if f is not None :
		''' Better way of reporting stats ? '''
		f.write("Trace file        : "  + str(tfile) + "\n")
		f.write("Total epochs      : "  + str("{:,}".format(buflen)) + "\n")
		f.write("Total null epochs : "  + str("{:,}".format(tnull)) + " (" + str(nlpcnt) + "%)\n")
		f.write("Total threads     : "  + str(len(tid_m)) + "\n")
		f.write("Average duration  : "  + str(avg_d) + " secs \n")
		f.write("5-tile epoch size : "  + str(p5)    + "\n")
		f.write("95-tile epoch size: "  + str(p95)   + "\n")
		f.write("99-tile epoch size: "  + str(p99)   + "\n")
		f.write("Median epoch size : "  + str(med) + "\n")
		f.write("95-tile page span : "  + str(psa95)   + "\n")
		f.write("Max page span     : "  + str(max_psa)   + "\n")
		f.write("Average epoch sz  : "  + str(avg_s) + "\n")
		f.write("Max epoch size    : "  + str(max_sz) + "\n")
		f.write("Min epoch size    : "  + str(min_sz) + "\n")
		f.write("\n* All epoch sizes are in terms of 64B cache blocks \n")		
		f.close()
	cmd = 'cat ' + fname
	os.system(cmd)


for i in range(0,w):
	cq = '/dev/shm/.' + str(os.path.basename(tfile.split('.')[0])) + '_' + str(i) + '.q'
	f = open(cq, 'r')
	csvr = csv.reader(f)
	for row in csvr:
		insert(row)
	f.close()
		
analyze()
