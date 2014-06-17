# std
from collections import defaultdict

# project
from checks import AgentCheck

# 3rd party
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from pysnmp.smi import builder
import pysnmp.proto.rfc1902 as snmp_type

# Additional types that are not part of the SNMP protocol. cf RFC 2856
(CounterBasedGauge64, ZeroBasedCounter64) = builder.MibBuilder().importSymbols("HCNUM-TC","CounterBasedGauge64", "ZeroBasedCounter64")

# Metric type that we support
SNMP_COUNTERS = [snmp_type.Counter32.__name__, snmp_type.Counter64.__name__, ZeroBasedCounter64.__name__]
SNMP_GAUGES = [snmp_type.Gauge32.__name__, CounterBasedGauge64.__name__]

# IF-MIB magic values
IF_TABLE_OID = '.1.3.6.1.2.1.2.2.1.'
IF_TABLE_TYPE_POS = 9
IF_TABLE_INDEX_POS = 10
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

        self.interface_list = {}

        # Load Custom MIB directory
        mibs_path = None
        if init_config is not None:
            mibs_path = init_config.get("mibs_folder")
        SnmpCheck.create_command_generator(mibs_path)

        # Detect the interfaces of the instance and retain their indexes
        if instances is not None:
            for instance in instances:
                if 'ip_address' in instance:
                    ip_address = instance["ip_address"]
                    self.interface_list[ip_address] = self.get_interfaces(instance)

    @classmethod
    def create_command_generator(cls, mibs_path=None):
        '''
        Create a command generator to perform all the snmp query
        If mibs_path is not None, load the mibs present in the custom mibs
        folder (Need to be in pysnmp format)
        '''
        cls.cmd_generator = cmdgen.CommandGenerator()
        if mibs_path is not None:
            mib_builder = cls.cmd_generator.snmpEngine.msgAndPduDsp.\
                          mibInstrumController.mibBuilder
            mib_sources = mib_builder.getMibSources() + (
                    builder.DirMibSource(mibs_path),
                    )
            mib_builder.setMibSources(*mib_sources)

    def get_interfaces(self, instance):
        '''
        Query the IF-MIB table to get the list of interfaces and their description
        Ignore the interfaces that are loopback (localhost)
        The nextCmd will return all the value in a format like this:

            [(1.3.6.1.2.1.2.2.1.{what type of information}.{index of the interface}, information)]

        For now we only care about the index, the description(eg. interface name eth0) and the type
        to ignore the loopback interface
        See http://www.alvestrand.no/objectid/1.3.6.1.2.1.2.2.1.html for more info about the table
        '''
        interface_list = {}
        transport_target = self.get_transport_target(instance)
        auth_data = self.get_auth_data(instance)

        snmp_command = self.cmd_generator.nextCmd
        error_indication, error_status, error_index, var_binds = snmp_command(
            auth_data,
            transport_target,
            IF_TABLE_OID,
            lookupValues = True
            )

        if_table = defaultdict(dict)
        if error_indication:
            raise Exception("{0} for instance {1}".format(error_indication, instance["ip_address"]))
        else:
            if error_status:
                raise Exception("{0} for instance {1}".format(error_status.prettyPrint(), instance["ip_address"]))
            else:
                for table_row in var_binds:
                    for name, val in table_row:
                        if_table[name.asTuple()[IF_TABLE_INDEX_POS]][name.asTuple()[IF_TABLE_TYPE_POS]] = val

        self.log.debug("Interface Table discovered %s" % if_table)
        for index in if_table:
            type = if_table[index].get(IF_TYPE)
            descr = if_table[index].get(IF_DESCR)
            if not reply_invalid(type):
                if int(type) != LOCALHOST_INTERFACE and not reply_invalid(descr):
                    interface_list[index] = str(descr)
                    self.log.info("Discovered interface %s" % str(descr))

        return interface_list

    @classmethod
    def get_auth_data(cls, instance):
        '''
        Generate a Security Parameters object based on the configuration of the instance
        See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
        '''
        if "community_string" in instance:
            # SNMP v1 - SNMP v2
            return cmdgen.CommunityData(instance['community_string'])
        elif "user" in instance:
            # SNMP v3
            user = instance["user"]
            auth_key = None
            priv_key = None
            auth_protocol = None
            priv_protocol = None
            if "authKey" in instance:
                auth_key = instance["authKey"]
                auth_protocol = cmdgen.usmHMACMD5AuthProtocol
            if "privKey" in instance:
                priv_key = instance["privKey"]
                auth_protocol = cmdgen.usmHMACMD5AuthProtocol
                priv_protocol = cmdgen.usmDESPrivProtocol
            if "authProtocol" in instance:
                auth_protocol = getattr(cmdgen, instance["authProtocol"])
            if "privProtocol" in instance:
                priv_protocol = getattr(cmdgen, instance["privProtocol"])
            return cmdgen.UsmUserData(user, auth_key, priv_key, auth_protocol, priv_protocol)
        else:
            raise Exception("An authentication method needs to be provided")

    @classmethod
    def get_transport_target(cls, instance):
        '''
        Generate a Transport target object based on the configuration of the instance
        '''
        if "ip_address" not in instance:
            raise Exception("An IP address needs to be specified")
        ip_address = instance["ip_address"]
        port = instance.get("port", 161) # Default SNMP port
        return cmdgen.UdpTransportTarget((ip_address, port))

    def check(self, instance):
        tags = instance.get("tags",[])
        ip_address = instance["ip_address"]
        device_oids = []
        oid_names ={}

        # Check the metrics completely defined
        for metric in instance.get('metrics', []):
            if 'MIB' in metric:
                device_oids.append(((metric["MIB"], metric["symbol"]), metric["index"]))
            elif 'OID' in metric:
                device_oids.append(metric['OID'])
                # Associate the name to the OID so that we can perform the matching
                oid_names[metric['OID']] = metric['name']
            else:
                raise Exception('Unsupported metrics format in config file')
        self.log.debug("Querying device %s for %s oids", ip_address, len(device_oids))
        results = SnmpCheck.snmp_get(instance, device_oids)
        for oid, value in results:
            self.submit_metric(instance, oid, value, tags=tags + ["snmp_device:" + ip_address],
                                                     oid_names = oid_names)

        # Check the metrics defined per interface by appending the index
        # of the table to create a fully defined metric
        interface_oids = []
        for metric in instance.get('interface_metrics', []):
            interface_oids.append((metric["MIB"], metric["symbol"]))
        for interface, descr in self.interface_list[instance['ip_address']].items():
            oids = [(oid, interface) for oid in interface_oids]
            self.log.debug("Querying device %s for %s oids", ip_address, len(oids))
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
        error_indication, error_status, error_index, var_binds = snmp_command(
                auth_data,
                transport_target,
                *oids,
                lookupNames=True,
                lookupValues=True
                )

        if error_indication:
            raise Exception("{0} for instance {1}".format(error_indication, instance["ip_address"]))
        else:
            if error_status:
                raise Exception("{0} for instance {1}".format(error_status.prettyPrint(), instance["ip_address"]))
            else:
                return var_binds

    def submit_metric(self, instance, oid, snmp_value, tags=[], oid_names={}):
        '''
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator
        '''
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning("No such Mib available: %s" %oid.getMibSymbol()[1])
            return

        # Get the name for the OID either from the name that we can decode
        # or from the name that was specified for it
        if str(oid.getOid()) in oid_names:
            name = "snmp."+ oid_names[str(oid.getOid())]
        else:
            try:
                name = "snmp." + oid.getMibSymbol()[1]
            except Exception:
                self.log.warning("Couldn't find a name for oid {0}".format(oid))
                return

        # Ugly hack but couldn't find a cleaner way
        # Proper way would be to use the ASN1 method isSameTypeWith but this
        # returns True in the case of CounterBasedGauge64 and Counter64 for example
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

