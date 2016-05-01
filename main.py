from ftread import ftread
from utread import utread
from smt import smt
from ep_stats import ep_stats
from multiprocessing import Pool, TimeoutError, Process, Queue, Lock
from multiprocessing.sharedctypes import Value, Array
from ctypes import Structure

import gzip
import time
import os
import subprocess
import sys
import errno
import csv
import argparse
import traceback
import gc

ttypes = (['ftrace', 'utrace'])
verbosity = (['1','2','3','4','5'])
reuse_t = ['1','2']

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-f', dest='tfile', required=True, help="Gzipped trace file")
parser.add_argument('-y', dest='ttype', required=True, help="Type of trace file", choices=ttypes)
parser.add_argument('-w', dest='workers', default = 1, help="Number of workers")
parser.add_argument('-b', dest='db', action='store_true', default=False, help="Create database")
parser.add_argument('-o', dest='flow', action='store_true', default=False, help="Get control flow of an epoch")
parser.add_argument('-nz', dest='anlz', action='store_false', default=True, help="Ignore analysis")
parser.add_argument('-ni', dest='nti', action='store_false', default=True, help="Ignore movnti")
parser.add_argument('-nf', dest='clf', action='store_false', default=True, help="Ignore clflush/clwb")
parser.add_argument('-ns', dest='st', action='store_false', default=True, help="Ignore stores")
parser.add_argument('-nl', dest='ld', action='store_false', default=True, help="Ignore loads")
parser.add_argument('-u', dest='reuse', default= 0, help="Calculate reuse [1 = Inside an epoch, 2 = Inside a thread, 3 = 1 & 2]", choices=reuse_t)
parser.add_argument('-p', '--print', dest='pt', default=0, help="Set verbosity and print trace for debugging (recommended value is 2)", choices=verbosity)
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")

try:
	args = parser.parse_args()
except:
	# parser.exit(status=0, message=parser.print_help())
	sys.exit(0)

# Objectify this
def ping_pong(usrargs, sysargs):
	
	tfile = usrargs.tfile
	gtid = sysargs[0]
	
	cmd = './reuse/reuse 10 ' + str("/dev/shm/." + \
									str(os.path.basename(tfile.split('.')[0])) \
									+ '-' + str(gtid) + '.e')
	print cmd
	# os.system(cmd)

	
