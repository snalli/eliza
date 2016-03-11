from tentry import tentry
class ftread:
	
	delim = ':'
	
	def __init__(self):
		return None
	
	def get_tentry(self, tl):
		assert tl is not None
		te = tentry()
		
		for te_type in te.te_types:
			if te_type in tl:
				te.set_type(te_type)
				break
				
		if te.is_valid() is False:
			del te
			return None
		
		l = tl.split()
		__l = l[5].split(':')
		
		te.set_tid(int(l[0].split('-')[1]))		
		te.set_time(float(l[3].split(':')[0]))
		
		if te.need_arg() is True:
			te.set_addr(__l[1])
			te.set_size(int(__l[2]))
				
		return te
