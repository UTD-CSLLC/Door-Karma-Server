import logging
import MySQLdb
import time

#I do not claim to write beautiful code
def fixFormatString(fmt):
	final = ""
	inc = 0
	for part in fmt.split("%s"):
		final += part + "'{" + str(inc) + "}'"
		inc += 1
	return final[:-len(str("'{"+str(inc - 1)+"}'"))]

#Michael has signed off on not sanitizing inputs
class DoorKarmaDatabase:
	'''Front end to the door karma database
	Allows the middleware writer a much easier time interfacing with MySQL so that errors can be avoided '''

	def __init__(self, host, username, password, dbname, tablename):
		logging.info("Initializing database connection")
		try:
			self.db = MySQLdb.connect(host, username, password, dbname)
			logging.debug("Connected; Acquiring cursor")
			self.cur = self.db.cursor()
			logging.debug("Selecting database...")
			self.cur.execute("USE {0};".format(dbname))
			logging.debug("Successfully selected")
		except MySQLdb.OperationalError, e:
			logging.critical("Database error: {0}".format(str(e)))
			raise e
		self.tablename = tablename
		self.fromuuidToID = dict()

	def closeConnection(self):
		'''This will immediately close the database connection. Call on cleanup'''

		logging.info("Closing database connection")
		self.db.close()

	def userRequest(self, fromuuid, submitterName, submitterPlatform, submitterVersion):
		"""Adds a new user request log to the database for later finishing. Stores the request ID into the dict"""

		logging.info("User {0} ({1}::{2}) requested".format(
			submitterName, submitterPlatform, submitterVersion))
		cmd = "INSERT INTO " + self.tablename + " (rFrom, platSubType, platSubVer, platSubUUID) VALUES(%s, %s, %s, %s);"
		try:
			logging.debug("About to execute \n{0}".format(fixFormatString(cmd).format(submitterName, submitterPlatform, submitterVersion, fromuuid)))
			self.cur.execute(cmd, (submitterName, submitterPlatform, submitterVersion, fromuuid))
			logging.debug("Successfully executed; Committing")
			self.db.commit()
			logging.debug("Committed")
		except MySQLdb.OperationalError, e:
			logging.debug("Commit failed; Rolling back")
			self.db.rollback()
			logging.critical("Database error: {0}".format(str(e)))
			raise e
		self.fromuuidToID[fromuuid] = self.cur.lastrowid

	def userFilled(self, fromuuid, byuuid, fillerName, fillerPlatform, fillerVersion):
		"""Fills the user request from before with the remaining information"""

		logging.info("User {0} is filling {1}'s request ({2}::{3})".format(
			byuuid, fromuuid, fillerPlatform, fillerVersion))
		cmd = "UPDATE " + self.tablename + " SET rFill=%s, tFill=NOW(), platFillType=%s, platFillVer=%s, platFillUUID=%s WHERE eventNumber=%s;"
		try:
			logging.debug("About to execute \"{0}\"".format(fixFormatString(cmd).format(fillerName, fillerPlatform, fillerVersion, byuuid, self.fromuuidToID[fromuuid])))
			self.cur.execute(cmd, (fillerName, fillerPlatform, fillerVersion, byuuid, self.fromuuidToID[fromuuid]))
			logging.debug("Successfully executed; Committing")
			self.db.commit()
			logging.debug("Committed")
		except MySQLdb.OperationalError, e:
			logging.debug("Commit failed; Rolling back")
			self.db.rollback()
			logging.critical("Database error: {0}".format(str(e)))
			raise e

	def dumpData(self):
		try:
			logging.debug("About to dump the database!")
			self.cur.execute("SELECT * FROM " + self.tablename + " WHERE 1")
			logging.debug("Successfully dumped; Returning")
			return self.cur.fetchall()
		except MySQLdb.OperationalError, e:
			logging.debug("Select failed")
			logging.critical("Database error: {0}".format(str(e)))
			raise e