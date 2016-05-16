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
import numpypy as np
import ConfigParser
import intervaltree as it
# import matplotlib.pyplot as plt
# from pylab import *
from os import listdir
from os.path import isfile, join
from multiprocessing import Pool, TimeoutError, Process, Queue, Lock
from ep_stats import ep_stats

debugl = [1,2,3,4]

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-d', dest='debug', default = 0, help="Debug levels", choices=debugl)
parser.add_argument('-r', dest='logdir', help="Log directory containing per-thread epoch logs")
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")

try:
	args = parser.parse_args()
except:
	sys.exit(0)

wpid = -1 # Worker pid
est = None
lookback_time = 0.000001 # 1 us
#lookback_time = 0.000005 # 5 us
lookback_time = 0.00005  # 50 us
#lookback_time = 0.0005   # 500 us
#lookback_time = 0.005    # 5000 us
# Keep the two separate so that you can collectively read in lines later
# if the files are too big
f_to_epochs_stime_m = {}
f_to_epochs_etime_m = {}
f_to_lnnums_m = {}

def make_index_by_etime(logdir, f):
	global f_to_epochs_etime_m
	f2e = []
	with open(logdir + '/' + f, 'r') as fp:
		for lno,l in enumerate(fp):
			try:
				# this may fail due to out-range index, hence "try"
				epstr = l.split(';')[2]
				stime = est.get_stime_from_str(epstr)
				etime = est.get_etime_from_str(epstr)
				f2e.append((etime, lno+1))
			except:
				continue
	fp.close()
	f_to_epochs_etime_m[f] = f2e
	
def make_index_by_stime(logdir, f):
	global f_to_epochs_stime_m
	f2e = []
	with open(logdir + '/' + f, 'r') as fp:
		for lno,l in enumerate(fp):
			try:
				# this may fail due to out-range index, hence "try"
				epstr = l.split(';')[2]
				stime = est.get_stime_from_str(epstr)
				etime = est.get_etime_from_str(epstr)
				f2e.append((stime, lno+1))
			except:
				continue
	fp.close()
	f_to_epochs_stime_m[f] = f2e
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
def make_lnmap(logdir, f):
	global f_to_lnnums_m
	lno_to_lines_m = {}
	with open(logdir + '/' + f, 'r') as fp:
		for lno,l in enumerate(fp): # 0 to n - 1
			try:
				tmpl = []
				tmpl.append(l.split(';')[1].split(','))

				epstr = l.split(';')[2]
				stime = est.get_stime_from_str(epstr)
				etime = est.get_etime_from_str(epstr)
				tmpl.append((stime,etime))		
			
				lno_to_lines_m[lno+1] = tmpl
			except:
				continue
	fp.close()
	f_to_lnnums_m[f] = lno_to_lines_m
	
def find_recent_past_ep_stime_helper(f, stime_, stime):
	''' Return all epochs that started between stime_ and stime'''
	f2e   = f_to_epochs_stime_m[f]
	pos_  = bisect.bisect_left(f2e, (stime_,))
	pos   = bisect.bisect_left(f2e, (stime,))

	if pos > pos_:
		st1,sno = f2e[pos_]
		st2,eno = f2e[pos-1] # To avoid index-out-of-range error
		assert stime_ <= st1 and st1 <= stime
		assert stime_ <= st2 and st2 <= stime
		assert sno <= eno
		return (sno,eno,st1,st2)
		# iterate from eno to sno
	return None

def find_recent_past_ep_etime_helper(f, stime_, stime):
	''' Return all epochs that ended between stime_ and stime'''
	f2e   = f_to_epochs_etime_m[f]
	pos_  = bisect.bisect_left(f2e, (stime_,))
	pos   = bisect.bisect_left(f2e, (stime,))

	if pos > pos_:
		et1,sno = f2e[pos_]
		et2,eno = f2e[pos-1] # To avoid index-out-of-range error
		assert stime_ <= et1 and et1 <= stime
		assert stime_ <= et2 and et2 <= stime
		assert sno <= eno
		return (sno,eno,et1,et2)
		# iterate from eno to sno
	return None

def find_recent_past_ep(f, stime_, stime):
	t = find_recent_past_ep_stime_helper(f, stime_, stime)
	if t is not None:
		sno_st, eno_st, st1, st2 = t
	else:
		return t
		
	t = find_recent_past_ep_etime_helper(f, stime_, stime)
	if t is not None:
		sno_et, eno_et, et1, et2 = t
	else:
		return t

	s1 = set(range(sno_st, eno_st + 1))
	s2 = set(range(sno_et, eno_et + 1))
	s3 = s1.intersection(s2)
	if len(s3) > 0:
		sno = max(sno_st, sno_et)
		eno = min(eno_st, eno_et)
		assert sno in s3
		assert eno in s3
		return (sno,eno)
	else:
		return None
	
