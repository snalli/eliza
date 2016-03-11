from epoch import epoch
from ftread import ftread
import gzip
import os
import sys

ttypes = (['ftrace', 'utrace'])
if len(sys.argv) == 1:
	print "Usage : python main.py <trace file> <trace type>"
	sys.exit(0)
else:
	tfile = sys.argv[1]
	ttype = sys.argv[2]
	if ttype in ttypes:
		if ttype == 'ftrace':
			tread = ftread()
		elif ttype == 'utrace':
			sys.exit(1) # for now
			
	tf = gzip.open(tfile, 'rb')

for tl in tf:
		te = tread.get_tentry(tl)
		if te is not None:
			l = te.te_list()
			print l
