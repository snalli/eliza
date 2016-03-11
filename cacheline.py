class cacheline:
	"""Cacheline"""
	cstates = set(['clean', 'dirty', 'invalid'])
	
	def __init__(self, addr):
		self.addr = addr
		self.state = 'invalid'
		assert self.addr is not None
		assert self.state in cstates
		
	def get_addr(self):
		return self.addr
	
	def get_state(self):
		assert self.state in cstates
		return self.state
		
	def set_state(self, state):
		assert state in cstates
		assert self.state in cstates
		self.state = state
