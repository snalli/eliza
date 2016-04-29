from epoch import epoch
from tentry import tentry
import os

class smt:
	def __init__(self, tid, time, usrargs):
		self.tid = tid
		self.usrargs = usrargs
		self.flow = usrargs.flow
		self.ep = None #epoch(0, 0.0)
		self.ep_ops = None #self.ep.get_ep_ops()
		self.call_chain = []
		# Clear away any previous epochs you may have recorded
		tfile = self.usrargs.tfile
		op = open("/dev/shm/." + str(os.path.basename(tfile.split('.')[0])) \
					+ '-' + str(self.tid) + '.e', 'w')		
		op.close()
	def sanity(self, sa, sz, r):
			return
			sa = int(sa, 16)
			ea = sa + sz - 1 # This prevents an off-by-one error
			ecl = ea & ~(63)
			if ecl !=r :
				print hex(ecl), hex(r)
			assert ecl == r

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
		
		if self.ep is None: 
			if te.is_write():
				# The beginning of a new epoch
				self.ep = epoch(self.tid, te.get_time(), self.usrargs)
				self.ep_ops = self.ep.get_ep_ops()
				
				r = self.ep_ops[te_type](te)
				''' Size has to be greater than 0'''
				self.sanity(te.get_addr(), te.get_size(), r)

				assert self.ep.is_true()
				
			elif te.is_fence():
				# Null epoch
				self.ep = epoch(self.tid, te.get_time(), self.usrargs)
				self.ep_ops = self.ep.get_ep_ops()
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep = None
				self.ep_ops = None
		else: 
			# True epoch
			if te.is_fence():
				# The end of another epoch
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep = None
				self.ep_ops = None
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
				
			
