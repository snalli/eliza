from epoch import epoch
import sqlite3
class etable:
	def __init__(self, name):
		assert name is not None
		self.tname = str(name)
		self.dbname = self.tname + '.db'
		self.conn = sqlite3.connect(self.dbname)
		self.c = self.conn.cursor()
		self.c.execute('''create table if not exists '%s'
			(id text, type text, csize integer, nsize integer, rsize integer,
			 stime real, etime real,
			 tid integer, primary key (id))''' % self.tname)

	def insert(self, ep):
		eid = str(ep.get_tid()) + '.' + str(ep.get_end_time())
		etype = ep.get_epoch_type()
		csize = ep.get_cwrt_set_sz()
		nsize = ep.get_nwrt_set_sz()
		rsize = ep.get_rd_set_sz()
		stime = ep.get_start_time()
		etime = ep.get_end_time()
		tid = ep.get_tid()
		c = self.c
		tname = self.tname

		t =  (eid, etype, csize, nsize, rsize,
		        stime, etime, tid)
		try:
			c.execute("insert into '%s' values (?,?,?,?,?,?,?,?)" % tname, t)
		except:
			return None

	def commit(self):
		self.conn.commit()

