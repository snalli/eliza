from cacheline import cacheline
from tentry import tentry
class epoch:

	"""A structure per-SMT context"""
	epoch_types = set(['null', 'rd-only','true'])
	CMASK = 0x3f
	CSIZE = 64
	
	def __init__(self, tid, time):
		self.rd_set = {}
		self.cwrt_set = {}
		self.nwrt_set = {}
		self.tid = tid
		self.start_time = time
		self.end_time   = 0.0
		self.etype = 'null'
		self.size = 0
		self.ep_ops = {'PM_R' : self.read, 'PM_W' : self.cwrite, 
				'PM_I' : self.nwrite, 'PM_L' : self.clflush,
				'PM_XS' : self.do_nothing, 'PM_XE' : self.do_nothing,
				'PM_C' : self.do_nothing}
				
		self.end_ops = ['PM_N','PM_B']

		assert tid > 0
		assert self.start_time > 0.0
		assert self.etype in self.epoch_types

	def get_ep_ops(self):
		return self.ep_ops
		
	def get_n_cl(self, s_addr, size):
		e_addr = s_addr + size - 1
		s_cl = s_addr & ~(self.CMASK)
		e_cl = e_addr & ~(self.CMASK)
		return 1 + ((e_cl - s_cl)/self.CSIZE)
		
	def ecl(self, s_addr, size):
		e_addr = s_addr + size - 1
		s_cl = s_addr & ~(self.CMASK)
		e_cl = e_addr & ~(self.CMASK)
		return e_cl

	def read(self, te):
		addr = te.get_addr()
		size = te.get_size()
		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		
		n_cl = self.get_n_cl(s_addr, size)
		s_cl = s_addr & ~(self.CMASK)
		for i in range(0, n_cl):
			cl = cacheline(s_cl + i*self.CSIZE)
			self.read_cacheline(cl)
			
		return s_cl + i*self.CSIZE
	
	def cwrite(self, te):
		addr = te.get_addr()
		size = te.get_size()

		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		
		n_cl = self.get_n_cl(s_addr, size)
		s_cl = s_addr & ~(self.CMASK)
		for i in range(0, n_cl):
			cl = cacheline(s_cl + i*self.CSIZE)
			self.cwrite_cacheline(cl)

		return s_cl + i*self.CSIZE
		
	def clflush(self, te):
		addr = te.get_addr()
		size = te.get_size()

		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		return self.ecl(s_addr, size)
		
	def nwrite(self, te):
		addr = te.get_addr()
		size = te.get_size()

		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		n_cl = self.get_n_cl(s_addr, size)
		s_cl = s_addr & ~(self.CMASK)
		for i in range(0, n_cl):
			cl = cacheline(s_cl + i*self.CSIZE)
			self.nwrite_cacheline(cl)

		return s_cl + i*self.CSIZE

		
	def do_nothing(self, te):
		return 0
		
	def read_cacheline(self, cl):
		assert self.etype in self.epoch_types

		__addr = cl.get_addr()

		# Refer to state diagram
		if __addr not in self.cwrt_set:
			
			if __addr in self.nwrt_set:
				self.nwrt_set.pop(__addr)
				
			assert (__addr not in self.nwrt_set)
				
			if __addr not in self.rd_set and __addr not in self.nwrt_set:
					self.rd_set[__addr] = cl
		
		if self.etype == 'null':
			self.etype = 'rd-only'

		assert (__addr in self.rd_set) or (__addr in self.cwrt_set) or (__addr in self.nwrt_set)
		assert (self.etype in self.epoch_types) and (self.etype != 'null')

	def cwrite_cacheline(self, cl):
		assert self.etype in self.epoch_types

		__addr = cl.get_addr()

		if __addr in self.rd_set:
			self.rd_set.pop(__addr)
			assert (__addr not in self.rd_set)
		
		if __addr in self.nwrt_set:
			self.nwrt_set.pop(__addr)
			assert (__addr not in self.nwrt_set)

		if __addr not in self.cwrt_set:
			self.cwrt_set[__addr] = cl
		
		if (self.etype == 'null') or (self.etype == 'rd-only'):
			self.etype = 'true'

		assert (__addr in self.cwrt_set)
		assert (self.etype in self.epoch_types) and (self.etype == 'true')

	def nwrite_cacheline(self, cl):
		assert self.etype in self.epoch_types

		__addr = cl.get_addr()

		if __addr in self.rd_set:
			self.rd_set.pop(__addr)
			assert (__addr not in self.rd_set)
		
		if __addr in self.cwrt_set:
			self.cwrt_set.pop(__addr)
			assert (__addr not in self.cwrt_set)

		if __addr not in self.nwrt_set:
			self.nwrt_set[__addr] = cl
		
		if (self.etype == 'null') or (self.etype == 'rd-only'):
			self.etype = 'true'

		assert (__addr in self.nwrt_set)
		assert (self.etype in self.epoch_types) and (self.etype == 'true')
		
	def end_epoch(self, te):
		assert self.etype in self.epoch_types
		end_time = te.get_time()
		assert end_time >= self.start_time

		self.end_time = end_time
		self.size = self.get_size()
		cwrt_set = self.cwrt_set
		nwrt_set = self.nwrt_set
		etype = self.etype
		
		return self.merge_sets(nwrt_set, cwrt_set) 
		# Nobody cares about this return value
			
	def merge_sets(self,a,b):
		assert a is not None
		assert b is not None

		c = a.copy()
		c.update(b)
		
		return c

	def get_cachelines(self):
		# Only cache rd and wrt
		rw_set = self.merge_sets(self.rd_set, self.cwrt_set)
		assert len(rw_set) == self.get_size()
		return rw_set

	def get_duration(self):
		etime = self.end_time	
		stime = self.start_time
		
		if etime == 0.0:
			return 0.0
		else:
			assert (etime >= stime)
			return (etime - stime)
			
	def get_start_time(self):
		return self.start_time
		
	def get_end_time(self):
		return self.end_time
		
	def get_tid(self):
		return self.tid
	
	def get_epoch_type(self):
		return self.etype

	def get_rd_set(self):
		return self.rd_set
	
	def get_cwrt_set(self):
		return self.cwrt_set

	def get_nwrt_set(self):
		return self.nwrt_set

	def get_rd_set_sz(self):
		return len(self.rd_set)

	def get_cwrt_set_sz(self):
		return len(self.cwrt_set)
	
	def get_nwrt_set_sz(self):
		return len(self.nwrt_set)

	def get_size(self):
		return len(self.cwrt_set) + len(self.rd_set) + len(self.nwrt_set)
	
	def is_true(self):
		if self.etype == 'true':
			return True
		else:
			return False
			
	def is_rd_only(self):
		if self.etype == 'rd-only':
			return True
		else:
			return False
