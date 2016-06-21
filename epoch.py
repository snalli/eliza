from cacheline import cacheline
from tentry import tentry
import sys,os
class epoch:

	"""A structure per-SMT context"""

	epoch_types = set(['null', 'rd-only','true'])
	BSIZE = 8
	CSIZE = 64
	PSIZE = 4096
	''' 
		The ~ operator doesn't work as expected 
		~0x7 = -8 and not 0xfffffffffffffff8 !
	'''
	CMASK = 0xffffffffffffffc0
	BMASK = 0xfffffffffffffff8
	PMASK = 0xfffffffffffff000
	COFF  = 0x3f
	BOFF  = 0x7
	POFF  = 0x0fff
	
	def __init__(self, epargs, tidargs, usrargs):

		# Original members
		self.prev_wrt_addr = -1
		self.rd_set = {}
		self.cwrt_set = {}
		self.nwrt_set = {}
		self.page_set = {}

		# Intra thread dep stuff
		self.wrt_l = [] # TODO Redundant ?
		self.page_span = 0
		self.eid = epargs[0]
		self.most_recent_dep = 0
		self.least_recent_dep = self.eid
		self.dep_track = int(usrargs.reuse)
		# Not having type-safety is a boon
		self.log = tidargs[1]
		self.tl_cwrt_set = tidargs[2]

		#Inter thread dep stuff
		self.epaddr2pc = {}
		self.writer = 'none'
		
		self.tid = tidargs[0]
		self.start_time = epargs[1]
		self.end_time   = 0.0
		self.etype = 'null'
		self.size = 0
		self.ep_ops = {'PM_R' : self.read, 'PM_W' : self.cwrite, 
				'PM_I' : self.cwrite, 'PM_L' : self.clflush,
				'PM_XS' : self.do_nothing, 'PM_XE' : self.do_nothing,
				'PM_C' : self.do_nothing}
				
		self.end_ops = ['PM_N','PM_B']

		assert self.etype in self.epoch_types

	def ep_list(self):
			
		cwsize = self.get_cwrt_set_sz()
		wsize  = float(cwsize) + self.get_nwrt_set_sz()
		esize  = wsize + float(self.get_rd_set_sz())
		
		# t =  (etype, esize, wsize, cwsize,
		#        stime, etime, r1, r2, r3 ,r4, tid)

		return [self.tid, self.end_time, self.etype, esize, wsize, cwsize, self.start_time]

	def reset(self):
		# Obsolete, do not use
		self.rd_set.clear()
		self.cwrt_set.clear()
		self.nwrt_set.clear()
		self.tid = 0
		self.page_span = 0
		self.start_time = 0.0
		self.end_time   = 0.0
		self.etype = 'null'
		self.size = 0
		
	def get_ep_ops(self):
		return self.ep_ops
		
	def get_n_cl(self, s_addr, size):
		e_addr = s_addr + size - 1
		s_cl = s_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		e_cl = e_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		return 1 + ((e_cl - s_cl)/self.CSIZE)
		
	def get_n_bi(self, s_addr, size):
		if size == 0:
			return 0

		# s_addr is 8-byte aligned
		# size is a mutiple of 8
		e_addr = s_addr + size - 1
		assert ((e_addr + 0x1) & self.BOFF == 0)
		s_bi = s_addr & self.BMASK # ~(self.BMASK) BMASK = 0x7
		e_bi = e_addr & self.BMASK # ~(self.BMASK) BMASK = 0x7
		return 1 + ((e_bi - s_bi)/self.BSIZE)

	def ecl(self, s_addr, size):
		e_addr = s_addr + size - 1
		s_cl = s_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		e_cl = e_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		return e_cl

	''' Stage 1 '''

	def read(self, te):
		addr = te.get_addr()
		size = te.get_size()
		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		
		n_cl = self.get_n_cl(s_addr, size)
		s_cl = s_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		for i in range(0, n_cl):
			cl = cacheline(s_cl + i*self.CSIZE)
			self.read_cacheline(cl)
			
		return s_cl + i*self.CSIZE
	
	def cwrite(self, te):
		addr = te.get_addr()
		size = te.get_size()
		self.writer = te.get_caller() + '/' + str(te.get_pc())
		
		s_addr = int(addr, 16)
		assert size > 0
		assert s_addr > 0
		
		n_cl = self.get_n_cl(s_addr, size)
		s_cl = s_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		ar   = s_addr
		sz   = 0
		'''
			This coding here is superb !
			It takes care of writes that are un-aligned
			with cacheline boundary.
		'''
		for i in range(0, n_cl):
			cl = cacheline(s_cl + i*self.CSIZE)
			# Put cl in a list here for WaW calculation
			'''
				Up until this layer of implementation of the epoch abstraction,
				we have enough information to log all store accesses made
				by the epoch. But if we want to track dependency, we have 
				to track ownership and for that we need to go one layer down !
			'''
			if (ar & self.CMASK) != ((ar + size - 1) & self.CMASK):
				sz = ((ar + self.CSIZE) & self.CMASK) - ar
			else:
				sz = size
				
			self.cwrite_cacheline(cl, ar, sz)

			ar = ar + sz
			size = size - sz

		self.writer = 'none'
		assert size == 0
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
		self.writer = te.get_caller() + '/' + str(te.get_pc())
		
		assert size > 0
		assert s_addr > 0
		
		'''
		It is wise to not intriduce another abstraction of a buffer item
		but think in terms of whole or partially-dirty cachelines.
		This makes programming easier. When you store to a cacheline,
		you can pass its address to the WCB and invalidate the line. This
		would not have been possible if you used buffer item abstraction.
		
		Further, there are two conditions to write non-temporally :
		1. The start address of every write must be 8-byte aligned
		2. There must be at least 8-bytes to write
		
		'''

		if size < self.BSIZE:
			cl = cacheline(s_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
			self.cwrite_cacheline(cl)

			''' The write can be across cache-line boundaries '''
			e_addr = s_addr + size - 1
			#print "1)", size, "b sa=", hex(s_addr & ~self.CMASK), " ea=", hex(e_addr & ~self.CMASK)
			cl = cacheline(e_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
			self.cwrite_cacheline(cl)

			self.writer = 'none'
			return e_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		elif size == self.BSIZE:
			if (s_addr & self.BOFF == 0):
				cl = cacheline(s_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
				b_idx = (s_addr - (s_addr & self.CMASK)) / self.BSIZE # ~(self.CMASK) CMASK = 0x3f
				self.nwrite_cacheline(cl, b_idx)
				#print "2)", size, "b sa/ea=", hex(s_addr & ~self.CMASK), " b_idx=", b_idx
				
				self.writer = 'none'
				return s_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
			else:
				cl = cacheline(s_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
				self.cwrite_cacheline(cl)

				''' The write can be across cache-line boundaries '''
				e_addr = s_addr + size - 1
				# print "3)", size, "b sa=", hex(s_addr & ~self.CMASK), " ea=", hex(e_addr & ~self.CMASK)
				cl = cacheline(e_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
				self.cwrite_cacheline(cl)

				self.writer = 'none'
				return e_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f
		elif size > self.BSIZE:

			s_cbytes = 0
			if (s_addr & self.BOFF != 0):
				s_cbytes = (s_addr & self.BMASK) + self.BSIZE - s_addr
				cl = cacheline(s_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
				# print "4.0)", s_cbytes, "b sa=", hex(s_addr & ~self.CMASK)		
				self.cwrite_cacheline(cl)
				s_addr = (s_addr & self.BMASK) + self.BSIZE
				size = size - s_cbytes
		
			e_cbytes = 0	
			e_addr = s_addr + size - 1
			if((e_addr + 1) & self.BOFF != 0):
				e_cbytes = e_addr - (e_addr & self.BMASK) + 1
				size = size - e_cbytes
				
			# print "4.2)", size, "b sa=", hex(s_addr & ~self.CMASK), " ea=", hex(e_addr & ~self.CMASK)		
		
			assert (size % 8 == 0) # size is multiple of 8
			assert s_addr > 0 
			assert (s_addr & self.BOFF == 0) # addr is 8-byte aligned
		
			n_bi = self.get_n_bi(s_addr, size)
			s_bi = s_addr
			for i in range(0, n_bi):
			
				__s_bi = s_bi + i*self.BSIZE
				s_cl = __s_bi & self.CMASK # ~(self.CMASK) CMASK = 0x3f
				b_idx = (__s_bi - s_cl)/self.BSIZE
			
				# print "5) 8 b, sa_b=", hex(__s_bi), " b_idx=", b_idx
				# print n_bi, hex(s_cl)
				cl = cacheline(s_cl)
				# TODO : Put cl in a list for WaW distance calculation
				# But be careful about multiple writes to the same CL
				# That can alter the WaW drastically.
				self.nwrite_cacheline(cl, b_idx)

			if((e_addr + 1) & self.BOFF != 0):
				cl = cacheline(e_addr & self.CMASK) # ~(self.CMASK) CMASK = 0x3f
				# print "4.1)", e_cbytes, "b sa=", hex(e_addr & ~self.CMASK)		
				self.cwrite_cacheline(cl)
				
			self.writer = 'none'
			return e_addr & self.CMASK # ~(self.CMASK) CMASK = 0x3f

		
	def do_nothing(self, te):
		return 0

	''' Stage 2 '''
	def logger(self, cl_addr):
		''' 
			We don't write to the log here since writing to an
			external file on every access is slower than buffering it
			in memory and writing back in batches later.
			
			But we still do check to see if the logfile handler is non-null,
			to decide if we want to cache the order of addresses accessed
			by the epoch.
			
			The write requests are completed in two stages. In the first stage,
			the write requests is converted into a list of one or more 
			cache-aligned addresses. These addresses are then issued one by one
			to the second stage that checks for ownership and dependencies with
			previous epochs. The stage two is unaware of whether the request to
			access an cl-addr was internal or external.
		'''
		if self.log is not None:
			if cl_addr != self.prev_wrt_addr:
				self.prev_wrt_addr = cl_addr
				self.wrt_l.append(self.prev_wrt_addr)
			# else you can count how many times was the same address written
			# to. but beware, the count can be a side-effect of your
			# instrumentation or measurement

	
	def get_dist_from_mrd(self):
		'''
			This "if" checks if an epoch has had any 
			dependencies. If none, return 0 indicating
			this is self-dependent or an independent epoch.
			Ignore all 0s when analyzing.
		'''
		if self.most_recent_dep == 0:
			return 0
			
		assert self.eid > self.most_recent_dep
		return self.eid - self.most_recent_dep
	
	def get_dist_from_lrd(self):
		'''
			This "if" checks if an epoch has had any 
			dependencies. If none, return 0 indicating
			this is self-dependent or an independent epoch.
			Ignore all 0s when analyzing.
		'''
		if self.least_recent_dep == self.eid:
			return 0
			
		assert self.eid > self.least_recent_dep
		return self.eid - self.least_recent_dep
		
	def check_dep(self, owner, __addr):
		# Check for intra-thread epoch deps
		
		if owner is False:
			# Make this configurable in case you do not want to track deps
			if self.dep_track == 2:
				if __addr in self.tl_cwrt_set:
					last_dep = self.tl_cwrt_set[__addr]
					''' 
						If the curr epoch is not the owner
						of the cl, make sure the id of the last epoch
						that was the owner is LESS than the id of curr
						epoch.
						This gives rise to the notion of dependent epochs
						and independent epochs, which may be rare
					'''
					assert last_dep  < self.eid
					if last_dep > self.most_recent_dep:
						self.most_recent_dep = last_dep
					if last_dep < self.least_recent_dep:
						self.least_recent_dep = last_dep

				self.tl_cwrt_set[__addr] = self.eid
				# look for thread-local ownership
			# elif self.dep_track == 3:
				# look for global ownership

		
	def read_cacheline(self, cl):
		assert self.etype in self.epoch_types

		__addr = cl.get_addr()
		assert (__addr & self.COFF == 0)

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

	def cwrite_cacheline(self, cl, ar, sz):
		assert self.etype in self.epoch_types

		owner = False
		__addr = cl.get_addr()
		assert (__addr & self.COFF == 0)
		assert sz > 0
		assert (ar & self.CMASK) == __addr
		# self.logger(cl.get_addr())
		
		# Refer to state diagram
		if __addr in self.rd_set:
			self.rd_set.pop(__addr)
			assert (__addr not in self.rd_set)
		
		if __addr in self.nwrt_set:
			owner = True
			self.nwrt_set.pop(__addr)
			assert (__addr not in self.nwrt_set)

		if __addr not in self.cwrt_set:
			# self.check_dep(owner, __addr)
			self.cwrt_set[__addr] = cl

		''' Update stats ''' 
		self.cwrt_set[__addr].dirty_all()
		self.cwrt_set[__addr].dirty_bytes(ar, sz)
		self.epaddr2pc[__addr] = str(self.writer) # Last writer wins
		
		if (self.etype == 'null') or (self.etype == 'rd-only'):
			self.etype = 'true'

		assert (__addr in self.cwrt_set)
		assert (self.etype in self.epoch_types) and (self.etype == 'true')

	def nwrite_cacheline(self, cl, b_idx):
		assert b_idx > -1 and b_idx < 8
		assert self.etype in self.epoch_types
		
		owner = False
		__addr = cl.get_addr()
		assert (__addr & self.COFF == 0)
		# self.logger(cl.get_addr())
		
		# Refer to state diagram
		if __addr in self.rd_set:
			self.rd_set.pop(__addr)
			assert (__addr not in self.rd_set)
		
		if __addr in self.cwrt_set:
			owner = True
			self.cwrt_set.pop(__addr)
			assert (__addr not in self.cwrt_set)

		if __addr not in self.nwrt_set:
			# self.check_dep(owner, __addr)
			self.nwrt_set[__addr] = cl
			if len(self.nwrt_set) > 512:
				assert False
		
		self.nwrt_set[__addr].dirty(b_idx)
		self.epaddr2pc[__addr] = str(self.writer) # Last writer wins
				
		if (self.etype == 'null') or (self.etype == 'rd-only'):
			self.etype = 'true'

		assert (__addr in self.nwrt_set)
		assert (self.etype in self.epoch_types) and (self.etype == 'true')
		
	def end_epoch(self, te):
		assert self.etype in self.epoch_types
		end_time = te.get_time()
		assert end_time >= self.start_time

		self.end_time = end_time
		''' 
			Calculate page span here.
			It could have been done in the nwrite and cwrite routines
			using a O(1) hash table look up but there would have been 
			significantly higher number of hash table lookups there 
			than here.
			But then we do not know how many times a page is referenced
			in an epoch. Not sure if that is interesting.
		'''
		for k in self.cwrt_set.keys():
			self.page_set[k & self.PMASK] = 0
			
		for k in self.nwrt_set.keys():
			self.page_set[k & self.PMASK] = 0
			
		self.page_span = len(self.page_set)
		
		# return the string of accesses inside this epoch here
		# or simply dump the list in a file and invoke Rathijit's
		# reuse tool with the output file name. Use the tid to get
		# the filename. Make this configurable
		# Try to see if you can move this out of the epoch code
		# This epoch code is extremely robust
		# reuse within threads can show us cascades !
		# Do all stat collection in the destructor routine, you have
		# my permission to do it. But don't touch the core of the epoch
		# code.
		if self.etype == 'true' and self.log is not None:
			# If you are going to include non-temporal stores as well,
			# change the if condition to check for non-empty nwrt_set 
			# PS : It suffices to check if the epoch is true or null
			tmp_l = sorted(list(self.merge_sets(self.cwrt_set, self.nwrt_set)))
			first_entry = True
			# It is not enuf just to check prev_addr ! Consider aaabbcca --> (a,b,c,a)!
			for addr in tmp_l:#set(self.wrt_l): # You can merge the two write sets here ?!
				if first_entry is True:
					first_entry = False
				else:
					self.log.write(',')
				self.log.write(str(hex(addr)));
			self.log.write(';');

			
			first_entry = True
			for addr in tmp_l:
				if first_entry is True:
					first_entry = False
				else:
					self.log.write(',')
				self.log.write(self.epaddr2pc[addr]);
			self.log.write(';');
			
#		self.size = self.get_size()
#		cwrt_set = self.cwrt_set
#		nwrt_set = self.nwrt_set
#		etype = self.etype
		
#		return self.merge_sets(nwrt_set, cwrt_set) 
		# Nobody cares about this return value
			
	def merge_sets(self,a,b):
		assert a is not None
		assert b is not None

		c = a.copy()
		c.update(b)
		
		return c

	def get_page_span(self):
		return self.page_span
		
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
	
	def set_tid(self, tid):
		self.tid = tid

	def set_time(self, time):
		self.start_time = time

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
		n_buf = 0
		for a,cl in self.nwrt_set.iteritems():
			# print hex(cl.get_addr()), cl.get_dirtyness()
			n_buf += cl.get_dirtyness()
		
		# print "nwrt_sz", n_buf, float(n_buf)/ float(self.BSIZE)
		return float(n_buf) / float(self.BSIZE)

	def get_size(self):
		return len(self.cwrt_set) + len(self.rd_set) + self.get_nwrt_set_sz()
	
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

	def is_null(self):
		if self.etype == 'null':
			return True
		else:
			return False
