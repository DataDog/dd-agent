'''
Check the statistics from IBM Websphere MQ

See http://www-01.ibm.com/support/knowledgecenter/SSFKSJ_7.5.0/com.ibm.mq.ref.adm.doc/q086260_.htm
for MQSC command details
'''
#stdlib
import os, re, subprocess
from datetime import datetime, timedelta

# project
from checks import AgentCheck

class WebsphereMQ(AgentCheck):
    def check(self, instance):
        qmgr = instance['qmgr']
        self.log.debug('Getting metrics for queue manager ' + qmgr)
        
        mqscCommand = "runmqsc -e {0}".format(qmgr)
        managerTag = "manager:" + qmgr
        
        # does the manager exist and is it running?
        process = subprocess.Popen("dspmq.exe -m {0}".format(qmgr), stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = process.communicate()[0]
        if process.returncode == 0:
            # it exists - check status
            status = 0 if re.match(".*STATUS\(Running\)", result) is None else 1
            self.gauge("webspheremq.queuemanager.running", status, [managerTag])
            
            # if the manager isn't running then we can't get stats
            if status == 0:
                self.log.warning("Queue Manager {0} is not running. No metrics gathered".format(qmgr))
                return
        else:
            raise Exception("Queue Manager {0} does not exist".format(qmgr))

        # get queue manager stats
        process = subprocess.Popen(mqscCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = process.communicate("display qmstatus conns")[0]
        self.log.debug("display qmstatus returned " + result)
        
        queueData = re.findall(".*\n.*CONNS\((.*?)\)", result, re.M)
        for data in queueData:
            self.gauge("webspheremq.queuemanager.connections", data, [managerTag])

        # get channel stats
        process = subprocess.Popen(mqscCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = process.communicate("display chstatus(*)")[0]
        self.log.debug("display chstatus(*) returned " + result)
        
        queueData = re.findall(".*CHANNEL\((.*?)\).*CHLTYPE\((.*?)\).*\n.*\n" + 
            ".*STATUS\((.*?)\)", result, re.M)
        for data in queueData:
            tags = ["name:" + data[0], "type:" + data[1], managerTag]
            status = 1 if data[2] == "RUNNING" else 0
            self.gauge("webspheremq.channel.running", status, tags)

        # get queue defs
        process = subprocess.Popen(mqscCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = process.communicate("display queue(*) type maxdepth")[0]
        self.log.debug("display queue returned " + result)

        queueData = re.findall(".*QUEUE\((.*?)\).*TYPE\((.*?)\).*\n" + 
            ".*MAXDEPTH\((.*?)\)", result, re.M)
        queueDefs = dict()
        for data in queueData:
            queueName = data[0]
            tags = ["name:" + queueName, managerTag]
            queueDefs[queueName] = (data[1], data[2])
        
        # Get queue stats
        process = subprocess.Popen(mqscCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = process.communicate("display qstatus(*) all")[0]
        self.log.debug("display qstatus returned " + result)
        
        # parse output to pick up values of fields. Relies on field order remaining constant
        queueData = re.findall(".*QUEUE\((.*?)\).*\n" + 
            ".*CURDEPTH\((.*?)\).*IPPROCS\((.*?)\).*\n" +
            ".*LGETDATE\((.*?)\).*LGETTIME\((.*?)\).*\n" +
            ".*LPUTDATE\((.*?)\).*LPUTTIME\((.*?)\).*\n.*\n" +
            ".*MSGAGE\((.*?)\).*OPPROCS\((.*?)\).*\n" +
            ".*QTIME\((.*?),(.*?)\)", result, re.M)
        
        # log metric for each value
        for data in queueData:
            queueName = data[0]
            tags = ["name:" + queueName, managerTag]

            if queueName in queueDefs:
                tags.append("type:" + queueDefs[queueName][0])
                maxDepth = float(queueDefs[queueName][1])
                self.gauge("webspheremq.queue.max_depth", maxDepth, tags)
                self.gauge("webspheremq.queue.percent_depth", float(data[1]) / maxDepth, tags)

            self.gauge("webspheremq.queue.current_depth", data[1], tags)
            self.gauge("webspheremq.queue.open_input", data[2], tags)
            self.gauge("webspheremq.queue.open_output", data[8], tags)

            if len(data[7].strip()) > 0:
                self.gauge("webspheremq.queue.msgage_secs", data[7], tags)

            if len(data[9].strip()) > 0:
                self.gauge("webspheremq.queue.qtime_recent_microsecs", data[9], tags)
                self.gauge("webspheremq.queue.qtime_longer_microsecs", data[10], tags)
            
            if len(data[3].strip()) > 0:
                lastGet = datetime.strptime(data[3] + " " + data[4], "%Y-%m-%d %H.%M.%S")
                lastGetSecs = (datetime.utcnow() - lastGet).total_seconds()
                self.gauge("webspheremq.queue.last_get_millisecs", lastGetSecs * 1000, tags)

            if len(data[5].strip()) > 0:
                lastPut = datetime.strptime(data[5] + " " + data[6], "%Y-%m-%d %H.%M.%S")
                lastPutSecs = (datetime.utcnow() - lastPut).total_seconds()
                self.gauge("webspheremq.queue.last_put_millisecs", lastPutSecs * 1000, tags)

