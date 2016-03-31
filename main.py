from ftread import ftread
from smt import smt
# from etable import etable
# from flow_table import flow_table
from ep_stats import ep_stats
from multiprocessing import Pool, TimeoutError, Process, Queue, Lock
from multiprocessing.sharedctypes import Value, Array
from ctypes import Structure

import gzip
import time
import os
import sys
import errno
import csv
# import sqlite3
import argparse
import traceback
import gc

ttypes = (['ftrace', 'utrace'])
debugl = [1,2,3,4]

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-f', dest='tfile', required=True, help="Gzipped trace file")
parser.add_argument('-y', dest='ttype', required=True, help="Type of trace file", choices=ttypes)
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

def digest(usrargs, sysargs):
	
	args = usrargs
	
	tfile = args.tfile
	ttype = args.ttype
	pt = args.pt
	db = args.db
	flow = args.flow
	anlz = args.anlz

	pid   = sysargs[0]
	avoid = sysargs[1]
	BATCH = sysargs[2]
	n_workers = sysargs[3]
	myq = open(sysargs[4], 'w')
	csvq = csv.writer(myq)
	# myq = sysargs[4]
	
	if ttype == 'ftrace':
		tread = ftread(pid, n_workers)
	elif ttype == 'utrace':
		print "Unimplemented trace processor"
		sys.exit(errno.EINVAL) # for now, later tread = utread()

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
	t_buf = []
	t_buf_len = 0
	t_thresh = 10000
	tid = -1
	tname = str(os.path.basename(tfile.split('.')[0]))
	# et = etable(tname, db)
	# ft = flow_table(tname, flow)
	est = ep_stats(anlz, 'nil')

	n_tl = 0

	try:
		for tl in os.popen(cmd, 'r', 32768): # input is global
			n_tl += 1;

			if(pt):
				sys.stdout.write(tl)
			if(n_tl % BATCH == 0):
				print "Worker ", pid, "completed ", n_tl, " trace entries", len(m_threads.keys())
			
			te = tread.get_tentry(tl)
			if te is None:
				continue

			if te.get_tid() in avoid:
				continue

			# caller = te.get_caller()
			# callee = te.get_callee()
			if te.get_tid() != tid:
				tid = te.get_tid()
				if tid not in m_threads:
					m_threads[tid] = smt(tid, te.get_time(), flow)
				
				curr = m_threads[tid]			
			
			#l = te.te_list()
			#print tl,l

			# curr.update_call_chain(caller, callee)
		
	        #if te.is_valid() is True:

			ep = curr.do_tentry(te)

			
			if ep is not None:
				#	et.insert(ep)
				#	ft.insert(curr.get_call_chain(), curr.get_tid(), ep.get_start_time(), ep.get_end_time())
				t = est.get_tuple(ep)

				t_buf.append(t)
				t_buf_len += 1
				if t_buf_len == t_thresh:
					for t in t_buf:
						csvq.writerow(t)
					t_buf = []
					t_buf_len = 0
					
				# est.insert(ep)



		
	except Exception as inst:
		for t in t_buf:
			csvq.writerow(t)
			t_buf = []
			t_buf_len = 0

		print "Failure to unzip", sys.exc_info()[0] # or inst
		sys.exit(0)
	#	et.commit()
	#ft.commit()
	for t in t_buf:
		csvq.writerow(t)
	t_buf = []
	t_buf_len = 0

	# et.commit()
	# est.analyze()
	#ft.commit()

#class ep_tuple(Structure):
#	_fields_ = [('eid', c_int), ('etype',), (esize,), (wsize,), (cwsize,)
#		        (stime,), (etime,), (r1,), (r2,), (r3,), (r4,), (tid,)]

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

		for pid in range(0, w):
			qs[pid] = '/dev/shm/' + str(os.path.basename(args.tfile.split('.')[0])) + '_' + str(pid) + '.q'
			# qs[pid] = Queue()
			pmap[pid] = Process(target=digest, args=(args, [pid, [3412], 1000000, w, qs[pid]]))
			pmap[pid].start()
			print "Parent started worker ", pid
		
		for pid,p in pmap.items():
			print "Parent waiting for worker", pid
			p.join()
			
		#est = ep_stats(args.anlz, 'stat/' + str(args.tfile.split('.')[0]) + '.stat')			
		#for cq in qs.values():
		#	f = open(cq, 'r')
		#	csvr = csv.reader(f)
		#	for row in csvr:
		#		est.insert_l(row)
		#	f.close()
		
		#est.analyze()
			
