"""Check cassandra cluster health via nodetool.
"""
from subprocess import Popen, PIPE
from collections import deque
import os.path
import re
import itertools
import math

def _fst(groups):
    if groups is not None and len(groups) > 0:
        return groups[0]
    else:
        return None

class Cassandra(object):    

    UNITS_FACTOR = {
         'bytes': 1,
         'KB': 1024,
         'MB': 1024**2,
         'GB': 1024**3,
         'TB': 1024**4 }


    @staticmethod
    def _find(lines, regex, postprocess=_fst, all=False):
        """Poor man's awk"""
        r = re.compile(regex)
        matches = [r.search(l) for l in lines if r.match(l)]
        res = [postprocess(m.groups()) for m in matches if m is not None and m.groups is not None]
        if all:
            return res
        else:
            if res is None or len(res) == 0:
                return None
            else:
                return res[0]


    def _parseInfoToken(self, lines):
        """
        Extract the token from the cassandra info

        v 0.7
        36299342986353445520010708318471778930

        v 0.8
        Token            : 51022655878160265769426795515063697984

         With order preserving partitioner
        Token            : Token(bytes[56713727820156410577229101240436610842])
        """

        # The first regex to match will return the token.
        regexes = deque([
            r"^(\d+)$",                     # Version 0.7
            r"Token.*\(bytes\[(\d+)\]\)",   # Version 0.8 with order preserving
            r"^Token[^:]+: ([0-9]+)$"       # Version 0.8
        ])

        token = None
        while not token and regexes:
            r = regexes.popleft()
            token = self._find(lines, r)

        if not token:
            raise Exception("Couldn't find token in:\n %s" % "\n".join(lines))

        # Convert token to a float since it does not fit in a 2**64 value.
        # The loss of precision does not really matter since a well-balanced cluster
        # will have markedly different tokens across all nodes.
        return float(token)

        
    def _parseInfo(self, info, results, logger):
        """
        v 0.7

        36299342986353445520010708318471778930
        Load             : 457.02 KB
        Generation No    : 1295816448
        Uptime (seconds) : 95
        Heap Memory (MB) : 521.86 / 1019.88

        v 0.8
        Token            : 51022655878160265769426795515063697984
        Gossip active    : True
        Load             : 283.87 GB
        Generation No    : 1331653944
        Uptime (seconds) : 188319
        Heap Memory (MB) : 2527.04 / 3830.00
        Data Center      : 283
        Rack             : 76
        Exceptions       : 0

        According to io/util/FileUtils.java units for load are:
        TB/GB/MB/KB/bytes
        """

        def convert_size(g):
            size, unit = g
            return str(int(float(size) * self. UNITS_FACTOR[unit]))
  
        lines = info.split("\n")

        try:
            results["token"] = self._parseInfoToken(lines)
        except:
            logger.exception("Unable to parse Cassandra token. Continuing. Stacktrace:")

        results["load"]     = float(Cassandra._find(lines, 
            r"^Load[^:]+:\s+([0-9.]+).*([KMGT]B|bytes)$", postprocess=convert_size))
        results["uptime"]   = int(Cassandra._find(lines, r"^Uptime[^:]+: (\d+)$"))
        
        heap = Cassandra._find(lines, r"^Heap Memory[^:]+: ([0-9.]+) / ([0-9.]+)$", postprocess=lambda g: g)
        results["heap_used"] = float(heap[0])
        results["heap_total"] = float(heap[1])

        e = Cassandra._find(lines, r"^Exceptions[^:]+: ([0-9]+)$")
        if e:
            results["exceptions"] = int(e)
        dc = Cassandra._find(lines, r"^Data Center[^:]+: ([0-9]+)$")
        if dc:
            results["datacenter"] = int(dc)
        r = Cassandra._find(lines, r"Rack[^:]+: ([0-9]+)$")
        if r:
            results["rack"] = int(r)

        return results

    @staticmethod    
    def _normalize(strings):
        """Replace capitalization and spacing by _"""
        res = []
        lastValid = False
        for string in strings:
            for c in string:
                if c.isalpha():
                    if c.isupper():
                        if lastValid:
                            res.append('_')
                            res.append(c.lower())
                            lastValid = False
                        else:
                            res.append(c.lower())
                    else:
                        lastValid = True
                        res.append(c)
                elif c.isspace():
                    if lastValid:
                        res.append('_')
                        lastValid = False
       
        return "".join(res)

    def _parseTpstats(self, cfstats, results):
        """
        Pool Name                    Active   Pending      Completed
        ReadStage                         0         0              1
        RequestResponseStage              0         0              0
        MutationStage                     0         0              3
        ReadRepair                        0         0              0
        GossipStage                       0         0              0
        AntiEntropyStage                  0         0              0
        MigrationStage                    0         0              0
        MemtablePostFlusher               0         0              2
        StreamStage                       0         0              0
        FlushWriter                       0         0              2
        MiscStage                         0         0              0
        FlushSorter                       0         0              0
        InternalResponseStage             0         0              0
        """

        
        lines = cfstats.split("\n")
        if len(lines) > 1:
            active, pending, completed = lines[0].lower().split()[-3:]
            for line in lines[1:]:
                stats = line.split()
                if len(stats) >= 4:
                    name = self._normalize(stats[:-3]) + '.'
                    results[name + active] = stats[-3]
                    results[name + pending] = stats[-2]
                    results[name + completed] = stats[-1]

        return results
        
    def _parseCfstats(self, tpstats, results):
        """
        ----------------
        Keyspace: Intake
        	Read Count: 0
        	Read Latency: NaN ms.
        	Write Count: 0
        	Write Latency: NaN ms.
        	Pending Tasks: 0
        		Column Family: Events
        		SSTable count: 3
        		Space used (live): 6623
        		Space used (total): 6623
        		Memtable Columns Count: 0
        		Memtable Data Size: 0
        		Memtable Switch Count: 0
        		Read Count: 0
        		Read Latency: NaN ms.
        		Write Count: 0
        		Write Latency: NaN ms.
        		Pending Tasks: 0
        		Key cache capacity: 200000
        		Key cache size: 0
        		Key cache hit rate: NaN
        		Row cache: disabled
        		Compacted row minimum size: 0
        		Compacted row maximum size: 372
        		Compacted row mean size: 103

        		Column Family: Encodings
        		SSTable count: 2
        		Space used (live): 19497
        		Space used (total): 19497
        		Memtable Columns Count: 0
        		Memtable Data Size: 0
        		Memtable Switch Count: 0
        		Read Count: 0
        		Read Latency: NaN ms.
        		Write Count: 0
        		Write Latency: NaN ms.
        		Pending Tasks: 0
        		Key cache capacity: 200000
        		Key cache size: 0
        		Key cache hit rate: NaN
        		Row cache: disabled
        		Compacted row minimum size: 149
        		Compacted row maximum size: 179
        		Compacted row mean size: 149
        """


        def indent(astr):
            return len(list(itertools.takewhile(str.isspace,astr)))

        def get_metric(line):
            """    metric name: val"""
            i = line.rfind(':')
            if i == -1:
                return None, None
            else:
                try:
                    val = line[i+1:].strip()
                    if val.endswith(" ms."):
                        val = val[:-4]
                    val = float(val)
                    if math.isnan(val):
                        return None, None

                    return self._normalize(line[:i]), val
                except:
                    return None, None

        keyspace = None
        cf = None
        
        lines = tpstats.split("\n")
        for line in lines:
            ind = indent(line)
            if line.find("Keyspace") != -1:
                keyspace = line.split()[1]
            elif line.find("Column Family") != -1:
                cf = line.split()[2]
            elif ind == 0:
                if cf is not None:
                    cf = None
                elif keyspace is not None:
                    keyspace = None
            elif ind == 2 and cf is not None:
                # Metric for a column family
                metric_name, val = get_metric(line)                
                if metric_name is not None and val is not None:
                    metric_name = metric_name + "." + keyspace + ":" + cf
                    results[metric_name] = val
            elif ind == 1 and keyspace is not None:
                # Metric for a keyspace
                metric_name, val = get_metric(line)                
                if metric_name is not None and val is not None:
                    metric_name = metric_name + "." + keyspace
                    results[metric_name] = val

        return results

    def check(self, logger, agentConfig):
        """Return a dictionary of metrics
        Or False to indicate that there are no data to report"""
        logger.debug('Cassandra: start')
        try:
            # How do we get to nodetool
            nodetool = agentConfig.get("cassandra_nodetool", None)
            if nodetool is None:
                return False
            else:
                if not os.path.exists(nodetool) or not os.path.isfile(nodetool):
                    logger.warn("Cassandra's nodetool cannot be found at %s" % (nodetool,))
                    return False
                
            # Connect to what?
            cassandra_host = agentConfig.get("cassandra_host", None)
            if cassandra_host is None:
                if nodetool is not None:
                    cassandra_host = "localhost"
                    logger.info("Nodetool is going to assume %s" % (cassandra_host))
                else:
                    return False
                    
            # A specific port, assume 8080 if none is given
            cassandra_port = agentConfig.get("cassandra_port", None)
            if cassandra_port is None:
                if nodetool is not None:
                    cassandra_port = 8080
                    logger.info("Nodetool is going to assume %s" % (cassandra_port))
                else:
                    return False
            
            nodetool_cmd = "%s -h %s -p %s" % (nodetool, cassandra_host, cassandra_port)
            logger.debug("Connecting to cassandra with: %s" % (nodetool_cmd,))
            bufsize = -1
            results = {}
            
            # nodetool info
            pipe = Popen("%s %s" % (nodetool_cmd, "info"), shell=True, universal_newlines=True, bufsize=bufsize, stdout=PIPE, stderr=None).stdout
            self._parseInfo(pipe.read(), results, logger)
            logger.debug("Cassandra info: %s" % results)
            pipe.close()
            
            # nodetool cfstats
            pipe = Popen("%s %s" % (nodetool_cmd, "cfstats"), shell=True, universal_newlines=True, bufsize=bufsize, stdout=PIPE, stderr=None).stdout
            self._parseCfstats(pipe.read(), results)
            pipe.close()
                                                
            # nodetool tpstats
            pipe = Popen("%s %s" % (nodetool_cmd, "tpstats"), shell=True, universal_newlines=True, bufsize=bufsize, stdout=PIPE, stderr=None).stdout
            self._parseTpstats(pipe.read(), results)                                
            pipe.close()
            
            return results
        except Exception, e:
            logger.exception(e)
            return False


if __name__ == "__main__":

    import logging
    c = Cassandra()
    c.check(logging,{'cassandra_nodetool': '/usr/local/cassandra/bin/nodetool',
                     'cassandra_host': 'localhost',
                     'cassandra_port': 8080,
                    })
