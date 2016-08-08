from txn import tx
from tentry import tentry
import sys
import os,csv,gzip


class smt:
	def __init__(self, tid, usrargs, sysargs):
		self.tid = tid
		self.tx = None
		self.txid = 0
		self.tx_count = 0
		self.cwrt_set = {} # ?
		self.tx_stack = [] # For nested txns, may shift to real stack later
		# Clear away any previous epochs you may have recorded
		# We are maitaining per-thread logs of all NVM writes
		'''
		self.csvlog = open("/dev/shm/" + str(os.path.basename(self.tfile.split('.')[0])) \
					+ '-' + str(self.tid) + '.csv', 'w')

		# self.csvlog = gzip.open("/dev/shm/" + str(os.path.basename(self.tfile.split('.')[0])) \
		#			+ '-' + str(self.tid) + '.csv.gz', 'wb')
					
		self.log = csv.writer(self.csvlog)		
		'''
		# Open a per-thread log file here
		self.sysargs = sysargs
		self.usrargs = usrargs
		self.logdir = sysargs[6]
		self.tfile = self.usrargs.tfile
		self.log = None
		if self.usrargs.reuse > 0: #1,2,3
			print self.logdir + '/' + str(os.path.basename(self.tfile.split('.')[0])) \
				+ '-' + str(self.tid) + '.txt'
			try :
				self.log = open(self.logdir + '/' + str(os.path.basename(self.tfile.split('.')[0])) \
					+ '-' + str(self.tid) + '.txt', 'w')
			except:
				# When there are too many open files, open() fails
				self.log = None
		else:
			self.log = None
			
	def log_start_entry(self):
		if self.log is not None:
			self.log.write('{;')
			
	def log_end_entry(self):
		if self.log is not None:
			self.log.write('}\n')
		
	def log_insert_entry(self, lentry):
		if self.log is not None:
			self.log.write(str(lentry) + ';')
				
	def do_tentry(self, te):
		'''
			A thread can receive a compound operation or a simple
			operation. A compound operation is an operation on a range of
			memory specified by the starting address of the range, the size
			of the range and the type of operation. The types can be
			read, write, movnti or clflush.
			
			A simple operation is an operation on a 8-byte or 64-bit range.
			Mulitple consecutive simple operations form a compound operation.
		'''
		assert te.is_valid() is True
		
		ret = None
		te_type = te.get_type()
		log = self.log
		
		if te.is_tx_start():
			
			if self.tx is None:
				assert self.tx_count == 0
				self.tx_count += 1
				self.txid += 1
				''' Create a new txn context '''
				self.tx = tx([self.tid, self.txid, te.get_time(), 	\
								self.log, self.cwrt_set], 			\
								self.usrargs, self.sysargs)
				assert self.tx is not None

			return self.tx.do_tentry(te)
			
			''' 
				For nested transactions 
				Abandoning this code in favor of PMFS.
				For userspace, you may plug it back in
			
			if self.tx is not None:
				self.tx_stack.append(self.tx)
				
			self.txid += 1
			self.tx = tx([self.tid, self.txid, te.get_time(), 	\
							self.log, self.cwrt_set], 			\
							self.usrargs, self.sysargs)
			assert self.tx is not None
			return self.tx.do_tentry(te)
			'''
		elif te.is_tx_end():

			if self.tx_count > 0:
				self.tx_count -= 1
			
			if self.tx_count == 0 and (self.tx is not None): 
				try:
					ret = self.tx.tx_end(te)
				except:
					print "THD_ERR1", te.te_list()
					sys.exit(0)
				
				self.tx = None
				
			return None
			
			'''
				For nested transactions 
				Abandoning this code in favor of PMFS.
				For userspace, you may plug it back in

			if self.tx is None:
				return None
				# Houston, something is wrong and we lost the start of the txn
				# So ignore and proceed
				
			try:
				ret = self.tx.tx_end(te)
			except:
				print "THD_ERR1", te.te_list()
				sys.exit(0)

			self.tx = None
			if len(self.tx_stack) > 0:
				self.tx = self.tx_stack.pop()
			return ret
			'''
		else:
			if self.tx is None:
				return None
			# We don't care about operations outside a txn
			
			#try:
			return self.tx.do_tentry(te)
			#except:
			#	print "THD_ERR2", te.te_list()
			#	sys.exit(0)			
									
	def update_call_chain(self, caller, callee):
		return self.tx.update_call_chain(caller, callee)
	
	def get_call_chain(self):
		return self.tx.get_call_chain()
	
	def clear_call_chain(self):
		self.tx.clear_call_chain()
		
	def get_tid(self):
		return self.tid
		
	def get_tid(self):
		if tx is not None:
			assert tx.get_txid() == self.txid
		return self.txid

	def close_thread(self):
		if self.log is not None:
			self.log.close()
				
			
