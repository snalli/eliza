from cacheline import cacheline
class epoch:

	"""A structure per-SMT context"""
	epoch_types = set(['rd-only','true'])

	def __init__(self, start_time, tid):
		self.rd_set = {}
		self.wrt_set = {}
		self.tid = tid
		self.start_time = start_time
		self.end_time   = 0.0
		self.etype = 'null'
		assert tid > 0
		assert self.start_time > 0.0
		assert self.etype in epoch_types

	def read_cacheline(self, cl):
		assert self.etype in epoch_types

		rd_set = self.rd_set
		wrt_set = self.wrt_set
		etype = self.etype

		__addr = cl.get_addr()

		if __addr not in wrt_set:
			if __addr not in rd_set:
				rd_set[__addr] = cl
		
		if etype == 'null':
			etype = 'rd-only'

		assert (__addr in rd_set) or (__addr in wrt_set)
		assert (etype in epoch_types) and (etype != 'null')

	def write_cacheline(self, cl):
		assert self.etype in epoch_types

		rd_set = self.rd_set
		wrt_set = self.wrt_set
		etype = self.etype

		__addr = cl.get_addr()

		if __addr in rd_set:
			rd_set.pop(__addr)
			assert (__addr not in rd_set)

		if __addr not in wrt_set:
			wrt_set[__addr] = cl
		
		if (etype == 'null') or (etype == 'rd-only'):
			etype = 'true'

		assert (__addr in wrt_set)
		assert (etype in epoch_types) and (etype == 'true')

	def end_epoch(self, end_time):
		assert self.etype in epoch_types
		assert end_time >= self.start_time

		self.end_time = end_time
		rd_set = self.rd_set
		wrt_set = self.wrt_set
		etype = self.etype
		
		if etype != 'null':
			rw_set = self.merge_sets(rd_set, wrt_set)
			assert len(rw_set) == self.get_size()
			# The read and write sets must be mutually exclusive			
			return rw_set
		else:
			return None
			
	def merge_sets(a,b):
		assert a is not None
		assert b is not None

		c = a.copy()
		c.update(b)
		
		return c

	def get_cachelines(self):
		rw_set = self.merge_sets(self.rd_set, self.wrt_set)
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
	
	def get_wrt_set(self):
		return self.wrt_set

	def get_rd_set_sz(self):
		return len(self.rd_set)

	def get_wrt_set_sz(self):
		return len(self.wrt_set)
	
	def get_size(self):
		return len(self.wrt_set) + len(self.rd_set)
