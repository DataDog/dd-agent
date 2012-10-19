from checks.services_checks import ServicesCheck, Status, EventType
import socket
import time

class BadConfException(Exception): pass

class TCPCheck(ServicesCheck):

    def _load_conf(self, instance):
        # Fetches the conf

        port = instance.get('port', None)
        timeout = int(instance.get('timeout', 10))
        socket_type = None
        try:
            port = int(port)
        except Exception:
            raise BadConfException("%s is not a correct port." % str(port))

        try:
            url = instance.get('host', None)
            split = url.split(":")
        except Exception: # Would be raised if url is not a string 
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8: # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6
            
        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                raise BadConfException("URL: %s is not a correct IPv4, IPv6 or hostname" % addr)

        return addr, port, socket_type, timeout

    def _check(self, instance):

        addr, port, socket_type, timeout = self._load_conf(instance)
        try:    
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except Exception, e:
            self.log.info("%s:%s is down" % (addr, port))
            return Status.DOWN, str(e)

        self.log.info("%s:%s is UP" % (addr, port))
        return Status.UP, "UP"


    def _create_status_event(self, status, msg, instance):
        # Get the instance settings
        host = instance.get('host', None)
        port = instance.get('port', None)
        name = instance.get('name', None)
        
        # Get a custom message that will be displayed in the event
        custom_message = instance.get('message', "")
        if custom_message:
            custom_message += " \n"
        

        # Let the possibility to override the source type name
        instance_source_type_name = instance.get('source_type', None)
        if instance_source_type_name is None:
            source_type = "%s.%s" % (ServicesCheck.SOURCE_TYPE_NAME, name)
        else:
            source_type = "%s.%s" % (ServicesCheck.SOURCE_TYPE_NAME, instance_source_type_name)
        

        # Get the handles you want to notify
        notify = instance.get('notify', self.init_config.get('notify', []))
        notify_message = ""
        if notify:
            notify_list = []
            for handle in notify:
                notify_list.append("@%s" % handle.strip())
            notify_message = " ".join(notify_list) + " \n"


        if status == Status.DOWN:
            title = "[Alert] %s is down" % name
            alert_type = "error"
            msg = "%s %s %s reported that %s (%s:%s) failed with %s" % (notify_message,
                custom_message, self.hostname, name, host, port, msg)
            event_type = EventType.DOWN

        else: # Status is UP
            title = "[Recovered] %s is up" % name
            alert_type = "success"
            msg = "%s %s %s reported that %s (%s:%s) recovered" % (notify_message,
                custom_message, self.hostname, name, host, port)
            event_type = EventType.UP

        return {
             'timestamp': int(time.time()),
             'event_type': event_type,
             'host': self.hostname,
             'api_key': self.agentConfig['api_key'],
             'msg_text': msg,
             'msg_title': title,
             'alert_type': alert_type,
             "source_type_name": source_type,
             "event_object": name,
        }