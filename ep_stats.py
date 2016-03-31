from epoch import epoch
import numpypy
import numpy as np
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

	def insert_l(self, lst):
		if self.az is False:
			return
		
		eid = self.tno
		self.tno += 1
		etype = str(lst[0])
		esize  = float(lst[1])
		wsize  = float(lst[2])
		cwsize = float(lst[3])
		stime = float(lst[4])
		etime = float(lst[5])
		r1 = r2 = r3 = r4 = 0.0
		tid = lst[10]
		
		t =  (eid, etype, esize, wsize, cwsize,
		        stime, etime, r1, r2, r3 ,r4, tid)		
		
		self.buf.append(t) # Not buf += t
		self.buflen += 1;

	def insert(self, ep):
		if self.az is False:
			return
		etype = ep.get_epoch_type()
		if ep.is_null() is True:
			self.tnull += 1
			
		eid = self.tno
		self.tno += 1
		cwsize = ep.get_cwrt_set_sz()
		wsize  = float(cwsize) + ep.get_nwrt_set_sz()
		esize  = wsize + float(ep.get_rd_set_sz())
		stime = ep.get_start_time()
		etime = ep.get_end_time()
		tid = ep.get_tid()
		r1 = r2 = r3 = r4 = 0.0

		
		t =  (eid, etype, esize, wsize, cwsize,
		        stime, etime, r1, r2, r3 ,r4, tid)
		
		self.buf.append(t) # Not buf += t
		self.buflen += 1;

	def analyze(self):
		if self.az is False:
			return
		''' get 95-th percentile epoch size '''
		a = np.array([t[3] for t in self.buf])
		a = a[a != 0.0]
		p95 = np.percentile(a, 95)
		p5  = np.percentile(a, 5)
		med = np.median(a)
		avg_s = np.mean(a)
		max_sz = np.amax(a)
		min_sz = np.amin(a) # amino
		tot = self.buflen
		
		''' get avg duration in secs '''
		d = np.array([t[6]-t[5] for t in self.buf])
		avg_d = np.mean(d)
		
		f = open(self.fname, 'w')
		if f is not None :
			''' Better way of reporting stats ? '''
			f.write("DB                : "  + str(self.fname) + "\n")
			f.write("Total epochs      : "  + str(tot) + "\n")
			f.write("Total null epochs : "  + str(self.tnull) + "\n")
			f.write("Average duration  : "  + str(avg_d) + " secs \n")
			f.write("95-tile epoch size: "  + str(p95)   + "\n")
			f.write("5-tile epoch size : "  + str(p5)    + "\n")
			f.write("Median epoch size : "  + str(med) + "\n")
			f.write("Average epoch sz  : "  + str(avg_s) + "\n")
			f.write("Max epoch size    : "  + str(max_sz) + "\n")
			f.write("Min epoch size    : "  + str(min_sz) + "\n")
		
			f.close()
		
		
		
