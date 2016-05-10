import gzip
import time
import os
import sys
import subprocess
import errno
import csv
import argparse
import traceback
import gc
import bisect
import numpy as np
import ConfigParser
import matplotlib.pyplot as plt
from pylab import *
from os import listdir
from os.path import isfile, join
from multiprocessing import Pool, TimeoutError, Process, Queue, Lock
from ep_stats import ep_stats


ttypes = (['ftrace', 'utrace'])
debugl = [1,2,3,4]

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-d', dest='debug', default = 0, help="Debug levels", choices=debugl)
parser.add_argument('-r', dest='logdir', help="Log directory containing per-thread epoch logs")
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")

try:
	args = parser.parse_args()
except:
	# parser.exit(status=0, message=parser.print_help())
	sys.exit(0)

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

wpid = -1
lmaps = [] # list of maps 
est = None
lookback_t = 0.005 # 5 ms
lookback_map = {} # filename, another map = {lno,line in that file}

def make_index(logdir, f):
	global lmaps
	''' 
		We could have one giant index for all epochs in the env
		indexed using their start times. But then concurrent epochs
		from two different guest threads with the same start time will 
		contend for a space in the index and I am not sure how python
		handles such contention - chaining, or what ? I am assuming only
		one of the contending epochs gets to reside in the index and this can
		make me miss some dependencies. It doesn't matter if there are plenty
		of dependencies already and missing one or two doesn't matter. But at 
		this point we don't know so to be safe we will not have one index
		for all epochs in the env but one index per guest thread.
	'''
	# print "Worker " + str(wpid) + " Indexing : ", logdir + '/' + f
	fd = open(logdir + '/' + f, 'r')
	
	lno = 0
	__lmap = [] # A member of lmap
	for l in fd:
		lno += 1
		try:
			epstr = l.split(';')[2] # this may fail due to out-range index, hence "try"
			stime = est.get_stime_from_str(epstr)
			etime = est.get_etime_from_str(epstr)
			__lmap.append((stime, etime, lno))
		except:
			continue

	lmaps.append((f, __lmap)) # a thread log with an index on epochs
		#if wpid == 2:
		#	print lno, epstr
		# print f, lno
	
def cal_cross_thd_dep(pid, args):

	logdir = args[0]
	logfile = args[1]
	global wpid
	global est
	global lookback_t
	global lookback_map
	wpid = pid
	est = ep_stats()
	print "Worker " + str(wpid) + " analyzing " + logfile
	'''
		Launch a process for each file, which is a thread log with
		the filename and logdir as argument
		
		Laucn a maximum of four processes
		
		Have each process index all files except the one passed to it as argument
		
		I will write the later algo later
	'''

	# print logdir, logfile
	onlyfiles = [f for f in listdir(logdir) if isfile(join(logdir, f)) and 'txt' in f and f != logfile]
	
	for f in onlyfiles:
		make_index(logdir, f)
		
		lookback_map[f] = {}
		thd_log_map = lookback_map[f]
		thd_log_fp = open(logdir + f, 'r')
		for __lno, ep_str in enumerate(thd_log_fp):
			thd_log_map[__lno] = ep_str.split(';')[1]
		thd_log_fp.close()


	''' Core analysis begins here ''' 
	fd = open(logdir + '/' + logfile, 'r')
	for l in fd:
		''' 
			For each epoch in the curr thread,
			look for a competing epoch anywhere in the env
		'''
		
		try:
			epstr = l.split(';')[2] # this may fail due to out-range index
			stime = est.get_stime_from_str(epstr)
			etime = est.get_etime_from_str(epstr)
		except:
			continue
		
		comp_ep = [] # A list of competing epochs for one guest thread
		for (f,__lmap) in lmaps:
			pos = bisect.bisect_left(__lmap, (stime,))
			if pos != 0:
				# pos -= 1
				try:
					while __lmap[pos][1] > stime and pos != 0:
						pos -= 1 # Use an interval map
				except:
					# print pos, "premature exit. its ok. the EOF has been reached"
					sys.exit(0)
					
				__stime,__etime,lno = __lmap[pos]
				''' 
					If the time line of a thread goes frm
					left to right, __stime is the start time of 
					the most recent epoch any where in the system
				'''
				assert __etime <= stime # Assertion 1
				
				''' Making sure that __stime is within some time interval '''
				if __stime >= stime - lookback_t:
					# if stime - lookback <= __stime and __etime <= stime:

					pos_lb = bisect.bisect_left(__lmap, (stime - lookback_t,))
					__stime_lb,__etime_lb,lno_lb = __lmap[pos_lb]
					assert __stime_lb >= stime - lookback_t # Assertion 2
					'''
					if __stime_lb >= stime:
						print ">>>>",__stime_lb, stime, wpid, logfile
						sys.exit(0)
					'''
					assert __stime_lb <= stime
					
					# Assertion 1 and 2 are extremely important
					# if stime - lookback <= __stime_lb and __etime_lb <= stime:
					# comp_ep.append((f, lno, lno_lb, __stime, __etime, __stime_lb, __etime_lb))
					comp_ep.append((f, lno_lb, lno, __stime_lb, __etime))
					# No where am I checking for the end time ! Trouble ? Dunno 
					# Remember, if you are wrong, it is not hard to plug in an
					# interval tree

		
		# This is "if" condition is for debugging
		# Otherwise the code below it can be used
		if wpid == 0:
			if len(comp_ep) > 0:
				# assert len(comp_ep) % 2 == 0
				
				ep_addr_str = l.split(';')[1]
				head = "head -n "
				tail = "tail -n "
				egrep = "egrep "
				keys = ep_addr_str.split(',')
				# TODO : comment out

				print str(stime-lookback_t) + '-' + str(stime), keys
				for t in comp_ep:
					# TODO : comment out

					print "Concur", str(t)
					thd_log_fname = t[0] # f
					assert thd_log_fname in lookback_map
					thd_log_map = lookback_map[thd_log_fname]	
					start_lno = int(t[1]) #lno_lb
					end_lno = int(t[2]) #lno
					assert end_lno >= start_lno
					assert start_lno in thd_log_map
					assert end_lno in thd_log_map

					# if you want to reduce memory footprint then don't assume
					# the lines are already present, read them in selectively
					__lno = start_lno
					while __lno <= end_lno:
						for ep_addr in keys:
							if ep_addr in thd_log_map[__lno]:								
								print "Deps", str(t), ep_addr
							else:
								a = 1
						__lno += 1
					assert __lno - 1 == end_lno
						
					''' Shell util - Takes too much time
					# assert end_lno > start_lno
					diff = end_lno - start_lno
					
					cmd = head + str(end_lno) + " " + thd_log + " | " + tail + str(diff) + " | " + egrep + "\"" + keys + "\""
					print cmd
					os.system(cmd)
					'''
					
					''' python code also takes too long
					tlog_fp = open(thd_log, 'r')
			
					for __lno, ep_str in enumerate(tlog_fp):
						if start_lno <= __lno:
							if __lno <= end_lno:
								a = 0
							else:
								break
					
					tlog_fp.close()
					'''

			

