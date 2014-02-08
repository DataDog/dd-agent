from checks import AgentCheck

class Gearman(AgentCheck):

    def get_library_versions(self):
        try:
            import gearman
            version = gearman.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"gearman": version}

    def _get_client(self,host,port):
        try:
            import gearman
        except ImportError:
            raise Exception("Cannot import Gearman module. Check the instructions to install this module at https://app.datadoghq.com/account/settings#integrations/gearman")

        self.log.debug("Connecting to gearman at address %s:%s" % (host, port))
        return gearman.GearmanAdminClient(["%s:%s" %
            (host, port)])

    def _get_metrics(self, client, tags):
        data = client.get_status()
        running = 0
        queued = 0
        workers = 0
        
        for stat in data:
            running += stat['running']
            queued += stat['queued']
            workers += stat['workers']

        unique_tasks = len(data)

        self.gauge("gearman.unique_tasks", unique_tasks, tags=tags)
        self.gauge("gearman.running", running, tags=tags)
        self.gauge("gearman.queued", queued, tags=tags)
        self.gauge("gearman.workers", workers, tags=tags)

        self.log.debug("running %d, queued %d, unique tasks %d, workers: %d"
        % (running, queued, unique_tasks, workers))

    def _get_conf(self, instance):
        host = instance.get('server', None)
        port = instance.get('port', None)

        if host is None:
            self.warning("Host not set, assuming 127.0.0.1")
            host = "127.0.0.1"

        if port is None:
            self.warning("Port is not set, assuming 4730")
            port = 4730

        tags = instance.get('tags', [])

        return host, port, tags

    def check(self, instance):
        self.log.debug("Gearman check start")

        host, port, tags = self._get_conf(instance)
        client = self._get_client(host, port)
        self.log.debug("Connected to gearman")
        self._get_metrics(client, tags)
