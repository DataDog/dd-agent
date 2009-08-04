'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2009 all rights reserved
'''
	
#
# Argument checks
#
import sys

if len(sys.argv) != 5:
	print 'Usage: python sd-deploy.py [API URL] [subdomain] [username] [password]'
	sys.exit(2)	

#
# Get server details
#

import socket	

# IP
try:
	serverIp = socket.gethostbyname(socket.gethostname())
	
except socket.error, e:
	print 'Unable to get server IP: ' + str(e)
	sys.exit(2)
	
# Hostname
try:
	serverHostname = hostname = socket.getfqdn()
	
except socket.error, e:
	print 'Unable to get server hostname: ' + str(e)
	sys.exit(2)

#
# Get latest agent version
#

print '1/: Downloading latest agent version';
		
import httplib
import urllib2

# Request details
try: 
	requestAgent = urllib2.urlopen('http://www.serverdensity.com/agentupdate/')
	responseAgent = requestAgent.read()
	
except urllib2.HTTPError, e:
	print 'Unable to get latest version info - HTTPError = ' + str(e)
	sys.exit(2)
	
except urllib2.URLError, e:
	print 'Unable to get latest version info - URLError = ' + str(e)
	sys.exit(2)
	
except httplib.HTTPException, e:
	print 'Unable to get latest version info - HTTPException'
	sys.exit(2)
	
except Exception, e:
	import traceback
	print 'Unable to get latest version info - Exception = ' + traceback.format_exc()
	sys.exit(2)

#
# Define downloader function
#

import md5 # I know this is depreciated, but we still support Python 2.4 and hashlib is only in 2.5. Case 26918
import urllib

def downloadFile(agentFile, recursed = False):
	print 'Downloading ' + agentFile['name']
	
	downloadedFile = urllib.urlretrieve('http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name'])
	
	# Do md5 check to make sure the file downloaded properly
	checksum = md5.new()
	f = file(downloadedFile[0], 'rb')
	
	# Although the files are small, we can't guarantee the available memory nor that there
	# won't be large files in the future, so read the file in small parts (1kb at time)
	while True:
		part = f.read(1024)
		
		if not part: 
			break # end of file
	
		checksum.update(part)
		
	f.close()
	
	# Do we have a match?
	if checksum.hexdigest() == agentFile['md5']:
		return downloadedFile[0]
		
	else:
		# Try once more
		if recursed == False:
			downloadFile(agentFile, True)
		
		else:
			print agentFile['name'] + ' did not match its checksum - it is corrupted. This may be caused by network issues so please try again in a moment.'
			sys.exit(2)

#
# Install the agent files
#

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
import platform

pythonVersion = platform.python_version_tuple()

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		updateInfo = json.loads(responseAgent)
	except Exception, e:
		print 'Unable to get latest version info. Try again later.'
		sys.exit(2)
	
else:
	import minjson
	
	try:
		updateInfo = minjson.safeRead(responseAgent)
	except Exception, e:
		print 'Unable to get latest version info. Try again later.'
		sys.exit(2)

# Loop through the new files and call the download function
for agentFile in updateInfo['files']:
	agentFile['tempFile'] = downloadFile(agentFile)			

# If we got to here then everything worked out fine. However, all the files are still in temporary locations so we need to move them
import os
import shutil # Prevents [Errno 18] Invalid cross-device link (case 26878) - http://mail.python.org/pipermail/python-list/2005-February/308026.html

os.mkdir('sd-agent')

for agentFile in updateInfo['files']:
	print 'Installing ' + agentFile['name']
	
	if agentFile['name'] != 'config.cfg':
		shutil.move(agentFile['tempFile'], 'sd-agent/' + agentFile['name'])
	
print 'Agent files downloaded'

#
# Call API to add new server
#

print '2/: Adding new server'

# Build API payload
import time
timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

#
#
# REMOVE THIS LINE
#
#
serverIp = '10.0.0.14'

postData = urllib.urlencode({'name' : serverHostname, 'ip' : serverIp, 'notes' : 'Added by sd-deploy: ' + timestamp })

# Send request
try: 	
	# Password manager
	mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
	mgr.add_password(None, sys.argv[1] + '/1.0/', sys.argv[3], sys.argv[4])
	opener = urllib2.build_opener(urllib2.HTTPBasicAuthHandler(mgr), urllib2.HTTPDigestAuthHandler(mgr))
	
	urllib2.install_opener(opener)
	
	# Build the request handler
	requestAdd = urllib2.Request(sys.argv[1] + '/1.0/?account=' + sys.argv[2] + '&c=servers/add', postData, { 'User-Agent' : 'Server Density Deploy' })
	
	# Do the request, log any errors
	responseAdd = urllib2.urlopen(requestAdd)
	
	readAdd = responseAdd.read()
		
except urllib2.HTTPError, e:
	print 'HTTPError = ' + str(e)
	
except urllib2.URLError, e:
	print 'URLError = ' + str(e)
	
except httplib.HTTPException, e: # Added for case #26701
	print 'HTTPException' + str(e)
		
except Exception, e:
	import traceback
	print 'Exception = ' + traceback.format_exc()

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		serverInfo = json.loads(readAdd)
	except Exception, e:
		print 'Unable to add server.'
		sys.exit(2)
	
else:
	import minjson
	
	try:
		serverInfo = minjson.safeRead(readAdd)
	except Exception, e:
		print 'Unable to add server.'
		sys.exit(2)
		
print 'Server added - ID: ' + str(serverInfo['data']['serverId'])

#
# Write config file
#

print '3/: Writing config file'

configCfg = '[Main]\nsd_url: http://' + sys.argv[2] + '\nagent_key: ' + serverInfo['data']['agentKey'] + '\napache_status_url: http://www.example.com/server-status/?auto'

try:
	f = open('sd-agent/config.cfg', 'w')
	f.write(configCfg)
	f.close()

except Exception, e:
	import traceback
	print 'Exception = ' + traceback.format_exc()

print 'Config file written'