datadir = '/dev/shm/'
colmap = {}
colmap['etype'] = 0
colmap['epoch_esize'] = 1
colmap['epoch_wsize'] = 2
colmap['epoch_cwsize'] = 3
colmap['epoch_duration'] = 4
colmap['epoch_page_span'] = 6
colmap['epoch_dist_from_mrd'] = 7
colmap['epoch_dist_from_lrd'] = 8
marker = ['ro-', 'bs-', 'g^-', 'kD-']
plain  =   ['r-', 'b-', 'g-', 'k-']
logdir = '/dev/shm/' + args.logdir
cfg = ConfigParser.ConfigParser()
cfg.read('data.ini')

onlyfiles = [f for f in listdir(logdir) if isfile(join(logdir, f)) and '.txt' in f]
pmap = {}
pid = 0
max_pid = 8

for logfile in onlyfiles:
	'''
		Launch a process for each file, which is a thread log with
		the filename and logdir as argument
		
		Laucn a maximum of four processes
		
		Have each process index all files except the one passed to it as argument
		
		I will write the later algo later
	'''

	pmap[pid] = Process(target=cal_cross_thd_dep, args=(pid, [logdir, logfile]))
	pmap[pid].start()
	print "Parent started worker ", pid
	pid += 1;
	
	if pid == max_pid:
		print "Max number of processes reached"
		for pid,p in pmap.items():
			print "Parent waiting for worker", pid
			p.join()
		
		pid = 0
	else:
		continue

	
	
'''
for graph in cfg.sections():
	
	print "\nPlotting " + str(graph)

	optval = {}
	for option in cfg.options(graph):
		optval[option] = cfg.get(graph, option)

	if optval['graph_type'] == 'cdf':

		plt.clf()
		plt.xlabel(str(optval['xlabel']))
		plt.ylabel(str(optval['ylabel']))
		plt.title(str(optval['heading']))
		plt.grid(True)
		gname = 'png/' + graph + '.png'		
		
		if optval['values'] in colmap:
			col = colmap[optval['values']]
		else:
			print "value for config option 'values' unsupported"
			sys.exit(0)
		
		styles = marker
		if 'marker' in optval:
			if optval['marker'] == 'False':
				styles = plain
			else:
				print "value for config option 'marker' unsupported"
				sys.exit(0)
		n_si = len(styles)
		

		si = -1
		for fn in optval['data_files'].split(','):			
			si += 1
			buf = []
			buflen = 0				
			try:
				fd = open(datadir + fn, 'r')
			except:
				print "cannot open " + datadir + fn
				sys.exit(0)				

			csvfd = csv.reader(fd)
			for row in csvfd:
				insert(buf, buflen, row, col)			
			fd.close()
			print "Done reading " + str(fn)

			# Eliminate zeros
			buf = filter(lambda i: i > 0, buf)
			plot_cdf(buf,styles[si%n_si], int(optval['xcut']), int(optval['ycut']), fn.split('-')[0])

		
		plt.legend(loc='lower right')
		plt.savefig(gname, format='png', dpi=100)

	else:
		print "value for config option 'graph_type' unsupported"
		sys.exit(0)
'''
