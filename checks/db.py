import httplib
import traceback
import urllib2

class CouchDb(object):
	def check(self, logger, agentConfig):
		logger.debug('getCouchDBStatus: start')

		if ('CouchDBServer' not in agentConfig or agentConfig['CouchDBServer'] == ''):
			logger.debug('getCouchDBStatus: config not set')
			return False

		logger.debug('getCouchDBStatus: config set')

		# The dictionary to be returned.
		couchdb = {'stats': None, 'databases': {}}

		# First, get overall statistics.
		endpoint = '/_stats/'

		try:
			url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
			logger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			logger.error('Unable to get CouchDB statistics - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			logger.error('Unable to get CouchDB statistics - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			logger.error('Unable to get CouchDB statistics - HTTPException = ' + str(e))
			return False

		except Exception, e:
			logger.error('Unable to get CouchDB statistics - Exception = ' + traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				logger.debug('getCouchDBStatus: json read')
				stats = json.loads(response)

			else:
				logger.debug('getCouchDBStatus: minjson read')
				stats = minjson.safeRead(response)

		except Exception, e:
			import traceback
			logger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
			return False

		couchdb['stats'] = stats

		# Next, get all database names.
		endpoint = '/_all_dbs/'

		try:
			url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
			logger.debug('getCouchDBStatus: attempting urlopen')
			req = urllib2.Request(url, None, headers)

			# Do the request, log any errors
			request = urllib2.urlopen(req)
			response = request.read()
		except urllib2.HTTPError, e:
			logger.error('Unable to get CouchDB status - HTTPError = ' + str(e))
			return False

		except urllib2.URLError, e:
			logger.error('Unable to get CouchDB status - URLError = ' + str(e))
			return False

		except httplib.HTTPException, e:
			logger.error('Unable to get CouchDB status - HTTPException = ' + str(e))
			return False

		except Exception, e:
			logger.error('Unable to get CouchDB status - Exception = ' + traceback.format_exc())
			return False

		try:

			if int(pythonVersion[1]) >= 6:
				logger.debug('getCouchDBStatus: json read')
				databases = json.loads(response)

			else:
				logger.debug('getCouchDBStatus: minjson read')
				databases = minjson.safeRead(response)

		except Exception, e:
			logger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
			return False

		for dbName in databases:
			endpoint = '/%s/' % dbName

			try:
				url = '%s%s' % (agentConfig['CouchDBServer'], endpoint)
				logger.debug('getCouchDBStatus: attempting urlopen')
				req = urllib2.Request(url, None, headers)

				# Do the request, log any errors
				request = urllib2.urlopen(req)
				response = request.read()
			except urllib2.HTTPError, e:
				logger.error('Unable to get CouchDB database status - HTTPError = ' + str(e))
				return False

			except urllib2.URLError, e:
				logger.error('Unable to get CouchDB database status - URLError = ' + str(e))
				return False

			except httplib.HTTPException, e:
				logger.error('Unable to get CouchDB database status - HTTPException = ' + str(e))
				return False

			except Exception, e:
				import traceback
				logger.error('Unable to get CouchDB database status - Exception = ' + traceback.format_exc())
				return False

			try:

				if int(pythonVersion[1]) >= 6:
					logger.debug('getCouchDBStatus: json read')
					couchdb['databases'][dbName] = json.loads(response)

				else:
					logger.debug('getCouchDBStatus: minjson read')
					couchdb['databases'][dbName] = minjson.safeRead(response)

			except Exception, e:
				import traceback
				logger.error('Unable to load CouchDB database JSON - Exception = ' + traceback.format_exc())
				return False

		logger.debug('getCouchDBStatus: completed, returning')
		return couchdb

class MongoDb(object):
	def __init__(self):
		self.mongoDBStore = None
	
	def check(self, logger, agentConfig):
		logger.debug('getMongoDBStatus: start')

		if 'MongoDBServer' not in agentConfig or agentConfig['MongoDBServer'] == '':
			logger.debug('getMongoDBStatus: config not set')
			return False

		logger.debug('getMongoDBStatus: config set')

		try:
			import pymongo
			from pymongo import Connection
		except ImportError:
			logger.error('Unable to import pymongo library')
			return False

		# The dictionary to be returned.
		mongodb = {}

		try:
			mongoInfo = agentConfig['MongoDBServer'].split(':')
			if len(mongoInfo) == 2:
				conn = Connection(mongoInfo[0], int(mongoInfo[1]))
			else:
				conn = Connection(mongoInfo[0])
		except Exception, ex:
			import traceback
			logger.error('Unable to connect to MongoDB server - Exception = ' + traceback.format_exc())
			return False

		# Older versions of pymongo did not support the command()
		# method below.
		try:
			dbName = 'local'
			db = conn[dbName]
			status = db.command('serverStatus') # Shorthand for {'serverStatus': 1}
			# If these keys exist, remove them for now as they cannot be serialized
			try:
				status['backgroundFlushing'].pop('last_finished')
			except KeyError:
				pass
			try:
				status.pop('localTime')
			except KeyError:
				pass

			if self.mongoDBStore == None:
				logger.debug('getMongoDBStatus: no cached data, so storing for first time')
				self._clearMongoDBStatus(status)
			else:
				logger.debug('getMongoDBStatus: cached data exists, so calculating per sec metrics')
				accessesPS = float(status['indexCounters']['btree']['accesses'] - self.mongoDBStore['indexCounters']['btree']['accesses']) / 60
				
				if accessesPS >= 0:
					status['indexCounters']['btree']['accessesPS'] = accessesPS
					status['indexCounters']['btree']['hitsPS'] = float(status['indexCounters']['btree']['hits'] - self.mongoDBStore['indexCounters']['btree']['hits']) / 60
					status['indexCounters']['btree']['missesPS'] = float(status['indexCounters']['btree']['misses'] - self.mongoDBStore['indexCounters']['btree']['misses']) / 60
					status['indexCounters']['btree']['missRatioPS'] = float(status['indexCounters']['btree']['missRatio'] - self.mongoDBStore['indexCounters']['btree']['missRatio']) / 60
					status['opcounters']['insertPS'] = float(status['opcounters']['insert'] - self.mongoDBStore['opcounters']['insert']) / 60
					status['opcounters']['queryPS'] = float(status['opcounters']['query'] - self.mongoDBStore['opcounters']['query']) / 60
					status['opcounters']['updatePS'] = float(status['opcounters']['update'] - self.mongoDBStore['opcounters']['update']) / 60
					status['opcounters']['deletePS'] = float(status['opcounters']['delete'] - self.mongoDBStore['opcounters']['delete']) / 60
					status['opcounters']['getmorePS'] = float(status['opcounters']['getmore'] - self.mongoDBStore['opcounters']['getmore']) / 60
					status['opcounters']['commandPS'] = float(status['opcounters']['command'] - self.mongoDBStore['opcounters']['command']) / 60
					status['asserts']['regularPS'] = float(status['asserts']['regular'] - self.mongoDBStore['asserts']['regular']) / 60
					status['asserts']['warningPS'] = float(status['asserts']['warning'] - self.mongoDBStore['asserts']['warning']) / 60
					status['asserts']['msgPS'] = float(status['asserts']['msg'] - self.mongoDBStore['asserts']['msg']) / 60
					status['asserts']['userPS'] = float(status['asserts']['user'] - self.mongoDBStore['asserts']['user']) / 60
					status['asserts']['rolloversPS'] = float(status['asserts']['rollovers'] - self.mongoDBStore['asserts']['rollovers']) / 60
				else:
					logger.debug('getMongoDBStatus: negative value calculated, mongod likely restarted, so clearing cache')
					self._clearMongoDBStatus(status)

			self.mongoDBStore = status
			mongodb = status
		except Exception, ex:
			import traceback
			logger.error('Unable to get MongoDB status - Exception = ' + traceback.format_exc())
			return False

		logger.debug('getMongoDBStatus: completed, returning')
		return mongodb


	def _clearMongoDBStatus(self, status):
		status['indexCounters']['btree']['accessesPS'] = 0
		status['indexCounters']['btree']['hitsPS'] = 0
		status['indexCounters']['btree']['missesPS'] = 0
		status['indexCounters']['btree']['missRatioPS'] = 0
		status['opcounters']['insertPS'] = 0
		status['opcounters']['queryPS'] = 0
		status['opcounters']['updatePS'] = 0
		status['opcounters']['deletePS'] = 0
		status['opcounters']['getmorePS'] = 0
		status['opcounters']['commandPS'] = 0
		status['asserts']['regularPS'] = 0
		status['asserts']['warningPS'] = 0
		status['asserts']['msgPS'] = 0
		status['asserts']['userPS'] = 0
		status['asserts']['rolloversPS'] = 0


class MySql(object):
	def __init__(self):
		self.mysqlVersion = None
		self.mysqlConnectionsStore = None
		self.mysqlSlowQueriesStore = None
	
	def check(self, logger, agentConfig):
		logger.debug('getMySQLStatus: start')
		
		if 'MySQLServer' in agentConfig and 'MySQLUser' in agentConfig and agentConfig['MySQLServer'] != '' and agentConfig['MySQLUser'] != '':
		
			logger.debug('getMySQLStatus: config')
			
			# Try import MySQLdb - http://sourceforge.net/projects/mysql-python/files/
			try:
				import MySQLdb
			
			except ImportError, e:
				logger.debug('getMySQLStatus: unable to import MySQLdb')
				return False
				
			# Connect
			try:
				db = MySQLdb.connect(agentConfig['MySQLServer'], agentConfig['MySQLUser'], agentConfig['MySQLPass'])
				
			except MySQLdb.OperationalError, message:
				
				logger.debug('getMySQLStatus: MySQL connection error: ' + str(message))
				return False
			
			logger.debug('getMySQLStatus: connected')
			
			# Get MySQL version
			if self.mysqlVersion == None:
			
				logger.debug('getMySQLStatus: mysqlVersion unset storing for first time')
				
				try:
					cursor = db.cursor()
					cursor.execute('SELECT VERSION()')
					result = cursor.fetchone()
					
				except MySQLdb.OperationalError, message:
				
					logger.debug('getMySQLStatus: MySQL query error when getting version: ' + str(message))
			
				version = result[0].split('-') # Case 31237. Might include a description e.g. 4.1.26-log. See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
				version = version[0].split('.')
				self.mysqlVersion = version
			
			logger.debug('getMySQLStatus: getting Connections')
			
			# Connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Connections"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Connections: ' + str(message))
		
			if self.mysqlConnectionsStore == None:
				
				logger.debug('getMySQLStatus: mysqlConnectionsStore unset storing for first time')
				
				self.mysqlConnectionsStore = result[1]
				
				connections = 0
				
			else:
		
				logger.debug('getMySQLStatus: mysqlConnectionsStore set so calculating')
				logger.debug('getMySQLStatus: self.mysqlConnectionsStore = ' + str(self.mysqlConnectionsStore))
				logger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				connections = float(float(result[1]) - float(self.mysqlConnectionsStore)) / 60
				
				self.mysqlConnectionsStore = result[1]
				
			logger.debug('getMySQLStatus: connections = ' + str(connections))
			
			logger.debug('getMySQLStatus: getting Connections - done')
			
			logger.debug('getMySQLStatus: getting Created_tmp_disk_tables')
				
			# Created_tmp_disk_tables
			
			# Determine query depending on version. For 5.02 and above we need the GLOBAL keyword (case 31015)
			if int(self.mysqlVersion[0]) >= 5 and int(self.mysqlVersion[2]) >= 2:
				query = 'SHOW GLOBAL STATUS LIKE "Created_tmp_disk_tables"'
				
			else:
				query = 'SHOW STATUS LIKE "Created_tmp_disk_tables"'
			
			try:
				cursor = db.cursor()
				cursor.execute(query)
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Created_tmp_disk_tables: ' + str(message))
		
			createdTmpDiskTables = float(result[1])
				
			logger.debug('getMySQLStatus: createdTmpDiskTables = ' + str(createdTmpDiskTables))
			
			logger.debug('getMySQLStatus: getting Created_tmp_disk_tables - done')
			
			logger.debug('getMySQLStatus: getting Max_used_connections')
				
			# Max_used_connections
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Max_used_connections"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Max_used_connections: ' + str(message))
				
			maxUsedConnections = result[1]
			
			logger.debug('getMySQLStatus: maxUsedConnections = ' + str(createdTmpDiskTables))
			
			logger.debug('getMySQLStatus: getting Max_used_connections - done')
			
			logger.debug('getMySQLStatus: getting Open_files')
			
			# Open_files
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Open_files"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Open_files: ' + str(message))
				
			openFiles = result[1]
			
			logger.debug('getMySQLStatus: openFiles = ' + str(openFiles))
			
			logger.debug('getMySQLStatus: getting Open_files - done')
			
			logger.debug('getMySQLStatus: getting Slow_queries')
			
			# Slow_queries
			
			# Determine query depending on version. For 5.02 and above we need the GLOBAL keyword (case 31015)
			if int(self.mysqlVersion[0]) >= 5 and int(self.mysqlVersion[2]) >= 2:
				query = 'SHOW GLOBAL STATUS LIKE "Slow_queries"'
				
			else:
				query = 'SHOW STATUS LIKE "Slow_queries"'
				
			try:
				cursor = db.cursor()
				cursor.execute(query)
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Slow_queries: ' + str(message))
		
			if self.mysqlSlowQueriesStore == None:
				
				logger.debug('getMySQLStatus: mysqlSlowQueriesStore unset so storing for first time')
				
				self.mysqlSlowQueriesStore = result[1]
				
				slowQueries = 0
				
			else:
		
				logger.debug('getMySQLStatus: mysqlSlowQueriesStore set so calculating')
				logger.debug('getMySQLStatus: self.mysqlSlowQueriesStore = ' + str(self.mysqlSlowQueriesStore))
				logger.debug('getMySQLStatus: result = ' + str(result[1]))
				
				slowQueries = float(float(result[1]) - float(self.mysqlSlowQueriesStore)) / 60
				
				self.mysqlSlowQueriesStore = result[1]
				
			logger.debug('getMySQLStatus: slowQueries = ' + str(slowQueries))
			
			logger.debug('getMySQLStatus: getting Slow_queries - done')
			
			logger.debug('getMySQLStatus: getting Table_locks_waited')
				
			# Table_locks_waited
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Table_locks_waited"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Table_locks_waited: ' + str(message))
		
			tableLocksWaited = float(result[1])
				
			logger.debug('getMySQLStatus: tableLocksWaited = ' + str(tableLocksWaited))
			
			logger.debug('getMySQLStatus: getting Table_locks_waited - done')
			
			logger.debug('getMySQLStatus: getting Threads_connected')
				
			# Threads_connected
			try:
				cursor = db.cursor()
				cursor.execute('SHOW STATUS LIKE "Threads_connected"')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting Threads_connected: ' + str(message))
				
			threadsConnected = result[1]
			
			logger.debug('getMySQLStatus: threadsConnected = ' + str(threadsConnected))
			
			logger.debug('getMySQLStatus: getting Threads_connected - done')
			
			logger.debug('getMySQLStatus: getting Seconds_Behind_Master')
			
			# Seconds_Behind_Master
			try:
				cursor = db.cursor(MySQLdb.cursors.DictCursor)
				cursor.execute('SHOW SLAVE STATUS')
				result = cursor.fetchone()
				
			except MySQLdb.OperationalError, message:
			
				logger.debug('getMySQLStatus: MySQL query error when getting SHOW SLAVE STATUS: ' + str(message))
				result = None
			
			if result != None:
				try:
					secondsBehindMaster = result['Seconds_Behind_Master']
				
					logger.debug('getMySQLStatus: secondsBehindMaster = ' + str(secondsBehindMaster))
					
				except IndexError, e:					
					secondsBehindMaster = None
					
					logger.debug('getMySQLStatus: secondsBehindMaster empty')
			
			else:
				secondsBehindMaster = None
				
				logger.debug('getMySQLStatus: secondsBehindMaster empty')
			
			logger.debug('getMySQLStatus: getting Seconds_Behind_Master - done')
			
			return {'connections' : connections, 'createdTmpDiskTables' : createdTmpDiskTables, 'maxUsedConnections' : maxUsedConnections, 'openFiles' : openFiles, 'slowQueries' : slowQueries, 'tableLocksWaited' : tableLocksWaited, 'threadsConnected' : threadsConnected, 'secondsBehindMaster' : secondsBehindMaster}

		else:			
			
			logger.debug('getMySQLStatus: config not set')
			return False	
			
		