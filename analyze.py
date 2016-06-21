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
import ConfigParser
import matplotlib.pyplot as plt
from pylab import *
from os import listdir
from os.path import isfile, join

ttypes = (['ftrace', 'utrace'])
debugl = ['1','2','3','4']

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-p', '--print', dest='pt', action='store_true', default=False, help="Print trace")
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")
parser.add_argument('-r', dest='logdir', help="Log directory containing per-thread epoch logs and summary")

datadir = '/scratch/'
try:
	args = parser.parse_args()
except:
	parser.exit(status=0, message=parser.print_help())
	sys.exit(0)

logdir = datadir + args.logdir
only_csv_files = [f for f in listdir(logdir) if isfile(join(logdir, f)) and '.csv' in f]
assert len(only_csv_files) == 1
summary = logdir + '/' + only_csv_files[0]
'''
for i in range(0,w):
	cq = '/dev/shm/.' + str(os.path.basename(tfile.split('.')[0])) + '_' + str(i) + '.q'
	f = open(cq, 'r')
	csvr = csv.reader(f)
	for row in csvr:
		insert(row)
	f.close()
'''		
		
'''
		t =  ((0) etype, (1) esize, (2) wsize, (3) cwsize,
		        (4) stime, (5) etime, (6) r1, (7) r2, (8) r3 ,(9) r4, 
		        (10) tid)
		r1 = page_span t[6]
		r2 = min dist between dep epochs t[7]
		r3 = max dist between dep epochs t[8]

		def cdf(arr, fname, xaxis, heading, content)

'''
def plot_cdf(arr, style, xcut, ycut, lbl):
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
		if v not in m:
			m[v] = 0
		m[v] = m[v] + 1

	skeys = sorted(m.keys())
	
	X = [x for x in skeys]
	Y = np.cumsum([100*float(m[x])/fl for x in skeys])
	
	A = []
	B = []

	for i in range(0, len(X)-1):
		if X[i] < xcut and Y[i] < ycut:
			A.append(X[i])
			B.append(Y[i])
	
	X = A
	Y = B

	''' 
		State machine interface 
		Consider using OO interface later
	'''
	# xticks(np.arange(0.0, 200, 5.0))
	# yticks(np.arange(0.0, 120.0, 5.0))
	plt.plot(X,Y, style, label=lbl)

def insert(buf, buflen, row, col):
	
	'''
		t =  ((0) etype, (1) esize, (2) wsize, (3) cwsize,
		        (4) stime, (5) etime, (6) r1, (7) r2, (8) r3 ,(9) r4, 
		        (10) tid)
	'''
			
	buf.append(float(row[col])) # Not buf += t
	buflen += 1;

def cdf(arr, fname, xaxis, heading, content, clear):
	if clear == 1:
		clf()
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
		# if v != mx:
		if True is True:
			if v not in m:
				m[v] = 0
			m[v] = m[v] + 1

	skeys = sorted(m.keys())
	
	X = [x for x in skeys]
	Y = np.cumsum([100*float(m[x])/fl for x in skeys])
	
	A = []
	B = []
	for i in range(0, len(X)):
		if Y[i] < 99.5:
			A.append(X[i])
			B.append(Y[i])
	
	X = A
	Y = B

	''' 
		State machine interface 
		Consider using OO interface later
	'''
	# xticks(np.arange(0.0, 200, 5.0))
	# yticks(np.arange(0.0, 120.0, 5.0))
	ylabel('Percentage')
	xlabel(xaxis)
	title(heading + ' (' + fname + ')')
	plot(X,Y)
	
	''' Automate this saving ''' 
	fig = gcf()
	fig.set_size_inches(24,12.75)
	''' Graphs are saved in png/ in eliza '''
	gname = 'png/' + os.path.basename(fname).split('.')[0] + '-' + content + '.png'
	savefig(gname, format='png', dpi=100)

	
def analyze():

	global summary
	fname = summary

	'''
		t =  ((0) etype, (1) esize, (2) wsize, (3) cwsize,
		        (4) stime, (5) etime, (6) r1, (7) r2, (8) r3 ,(9) r4, 
		        (10) tid)
		r1 = page_span t[6]
		r2 = min dist between dep epochs t[7]
		r3 = max dist between dep epochs t[8]

		def cdf(arr, fname, xaxis, heading, content)

	'''
	sz_map = {}
	count = 0
	with open(fname, 'r') as fp:
		for te in fp:
			tl = te.split(',')
			sz = float(tl[2])
			if sz in sz_map:
				sz_map[sz] += 1
			else:
				sz_map[sz] = 1
				
			count += 1
			if (count % 1000000) == 0:
				print "Completed 1,000,000 rows"

		print "Epoch sizes		Abs.freq.		Rel. freq."
		print "==========================================="
		for sz in sorted(sz_map.keys()):
			abs_fq = sz_map[sz]
			rel_fq = float(round(100*abs_fq/count,2))
			print sz,"		",abs_fq,"		", rel_fq
		

analyze()
