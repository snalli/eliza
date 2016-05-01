from epoch import epoch
from tentry import tentry
import os,csv,gzip
from ep_stats import ep_stats


class smt:
	def __init__(self, tid, usrargs, sysargs):
		self.tid = tid
		self.ep = None #epoch(0, 0.0)
		self.ep_ops = None #self.ep.get_ep_ops()
		self.true_ep_count = 0 # Count of true epochs
		self.null_ep_count = 0 # Count of null epochs
		self.cwrt_set = {}
		self.call_chain = []

		self.ppid = sysargs[0]		

		self.usrargs = usrargs
		self.flow = self.usrargs.flow
		self.tfile = self.usrargs.tfile
		
		# Clear away any previous epochs you may have recorded
		# We are maitaining per-thread logs of all NVM writes
		'''
		self.csvlog = open("/dev/shm/" + str(os.path.basename(self.tfile.split('.')[0])) \
					+ '-' + str(self.tid) + '.csv', 'w')

		# self.csvlog = gzip.open("/dev/shm/" + str(os.path.basename(self.tfile.split('.')[0])) \
		#			+ '-' + str(self.tid) + '.csv.gz', 'wb')
					
		self.log = csv.writer(self.csvlog)		
		'''
		if self.usrargs.reuse > 0: #1,2,3
			try :
				self.log = open("/dev/shm/" + str(os.path.basename(self.tfile.split('.')[0])) \
					+ '-' + str(self.tid) + '.txt', 'w')
			except:
				# When there are too many open files, open() files
				self.log = None
		else:
			self.log = None
			
		self.est = ep_stats()

		
	def sanity(self, sa, sz, r):
			return
			sa = int(sa, 16)
			ea = sa + sz - 1 # This prevents an off-by-one error
			ecl = ea & ~(63)
			if ecl !=r :
				print hex(ecl), hex(r)
			assert ecl == r

	def log_start_entry(self):
		if self.log is not None:
			self.log.write('{')
			
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
		est = self.est
		
		if self.ep is None: 
			if te.is_write():
				# The beginning of a new epoch
				self.log_start_entry()

				# No epoch number should start from 0
				self.true_ep_count += 1
				self.ep = epoch([self.true_ep_count, te.get_time()], \
								[self.tid, self.log, self.cwrt_set], \
								self.usrargs) 
								#self.tid, te.get_time(), log)
				self.ep_ops = self.ep.get_ep_ops()
				
				r = self.ep_ops[te_type](te)
				''' Size has to be greater than 0'''
				self.sanity(te.get_addr(), te.get_size(), r)

				assert self.ep.is_true()
				
			elif te.is_fence():
				# Null epoch
				# No epoch number should start from 0
				self.null_ep_count += 1
				self.ep = epoch([self.null_ep_count, te.get_time()], \
								[self.tid, self.log, self.cwrt_set], \
								self.usrargs) 
				self.ep_ops = self.ep.get_ep_ops()
				self.ep.end_epoch(te)

				ret = self.ep
				self.ep = None
				self.ep_ops = None

				# self.log_start_entry()
				# self.log_insert_entry(est.get_str(ret))
				# self.log_end_entry()
		else: 
			# True epoch
			if te.is_fence():
				# The end of another epoch
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep = None
				self.ep_ops = None

				self.log_insert_entry(est.get_str(ret))
				self.log_end_entry()

			else:
					
				r = self.ep_ops[te_type](te)
				if(te.get_size() > 0):
					self.sanity(te.get_addr(), te.get_size(), r)
				
		return ret
		'''
		if te.is_write() is True:
			if self.ep.is_null():
				self.ep.set_tid(self.tid)
				self.ep.set_time(te.get_time())
			
			assert te_type in self.ep_ops
			
			ep_op = self.ep_ops[te_type]
			r = ep_op(te)
			if(te.get_size()):
				self.sanity(te.get_addr(), te.get_size(), r)
				# Do a sanity check only when u have memory accesses
			assert self.ep.is_true() is True
		elif te.is_fence():
			if self.ep.is_null(): # null epoch
				self.ep.set_tid(self.tid)
				self.ep.set_time(te.get_time())
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep.reset()
			else:
				assert self.ep.is_true() is True
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep.reset()
		else:
			if self.ep.is_true():
				ep_op = self.ep_ops[te_type]
				r = ep_op(te)
				if(te.get_size() > 0):
					self.sanity(te.get_addr(), te.get_size(), r)
				# Do a sanity check only when u have memory accesses
		return ret
		'''
	
	def update_call_chain(self, caller, callee):
		if self.flow is False:
			return
			
		l = len(self.call_chain)
		
		if caller != 'null':
			if l == 0:
				self.call_chain.append(caller)
			elif caller != self.call_chain[l-1]:
				self.call_chain.append(caller)
		
		if callee == 'null':
			# print "(update_call_chain)", self.tid, self.time
			# callee cannot be null because the processor always is 
			# inside a callee !
			assert callee != 'null'
		else:
			if l == 0:
				self.call_chain.append(callee)
			elif callee != self.call_chain[l-1]:
				self.call_chain.append(callee)
	
	def get_call_chain(self):
		if self.flow is False:
			return None
			
		if len(self.call_chain) == 0:
			# print "(get_call_chain)", tid
			assert len(self.call_chain) != 0
		else:
			call_str = 'S'
			m = "->"
			for f in self.call_chain:
				call_str += m
				call_str += f
			
		call_str += m
		call_str += 'E'	
		self.call_chain = []
		return call_str
	
	def clear_call_chain(self):
		self.call_chain = []
		
	def get_tid(self):
		return self.tid
		
	def close_thread(self):
		self.log.close()
				
			
