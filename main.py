from ftread import ftread
from smt import smt
from etable import etable
from flow_table import flow_table
import gzip
import os
import sys
import errno
import sqlite3
import argparse
import traceback

ttypes = (['ftrace', 'utrace'])
debugl = [1,2,3,4]

parser = argparse.ArgumentParser(prog="eliza", description="A tool to analyze epochs")
parser.add_argument('-f', dest='tfile', required=True, help="Gzipped trace file")
parser.add_argument('-t', dest='ttype', required=True, help="Type of trace file", choices=ttypes)
parser.add_argument('-d', dest='debug', default = 0, help="Debug levels", choices=debugl)
parser.add_argument('-b', dest='db', action='store_true', default=False, help="Create database")
parser.add_argument('-w', dest='flow', action='store_true', default=False, help="Get control flow of an epoch")
parser.add_argument('-p', '--print', dest='pt', action='store_true', default=False, help="Print trace")
parser.add_argument('-v', '--version', action='version', version='%(prog)s v0.1', help="Display version and quit")

try:
	args = parser.parse_args()
except:
	# parser.exit(status=0, message=parser.print_help())
	sys.exit(0)

tfile = args.tfile
ttype = args.ttype
pt = args.pt
db = args.db
flow = args.flow

if ttype == 'ftrace':
	tread = ftread()
elif ttype == 'utrace':
	print "Unimplemented trace processor"
	sys.exit(errno.EINVAL) # for now, later tread = utread()

try:
	tf = gzip.open(tfile, 'rb')
except:
	print "unable to open ", tfile
	sys.exit(errno.EIO)
	
m_threads = {}
tname = tfile.split('.')[0]
et = etable(tname, db)
ft = flow_table(tname, flow)
n_tl = 0

for i in range(0,1):
	for tl in tf:
		
		n_tl += 1;

		if(pt):
			sys.stdout.write(tl)
		elif(n_tl % 10000 == 0):
			print "Completed ", n_tl, " trace entries"

		te = tread.get_tentry(tl)
		if te is None:
			continue
			
		caller = te.get_caller()
		callee = te.get_callee()
		tid = te.get_tid()
		time = te.get_time()

		#l = te.te_list()
		#print l
		
		if tid not in m_threads:
			m_threads[tid] = smt(tid, time, flow)
		
		curr = m_threads[tid]
		curr.update_call_chain(caller, callee)
		
		if te.is_valid() is True:
			ep = curr.do_tentry(te)
			
			if ep is not None:
				et.insert(ep)
				#if ep.is_rd_only() is True:
				ft.insert(curr.get_call_chain(), curr.get_tid(), ep.get_start_time(), ep.get_end_time())
				#else:
				curr.clear_call_chain()
		
#except Exception as inst:
#	print "Failure to unzip", sys.exc_info()[0] # or inst
#	et.commit()
	#ft.commit()

et.commit()
#ft.commit()
