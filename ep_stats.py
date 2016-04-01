from epoch import epoch
class ep_stats:

	''' Epoch stat collector '''
	def __init__(self, az, fname):
		self.az = az
		assert fname is not None
		# self.dbname = "db/" + dbname + ".db"
		# self.fname = "stat/" + dbname + ".stat"
		self.fname = fname
		self.buf = []
		self.buflen = 0
		self.tno = 0
		self.tnull = 0
	
	def get_tuple(self, ep):
		if self.az is False:
			return None
		etype = ep.get_epoch_type()
		if ep.is_null() is True:
			self.tnull += 1
			
		cwsize = ep.get_cwrt_set_sz()
		wsize  = float(cwsize) + ep.get_nwrt_set_sz()
		esize  = wsize + float(ep.get_rd_set_sz())
		stime = ep.get_start_time()
		etime = ep.get_end_time()
		tid = ep.get_tid()
		r1 = r2 = r3 = r4 = 0.0
		
		t =  (etype, esize, wsize, cwsize,
		        stime, etime, r1, r2, r3 ,r4, tid)
		
		return t
		
		
		
