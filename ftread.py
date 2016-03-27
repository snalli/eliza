from tentry import tentry
class ftread:
	
	delim = ':'
	
	def __init__(self):
		return None
	
	def get_tentry(self, tl):
		assert tl is not None
		te = tentry()
		te_types = te.get_types()
		
		for te_type in te_types:
			if te_type in tl:
				te.set_type(te_type)
				break
				
		if te.is_valid() is False:
			del te
			return None
		
		l = tl.split()
		try:
			l0 = l[0].split('-')
			te.set_tid(int(l0[len(l0)-1]))		
			te.set_time(float(l[3].split(':')[0]))
		except:
			return None
		
		
		if te.is_valid() is True:
			#te.set_callee(l[4].split(':')[0])
			
			__l = l[5].split(':')	
			if te.need_arg() is True:
				te.set_addr(__l[1])
				te.set_size(int(__l[2]))
		else:
			te.set_callee(l[4])
			te.set_caller(l[5].split('-')[1])
							
		return te