def digest(usrargs, sysargs):
	
	args = usrargs
	
	tfile = args.tfile
	ttype = args.ttype
	pt = int(args.pt)
	db = args.db
	flow = args.flow
	anlz = args.anlz
	reuse = int(args.reuse)

	pid   = sysargs[0]
	avoid = sysargs[1]
	BATCH = sysargs[2]	# Worker emits stmt after processing BATCH entries
	n_workers = sysargs[3]
	myq = open(sysargs[4], 'w')
	printl = sysargs[5] # List of host tids you want to examine, for internal use only
	csvq = csv.writer(myq)

	if pt > 0:
		op = open("/dev/shm/" + str(os.path.basename(tfile).split('.')[0]) + '_' + str(pid) + '.t', 'w')	
	if ttype == 'ftrace':
		# tread = ftread(pid, n_workers)
		tread = ftread(usrargs, sysargs)
	elif ttype == 'utrace':
		tread = utread(usrargs, sysargs)
		# sys.exit(errno.EINVAL) # for now, later tread = utread()

	try:
		if 'gz' in tfile:
			cmd = "zcat " + tfile
			# tf = gzip.open(tfile, 'rb')
		else:
			cmd = "cat " + tfile
			tf = open(tfile, 'r')
	except:
		print "Unable to open ", tfile
		sys.exit(errno.EIO)
	
	m_threads = {} #tls
	m_reuse   = {} #tls
	t_buf = []
	t_buf_len = 0
	t_thresh = int(BATCH/10)
	tid = -1
	tname = str(os.path.basename(tfile.split('.')[0]))
	est = ep_stats()

	n_tl = 0

	# try:
	for i in range(0,1):
		for tl in os.popen(cmd, 'r', 32768): # input is global
			
			te = tread.get_tentry(tl)
			if te is None:
				continue

			if te.get_tid() in avoid:
				continue

			n_tl += 1;

			if(n_tl % BATCH == 0):
				print "Worker ", pid, "completed ", str("{:,}".format(n_tl)) , " trace entries"

			if pt > 0: # pt = 1
				if -1 in printl:
					# Write all
					op.write(tl)
				elif te.get_tid() in printl:
					# Write only specific tids
					op.write(tl)

			# caller = te.get_caller()
			# callee = te.get_callee()
			if te.get_tid() != tid:
				tid = te.get_tid()
				if tid not in m_threads:
					m_threads[tid] = smt(tid, usrargs, [pid])
				
				curr = m_threads[tid]			

			if pt > 1: # pt = 2
				l = te.te_list()
				op.write('te = ' + str(l) + '\n')

			# curr.update_call_chain(caller, callee)
		
			ep = curr.do_tentry(te)

			if ep is not None:
				if pt > 2: # pt = 3
					op.write('ep = ' + str(ep.ep_list()) + '\n')

				''' 
					The analysis module will always return, but you
					must decide whether to call into it or not.
				'''
				if anlz is True:
					t = est.get_tuple(ep)

					t_buf.append(t)
					t_buf_len += 1

					if pt > 3: # pt = 4
						op.write('tu[' + str(t_buf_len - 1) + '] = ' + str(t_buf[t_buf_len-1]) + '\n')

					if t_buf_len == t_thresh:
						for t in t_buf:
							csvq.writerow(t)

						myq.flush()
						t_buf = []
						t_buf_len = 0
	'''
	except Exception as inst:

		if anlz is True:
			for t in t_buf:
				csvq.writerow(t)

			myq.flush()
			t_buf = []
			t_buf_len = 0

		print "Failure to proceed", sys.exc_info()[0] # or inst
		sys.exit(0)
	'''
	if anlz is True:
		for t in t_buf:
			csvq.writerow(t)

		myq.flush()
		t_buf = []
		t_buf_len = 0
	'''
	if reuse > 0:
		# For each guest thread context
		for gtid,ctxt in m_threads.items():
			m_reuse[gtid] = Process(target=ping_pong, args=(usrargs, [gtid]))
			m_reuse[gtid].start()
		
		for gtid,reuse_worker in m_reuse.items():
			print "- Worker " + str(pid) + " waiting for reuse worker " + str(gtid)
			m_reuse[gtid].join()
	elif reuse > 1:
		for gtid in m_threads.keys():
			# get the epoch summaries and put them in .q file for analyze.py to process
	'''

if __name__ == '__main__':
		
		try:
			w = int(args.workers)
		except:
			print "The number of workers must be an integer"
			sys.exit(1)
			
		if w <= 0:
			print "The number of workers must be greater than 0"
			sys.exit(1)
			
		pmap = {}
		shmmap = {}
		qs = {}

		print "Calculating number of trace entries... please wait"
		cmd = "zcat " + str(args.tfile) + " | wc -l"
		print "$", cmd
		os.system(cmd)

		for pid in range(0, w):
			qs[pid] = '/dev/shm/.' + str(os.path.basename(args.tfile.split('.')[0])) + '_' + str(pid) + '.q'
			pmap[pid] = Process(target=digest, args=(args, [pid, [], 1000000, w, qs[pid], [-1]]))
			pmap[pid].start()
			print "Parent started worker ", pid
		
		for pid,p in pmap.items():
			print "Parent waiting for worker", pid
			p.join()
		
		''' Analysis routines '''
		if args.anlz is True:
			cmd = 'mypy analyze.py -f ' + str(args.tfile) + ' -w' + str(w)
			os.system(cmd)
		else:
			print "No analysis performed"
		

