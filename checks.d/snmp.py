# std
from collections import defaultdict

# project
from checks import AgentCheck

# 3rd party
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from pysnmp.smi import builder
import pysnmp.proto.rfc1902 as snmp_type

(CounterBasedGauge64, ZeroBasedCounter64) = builder.MibBuilder().importSymbols("HCNUM-TC","CounterBasedGauge64", "ZeroBasedCounter64")

SNMP_COUNTERS = [snmp_type.Counter32.__name__, snmp_type.Counter64.__name__, ZeroBasedCounter64.__name__]
SNMP_GAUGES = [snmp_type.Gauge32.__name__, CounterBasedGauge64.__name__]

# IF-MIB magic values
IF_TABLE_TYPE_POS = 9
IF_TABLE_INDEX_POS = 10
IF_INDEX = 1
IF_DESCR = 2
IF_TYPE = 3
LOCALHOST_INTERFACE = 24

def reply_invalid(oid):
    return noSuchInstance.isSameTypeWith(oid) or \
           noSuchObject.isSameTypeWith(oid)

class SnmpCheck(AgentCheck):

    cmd_generator = None

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.counter_state = defaultdict(dict)
        self.interface_list = {}
        mibs_path = None
        if init_config is not None:
            mibs_path = init_config.get("mibs_folder")
        SnmpCheck.create_command_generator(mibs_path)
        if instances is not None:
            for instance in instances:
                if 'ip_address' in instance:
                    ip_address = instance["ip_address"]
                    self.interface_list[ip_address] = self.get_interfaces(instance)

    @classmethod
    def create_command_generator(cls, mibs_path=None):
        cls.cmd_generator = cmdgen.CommandGenerator()
        if mibs_path is not None:
            mibBuilder = cls.cmd_generator.snmpEngine.msgAndPduDsp.\
                         mibInstrumController.mibBuilder
            mibSources = mibBuilder.getMibSources() + (
                    builder.DirMibSource(mibs_path),
                    )
            mibBuilder.setMibSources(*mibSources)

    def get_interfaces(self, instance):
        interface_list = {}
        transport_target = self.get_transport_target(instance)
        auth_data = self.get_auth_data(instance)

        snmp_command = self.cmd_generator.nextCmd
        errorIndication, errorStatus, errorIndex, varBinds = snmp_command(
            auth_data,
            transport_target,
            '.1.3.6.1.2.1.2.2.1.',
            lookupValues = True
            )

        ifTable = defaultdict(dict)
        if errorIndication:
            raise Exception("{0} for instance {1}".format(errorIndication,instance["ip_address"]))
        else:
            if errorStatus:
                raise Exception("{0} for instance {1}".format(errorStatus.prettyPrint(),instance["ip_address"]))
            else:
                for tableRow in varBinds:
                    for name, val in tableRow:
                        ifTable[name.asTuple()[IF_TABLE_INDEX_POS]][name.asTuple()[IF_TABLE_TYPE_POS]] = val

        self.log.debug("Interface Table discovered %s" % ifTable)
        for index in ifTable:
            type = ifTable[index].get(IF_TYPE)
            descr = ifTable[index].get(IF_DESCR)
            if not reply_invalid(type):
                if int(type) != LOCALHOST_INTERFACE and not reply_invalid(descr):
                    interface_list[index] = str(descr)
                    self.log.info("Discovered interface %s" % str(descr))

        return interface_list

    @classmethod
    def get_auth_data(cls, instance):
        if "community_string" in instance:
            # SNMP v1 - SNMP v2
            return cmdgen.CommunityData(instance['community_string'])
        elif "user" in instance:
            # SNMP v3
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

    @classmethod
    def get_transport_target(cls, instance):
        if "ip_address" not in instance:
            raise Exception("An IP address needs to be specified")
        ip_address = instance["ip_address"]
        port = instance.get("port", 161) # Default SNMP port
        return cmdgen.UdpTransportTarget((ip_address,port))

    def check(self, instance):
        tags = instance.get("tags",[])
        ip_address = instance["ip_address"]
        device_oids = []
        interface_oids = []
        oid_names ={}
        for metric in instance.get('metrics',[]):
            if 'MIB' in metric:
                device_oids.append(((metric["MIB"],metric["symbol"]),metric["index"]))
            elif 'OID' in metric:
                device_oids.append(metric['OID'])
                oid_names[metric['OID']]=metric['name']
            else:
                raise Exception('Unsupported metrics format in config file')
        self.log.debug("Querying device %s for %s oids",ip_address, len(device_oids))
        results = SnmpCheck.snmp_get(instance, device_oids)
        for oid, value in results:
            self.submit_metric(instance, oid, value, tags=tags + ["snmp_device:" + ip_address],
                                                     oid_names = oid_names)

        for metric in instance.get('interface_metrics',[]):
            interface_oids.append((metric["MIB"],metric["symbol"]))
        for interface, descr in self.interface_list[instance['ip_address']].items():
            oids = [(oid, interface) for oid in interface_oids]
            self.log.debug("Querying device %s for %s oids",ip_address, len(oids))
            interface_results = SnmpCheck.snmp_get(instance, oids)
            for oid, value in interface_results:
                self.submit_metric(instance, oid, value, tags = tags + ["snmp_device:" + ip_address,
                                                                            "interface:"+descr])

    @classmethod
    def snmp_get(cls, instance, oids):
        """
        Perform a snmp get command to the device that instance
        describe and return a list of tuble (name, values)
        corresponding to the elements in oids.
        """
        transport_target = cls.get_transport_target(instance)
        auth_data = cls.get_auth_data(instance)


        snmp_command = cls.cmd_generator.getCmd
        errorIndication, errorStatus, errorIndex, varBinds = snmp_command(
                auth_data,
                transport_target,
                *oids,
                lookupNames=True,
                lookupValues=True
                )

        if errorIndication:
            raise Exception("{0} for instance {1}".format(errorIndication,instance["ip_address"]))
        else:
            if errorStatus:
                raise Exception("{0} for instance {1}".format(errorStatus.prettyPrint(),instance["ip_address"]))
            else:
                return varBinds

    def submit_metric(self, instance, oid, snmp_value, tags=[], oid_names={}):
        if reply_invalid(snmp_value):
            self.log.warning("No such Mib available: %s" %oid.getMibSymbol()[1])
            return
        if str(oid.getOid()) in oid_names:
            name = "snmp."+ oid_names[str(oid.getOid())]
        else:
            try:
                name = "snmp." + oid.getMibSymbol()[1]
            except Exception:
                self.log.warning("Couldn't find a name for oid {0}".format(oid))
                return

        snmp_class = snmp_value.__class__.__name__
        for counter_class in SNMP_COUNTERS:
            if snmp_class==counter_class:
                value = int(snmp_value)
                self.rate(name, value, tags)
                return
        for gauge_class in SNMP_GAUGES:
            if snmp_class==gauge_class:
                value = int(snmp_value)
                self.gauge(name, value, tags)
                return
        self.log.warning("Unsupported metric type %s", snmp_class)

