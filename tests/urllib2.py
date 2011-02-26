class Request(object):
    apache_status = """Total Accesses: 456
Total kBytes: 12345
Uptime: 3
CPULoad: .00817439
ReqPerSec: 1.4
BytesPerSec: 2342.3
BusyWorkers: 1
IdleWorkers: 15
Scoreboard: W_______________................................................................................................................................................................................................................................................................................................................................................................................................"""
    nginx_status = """Active connections: 8 
server accepts handled requests
 1184286 1184286 4568412 
Reading: 0 Writing: 1 Waiting: 7"""

    def __init__(self, nginxOrApache, param1, param2):
        "nginxOrApache should be 'nginx' or 'apache'"
        self.nginxOrApache = nginxOrApache

    def read(self):
        if self.nginxOrApache == "nginx":
            return self.nginx_status
        elif self.nginxOrApache == "apache":
            return self.apache_status
        else:
            raise Exception("Unsupported web server")

def urlopen(req):
    "Pretend to read from the network"
    return req
        
