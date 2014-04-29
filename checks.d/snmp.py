from checks import AgentCheck

from pysnmp.entity.rfc3413.oneliner import cmdgen
import pysnmp.proto.rfc1902 as snmp_type

snmp_counters = [snmp_type.Counter32, snmp_type.Counter64]
snmp_gauges = [snmp_type.Gauge32]

target_oids = [
                (('SNMPv2-MIB','snmpInPkts'),'0'),
                (('UDP-MIB','udpInDatagrams'),'0')
                ]

class SnmpCheck(AgentCheck):
    
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.counter_state = {}
        self.interface_list = {}
    
    @staticmethod
    def get_auth_data(instance):
        if "community_string" in instance:
            return cmdgen.CommunityData(instance['community_string'])
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
        
        transport_target = SnmpCheck.get_transport_target(instance)
        auth_data = SnmpCheck.get_auth_data(instance)

        cmd_generator = cmdgen.CommandGenerator()

        errorIndication, errorStatus, errorIndex, varBinds = cmd_generator.getCmd(
                auth_data,
                transport_target,
                *target_oids,
                lookupNames=True,
                lookupValues=True
                )

        if errorIndication:
            self.log.warning(errorIndication)
        else:
            if errorStatus:
                self.log.warning(errorStatus.prettyPrint())
            else:
                for oid, value in varBinds:
                    self.report_as_statsd(oid.prettyPrint(), value)


    def report_as_statsd(self, name, snmp_value):
        snmp_class = getattr(snmp_value, '__class__')
        value = int(snmp_value)
        if snmp_class in snmp_counters:
            self.counter(name, value, snmp_class)
        elif snmp_class in snmp_gauges:
            self.gauge(name, value)


    def counter(self, name, value, snmp_class):
        if name in self.counter_state:
            diff = value - self.counter_state[name]
            if diff < 0:
                # Counters monotonically increase so it means the counter wrapped
                diff += pow(2, 32 if snmp_class==snmp_type.Counter32 else 64)
            self.increment(name, diff)
        else:
            self.log.info("Setting up initial value for Counter {0}".format(name))
        self.counter_state[name] = value
