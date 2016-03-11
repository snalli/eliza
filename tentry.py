class tentry:

					
	c_write_ops = set(['PM_W'])
	c_read_ops  = set(['PM_R'])
	n_write_ops = set(['PM_I'])
	flush_ops   = set(['PM_L'])
	commit_ops  = set(['PM_C'])
	fence_ops   = set(['PM_N', 'PM_B'])
	tx_delims   = set(['PM_XS', 'PM_XE'])
	te_types    = set().union(
						c_write_ops,
						c_read_ops, 
						n_write_ops, 
						flush_ops,
					    commit_ops, 
					    fence_ops, 
					    tx_delims)
					    
	delims      = set().union(
						commit_ops,
						fence_ops, 
						tx_delims)
							
	def __init__(self):
		self.tid = 0
		self.time = 0.0
		self.te_type = 'INV'
		self.addr = '0x0'
		self.size = 0
		return None

	def get_types(self):
			return self.te_types
	
	def is_valid(self):
		if self.te_type != 'INV':
			return True
		else:
			return False
	
	def get_type(self):
		return self.te_type
		
	def set_type(self,te_type):
		self.te_type = te_type
		
	def set_tid(self, tid):
		self.tid = tid
		
	def set_time(self, time):
		self.time = time
	
	def set_addr(self, addr):
		self.addr = addr
	
	def set_size(self, size):
		self.size = size
		
	def te_list(self):
		l = []
		l.append(str(self.tid))
		l.append(str(self.time))
		l.append(self.te_type)
		l.append(str(self.addr))
		l.append(str(self.size))
	
		return l
		
	def need_arg(self):
		if self.te_type not in self.delims:
			return True
		else:
			return False