def cal_cross_thd_dep(pid, args):

	logdir = args[0]
	logfile = args[1]
	recently_touched_addr = {}
	global wpid
	global est
	global lookback_time
	global f_to_lnnums_m
	global f_to_epochs_m
	wpid = pid
	#if wpid != 2:
	#	sys.exit(0)
	est = ep_stats()
	print "Worker " + str(wpid) + " analyzing " + logfile

	onlyfiles = [f for f in listdir(logdir) if isfile(join(logdir, f)) and 'txt' in f]
	
	for f in onlyfiles:
		make_index_by_stime(logdir, f)
		make_index_by_etime(logdir, f)
		make_lnmap(logdir, f)

	print "''' Core analysis begins here '''"
	with open(logdir + '/' + logfile, 'r') as fp:
		fo = open("deps-" + logfile, 'w')
		for lno,l in enumerate(fp):
			try:
				ep_addr  = l.split(';')[1].split(',')
				ep_summ  = l.split(';')[2] # this may fail due to out-range index
				stime    = est.get_stime_from_str(ep_summ)
				etime    = est.get_etime_from_str(ep_summ)
			except:
				continue

			#print '>>>>',lno+1,stime - lookback_time, stime, ep_addr
			''' find the most-recent-owner '''
			for f in onlyfiles:

				t = find_recent_past_ep(f, stime - lookback_time, stime)
				if t is not None:
					sno = t[0]
					eno = t[1]
					if f == logfile:
						assert eno < lno + 1
					
					'''
						We're finding all epochs in (X - t) secs identified
						by line number (lno) in a per-thread log where each line
						is one epoch. The asserts check if the epoch is really
						in the interval (X - t) secs.
					'''
					# print sno,'-',eno, f_to_lnnums_m[f][sno][1][0], f_to_lnnums_m[f][eno][1][1],f
					# start and end times of left  most epoch falling in the interval (X - t) secs
					assert stime - lookback_time <= f_to_lnnums_m[f][sno][1][0] and f_to_lnnums_m[f][sno][1][1] <= stime
					# start and end times of right most epoch falling in the interval (X - t) secs
					assert stime - lookback_time <= f_to_lnnums_m[f][eno][1][0] and f_to_lnnums_m[f][eno][1][1] <= stime	
					
					for ln in range(sno, eno + 1):
						l_addr = f_to_lnnums_m[f][ln][0]
						tmstmp = f_to_lnnums_m[f][ln][1]
						for addr in l_addr:
							if addr not in recently_touched_addr:
								recently_touched_addr[addr] = (tmstmp[0], tmstmp[1], f, ln)
							else:
								if (tmstmp[0], tmstmp[1], f, ln) > recently_touched_addr[addr]:
									recently_touched_addr[addr] = (tmstmp[0], tmstmp[1], f, ln)
			''' 
				What we've done so far is form a list of NVM addresses
				dirtied by all threads in the last 100 micro-seconds.
				This list also identifies the last epoch to dirty the addr.
			'''
			
			nprint = 0
			for ea in ep_addr:
				if ea in recently_touched_addr:
					# Asserting that the starting time of last owning epoch is within (X - t) secs
					b0 = (stime - lookback_time <= recently_touched_addr[ea][0] and recently_touched_addr[ea][0] <= stime)
					# Asserting that the ending time of last owning epoch is within (X - t) secs
					b1 = (stime - lookback_time <= recently_touched_addr[ea][1] and recently_touched_addr[ea][1] <= stime)
					if not (b0 and b1):
						continue
						
					ownership = "deadbeef"
					if logfile != recently_touched_addr[ea][2]:
						ownership = "cross_thread"
					else:
						ownership = "self_thread"
					
					if nprint == 0:
						print '>>>>',lno+1,stime - lookback_time, stime, ep_addr
						nprint = 1
						
					print ownership, ea, recently_touched_addr[ea]
			
			'''
				What we've done so far is to list self- and cross- thread
				dependencies in the last X usecs using a cache of NVM addresses
				that is updated for each epoch and keeps track of the most
				recent owner epoch. Then we simply check this cache for the most
				recent owner epoch in a different SMT context !
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
