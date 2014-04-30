from checks import AgentCheck

from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.exval import noSuchInstance
import pysnmp.proto.rfc1902 as snmp_type

snmp_counters = [snmp_type.Counter32, snmp_type.Counter64]
snmp_gauges = [snmp_type.Gauge32]

class SnmpCheck(AgentCheck):

    interface_oids = [
            ("IF-MIB", "ifInOctets"),
            ("IF-MIB", "ifInErrors"),
            ("IF-MIB", "ifInDiscards"),
            ("IF-MIB", "ifOutOctets"),
            ("IF-MIB", "ifOutErrors"),
            ("IF-MIB", "ifOutDiscards")
            ]

    device_oids = [
            (("UDP-MIB", "udpInDatagrams"),0),
            (("TCP-MIB", "tcpCurrEstab"),0),
            (("TCP-MIB", "tcpActiveOpens"),0),
            (("TCP-MIB", "tcpPassiveOpens"),0)
            ]



    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.counter_state = {}
        self.interface_list = {}
        for instance in instances:
            if 'ip_address' in instance:
                ip_address = instance["ip_address"]
                self.counter_state[ip_address] = {}
                self.interface_list[ip_address] = self.get_interfaces(instance)
                tags = instance.get("tags",[])
                tags.append("device:" + ip_address)
        for metric in init_config["metrics"]:
            SnmpCheck.device_oids.append(((metric["MIB"],metric["symbol"]),metric["index"]))


    def get_interfaces(self, instance):

        interface_list = {}

        def get_interfaces_nb():
            result = SnmpCheck.snmp_get(instance, [(("IF-MIB","ifNumber"),0)])[0]
            if noSuchInstance.isSameTypeWith(result[1]):
                return None
            else:
                return int(result[1])

        interface_nb = get_interfaces_nb()
        if interface_nb is not None:
            interfaces_descr_oids = []
            for interface in range(interface_nb):
                interface_index = interface + 1 #SNMP indexes start from 1
                interfaces_descr_oids.append((("IF-MIB","ifDescr"),interface_index))
                interfaces_descr_oids.append((("IF-MIB","ifType"),interface_index))

            interfaces_description = SnmpCheck.snmp_get(instance, interfaces_descr_oids)
            self.log.info(interfaces_description)
            for i in range(interface_nb):
                # order is guaranteed
                descr = str(interfaces_description.pop(0)[1])
                type = int(interfaces_description.pop(0)[1])
                if type != 24:
                    interface_list[i+1] = descr
        else:
            empty_reply = False
            interface_index = 1
            while not empty_reply:
                interfaces_descr_oids = []
                interfaces_descr_oids.append((("IF-MIB","ifDescr"),interface_index))
                interfaces_descr_oids.append((("IF-MIB","ifType"),interface_index))
                interfaces_description = SnmpCheck.snmp_get(instance, interfaces_descr_oids)
                descr = interfaces_description.pop(0)[1]
                if noSuchInstance.isSameTypeWith(descr):
                    empty_reply= True
                else:
                    type = int(interfaces_description.pop(0)[1])
                    if type != 24:
                        interface_list[interface_index] = str(descr)
                    interface_index += 1

        return interface_list

    @staticmethod
    def get_auth_data(instance):
        if "community_string" in instance:
            return cmdgen.CommunityData(instance['community_string'])
        elif "user" in instance:
            user = instance["user"]
            authKey = None
            privKey = None
            authProtocol = None
            privProtocol = None
            if "authKey" in instance:
                authKey = instance["authKey"]
                authProtocol = cmdgen.usmHMACMD5AuthProtocol
            if "privKey" in instance:
                privKey = instance["privKey"]
                authProtocol = cmdgen.usmHMACMD5AuthProtocol
                privProtocol = cmdgen.usmDESPrivProtocol
            if "authProtocol" in instance:
                authProtocol = getattr(cmdgen,instance["authProtocol"])
            if "privProtocol" in instance:
                privProtocol = getattr(cmdgen,instance["privProtocol"])
            return cmdgen.UsmUserData(user, authKey, privKey, authProtocol, privProtocol)
        else:
            raise Exception("An authentication method needs to be provided")

    @staticmethod
    def get_transport_target(instance):
        if "ip_address" not in instance:
            raise Exception("An IP address needs to be specified")
        ip_address = instance["ip_address"]
        port = instance.get("port", 161)
        return cmdgen.UdpTransportTarget((ip_address,port))

    def check(self, instance):
        tags = instance.get("tags",[])
        results = SnmpCheck.snmp_get(instance, SnmpCheck.device_oids)
        for oid, value in results:
            self.report_as_statsd(instance, oid, value, tags=tags)

        for interface, descr in self.interface_list[instance['ip_address']].items():
            oids = [(oid, interface) for oid in SnmpCheck.interface_oids]
            interface_results = SnmpCheck.snmp_get(instance, oids)
            for oid, value in interface_results:
                self.report_as_statsd(instance, oid, value, tags = tags + ["interface:"+descr])

    @staticmethod
    def snmp_get(instance, oids):
        """
        Perform a snmp get command to the device that instance
        describe and return a list of tuble (name, values)
        corresponding to the elements in oids.
        """
        transport_target = SnmpCheck.get_transport_target(instance)
        auth_data = SnmpCheck.get_auth_data(instance)

        cmd_generator = cmdgen.CommandGenerator()

        snmp_command = cmd_generator.getCmd
        errorIndication, errorStatus, errorIndex, varBinds = snmp_command(
                auth_data,
                transport_target,
                *oids,
                lookupNames=True,
                lookupValues=True
                )

        if errorIndication:
            self.log.warning(errorIndication)
        else:
            if errorStatus:
                self.log.warning(errorStatus.prettyPrint())
            else:
                return varBinds

    def report_as_statsd(self, instance, oid, snmp_value, tags=[]):
        if noSuchInstance.isSameTypeWith(snmp_value):
            return
        name = "snmp." + oid.getMibSymbol()[1]
        snmp_class = getattr(snmp_value, '__class__')
        value = int(snmp_value)
        if snmp_class in snmp_counters:
            self.counter(instance, name, value, snmp_class, tags)
        elif snmp_class in snmp_gauges:
            self.gauge(name, value, tags)


    def counter(self, instance, name, value, snmp_class, tags = []):
        current_state = self.counter_state[instance['ip_address']]
        metric_id = name + str(tags)
        if metric_id in current_state:
            diff = value - current_state[metric_id]
            if diff < 0:
                # Counters monotonically increase so it means the counter wrapped
                diff += pow(2, 32 if snmp_class==snmp_type.Counter32 else 64)
            self.increment(name, diff,tags=tags)
        else:
            self.log.info("Setting up initial value for Counter {0}".format(name))
        current_state[metric_id] = value
