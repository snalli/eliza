from epoch import epoch
from tentry import tentry

class smt:
	def __init__(self, tid, time):
		self.tid = tid
		self.ep = None #epoch(tid, time)
		self.ep_ops = None #self.ep.get_ep_ops()
		self.call_chain = []
		
	def sanity(self, sa, sz, r):
			sa = int(sa, 16)
			ea = sa + sz - 1 # This prevents an off-by-one error
			ecl = ea & ~(63)
			if ecl !=r :
				print hex(ecl), hex(r)
			assert ecl == r

	def do_tentry(self, te):
		assert te.is_valid() is True
		
		ret = None
		te_type = te.get_type()
		
		if te.is_write() is True:
			if self.ep is None:
				self.ep = epoch(self.tid, te.get_time())
				self.ep_ops = self.ep.get_ep_ops()
			
			assert self.ep is not None
			assert self.ep_ops is not None				
			assert te_type in self.ep_ops
			
			ep_op = self.ep_ops[te_type]
			r = ep_op(te)
			if(te.get_size()):
				self.sanity(te.get_addr(), te.get_size(), r)
				# Do a sanity check only when u have memory accesses
			assert self.ep.is_true() is True
			
		elif te.is_fence() is True:
			if self.ep is None: # null epoch
				self.ep = epoch(self.tid, te.get_time())
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep = None
				self.ep_ops = None
			else:
				assert self.ep.is_true() is True
				self.ep.end_epoch(te)
				ret = self.ep
				self.ep = None
				self.ep_ops = None
		else:
			if self.ep is not None:
				assert self.ep.is_true() is True
				assert self.ep_ops is not None
				assert te_type in self.ep_ops
				
				ep_op = self.ep_ops[te_type]
				r = ep_op(te)
				if(te.get_size() > 0):
					self.sanity(te.get_addr(), te.get_size(), r)
				# Do a sanity check only when u have memory accesses

		
		return ret

	
	def update_call_chain(self, caller, callee):
		l = len(self.call_chain)
		
		if caller != 'null':
			if l == 0:
				self.call_chain.append(caller)
			elif caller != self.call_chain[l-1]:
				self.call_chain.append(caller)
		
		if callee == 'null':
			print "(update_call_chain)", self.tid, self.time
			assert callee != 'null'
		else:
			if l == 0:
				self.call_chain.append(callee)
			elif callee != self.call_chain[l-1]:
				self.call_chain.append(callee)
	
	def get_call_chain(self):
		if len(self.call_chain) == 0:
			print "(get_call_chain)", tid
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
				
			
