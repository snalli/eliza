from tentry import tentry
import sys
class ftread:
	
	delim = ':'
	
	def __init__(self, pid, n):
		self.pid = pid
		self.n = n
		self.te = tentry()
		self.te_pm_ref = list(self.te.get_pm_ref())
		self.other_te_types = list(self.te.get_types() - self.te.get_pm_ref())
		return None
	
	def get_tentry(self, tl):
		assert tl is not None
		te = tentry()

		for te_type in self.te_pm_ref:
			if te_type in tl:
				te.set_type(te_type)
				break
		
		if te.is_valid() is False:
			for te_type in self.other_te_types:
				if te_type in tl:
					te.set_type(te_type)
					break
				
		if te.is_valid() is False:
			return None

		l = tl.split()
		l0 = l[0].split('-')
		te.set_tid(int(l0[len(l0)-1]))
		if te.get_tid() % self.n != self.pid:
			del te
			return None
			
		te.set_time(float(l[3].split(':')[0]))
		te.set_callee(l[4].split(':')[0])
			
		if te.need_arg():
			__l = l[5].split(':')	
			te.set_addr(__l[1])
			te.set_size(int(__l[2]))
		#else:
		#	te.set_callee(l[4])
			# te.set_caller(l[5].split('-')[1])
					
		return te
