import sqlite3
class flow_table:
	def __init__(self, tname):
		self.tname = str(tname) + '_ft'
		self.dbname = self.tname + '.db'
		self.conn = sqlite3.connect(self.dbname)
		self.c = self.conn.cursor()
		self.c.execute('''create table if not exists '%s'
			(id text, cchain text,
			 primary key (id))''' % self.tname)

	def insert(self, cchain, tid, stime, etime):
		t =  (str(tid)+'.'+str(stime)+'.'+str(etime), cchain)
		tname = self.tname
		c = self.c
		try:
			c.execute("insert into '%s' values (?,?)" % tname, t)
		except:
			return None

	def commit(self):
		self.conn.commit()
