# std
from collections import defaultdict
from functools import wraps

# 3rd party
from pysnmp.entity.rfc3413.oneliner import cmdgen
import pysnmp.proto.rfc1902 as snmp_type
from pysnmp.smi import builder
from pysnmp.smi.exval import noSuchInstance, noSuchObject
from pysnmp.error import PySnmpError

# project
from checks.network_checks import NetworkCheck, Status
from config import _is_affirmative



# Additional types that are not part of the SNMP protocol. cf RFC 2856
(CounterBasedGauge64, ZeroBasedCounter64) = builder.MibBuilder().importSymbols(
    "HCNUM-TC",
    "CounterBasedGauge64",
    "ZeroBasedCounter64")

# Metric type that we support
SNMP_COUNTERS = frozenset([
    snmp_type.Counter32.__name__,
    snmp_type.Counter64.__name__,
    ZeroBasedCounter64.__name__])

SNMP_GAUGES = frozenset([
    snmp_type.Gauge32.__name__,
    snmp_type.Unsigned32.__name__,
    CounterBasedGauge64.__name__,
    snmp_type.Integer.__name__,
    snmp_type.Integer32.__name__])

DEFAULT_OID_BATCH_SIZE = 10


def reply_invalid(oid):
    return noSuchInstance.isSameTypeWith(oid) or \
        noSuchObject.isSameTypeWith(oid)


class SnmpCheck(NetworkCheck):

    SOURCE_TYPE_NAME = 'system'
    # pysnmp default values
    DEFAULT_RETRIES = 5
    DEFAULT_TIMEOUT = 1
    SC_STATUS = 'snmp.can_check'

    def __init__(self, name, init_config, agentConfig, instances):
        for instance in instances:
            if 'name' not in instance:
                instance['name'] = self._get_instance_key(instance)
            instance['skip_event'] = True

        self.generators = {}

        # Set OID batch size
        self.oid_batch_size = int(init_config.get("oid_batch_size", DEFAULT_OID_BATCH_SIZE))

        # Load Custom MIB directory
        self.mibs_path = None
        self.ignore_nonincreasing_oid = False
        if init_config is not None:
            self.mibs_path = init_config.get("mibs_folder")
            self.ignore_nonincreasing_oid = _is_affirmative(
                init_config.get("ignore_nonincreasing_oid", False))

        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

    def _load_conf(self, instance):
        tags = instance.get("tags", [])
        ip_address = instance["ip_address"]
        metrics = instance.get('metrics', [])
        timeout = int(instance.get('timeout', self.DEFAULT_TIMEOUT))
        retries = int(instance.get('retries', self.DEFAULT_RETRIES))
        enforce_constraints = _is_affirmative(instance.get('enforce_mib_constraints', True))

        instance_key = instance['name']
        cmd_generator = self.generators.get(instance_key, None)
        if not cmd_generator:
            cmd_generator = self.create_command_generator(self.mibs_path, self.ignore_nonincreasing_oid)
            self.generators[instance_key] = cmd_generator

        return cmd_generator, ip_address, tags, metrics, timeout, retries, enforce_constraints

    def _get_instance_key(self, instance):
        key = instance.get('name', None)
        if key:
            return key

        host = instance.get('host', None)
        ip = instance.get('ip_address', None)
        port = instance.get('port', None)
        if host and port:
            key = "{host}:{port}".format(host=host, port=port)
        elif ip and port:
            key = "{host}:{port}".format(host=ip, port=port)
        elif host:
            key = host
        elif ip:
            key = ip

        return key

    def snmp_logger(self, func):
        """
        Decorator to log, with DEBUG level, SNMP commands
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.log.debug("Running SNMP command {0} on OIDS {1}"
                           .format(func.__name__, args[2:]))
            result = func(*args, **kwargs)
            self.log.debug("Returned vars: {0}".format(result[-1]))
            return result
        return wrapper

    def create_command_generator(self, mibs_path, ignore_nonincreasing_oid):
        '''
        Create a command generator to perform all the snmp query.
        If mibs_path is not None, load the mibs present in the custom mibs
        folder. (Need to be in pysnmp format)
        '''
        cmd_generator = cmdgen.CommandGenerator()
        cmd_generator.ignoreNonIncreasingOid = ignore_nonincreasing_oid

        if mibs_path is not None:
            mib_builder = cmd_generator.snmpEngine.msgAndPduDsp.\
                mibInstrumController.mibBuilder
            mib_sources = mib_builder.getMibSources() + \
                (builder.DirMibSource(mibs_path), )
            mib_builder.setMibSources(*mib_sources)

        return cmd_generator


    @classmethod
    def get_auth_data(cls, instance):
        '''
        Generate a Security Parameters object based on the instance's
        configuration.
        See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
        '''
        if "community_string" in instance:
            # SNMP v1 - SNMP v2

            # See http://pysnmp.sourceforge.net/docs/current/security-configuration.html
            if int(instance.get("snmp_version", 2)) == 1:
                return cmdgen.CommunityData(instance['community_string'],
                    mpModel=0)
            return cmdgen.CommunityData(instance['community_string'], mpModel=1)

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
            return cmdgen.UsmUserData(user,
                                      auth_key,
                                      priv_key,
                                      auth_protocol,
                                      priv_protocol)
        else:
            raise Exception("An authentication method needs to be provided")

    @classmethod
    def get_transport_target(cls, instance, timeout, retries):
        '''
        Generate a Transport target object based on the instance's configuration
        '''
        if "ip_address" not in instance:
            raise Exception("An IP address needs to be specified")
        ip_address = instance["ip_address"]
        port = int(instance.get("port", 161)) # Default SNMP port
        return cmdgen.UdpTransportTarget((ip_address, port), timeout=timeout, retries=retries)

    def raise_on_error_indication(self, error_indication, instance):
        if error_indication:
            message = "{0} for instance {1}".format(error_indication,
                                                    instance["ip_address"])
            instance["service_check_error"] = message
            raise Exception(message)

    def check_table(self, instance, cmd_generator, oids, lookup_names,
                    timeout, retries, enforce_constraints=False):
        '''
        Perform a snmpwalk on the domain specified by the oids, on the device
        configured in instance.
        lookup_names is a boolean to specify whether or not to use the mibs to
        resolve the name and values.

        Returns a dictionary:
        dict[oid/metric_name][row index] = value
        In case of scalar objects, the row index is just 0
        '''
        # UPDATE: We used to perform only a snmpgetnext command to fetch metric values.
        # It returns the wrong value when the OID passeed is referring to a specific leaf.
        # For example:
        # snmpgetnext -v2c -c public localhost:11111 1.36.1.2.1.25.4.2.1.7.222
        # iso.3.6.1.2.1.25.4.2.1.7.224 = INTEGER: 2
        # SOLUTION: perform a snmget command and fallback with snmpgetnext if not found

        # Set aliases for snmpget and snmpgetnext with logging
        snmpget = self.snmp_logger(cmd_generator.getCmd)
        snmpgetnext = self.snmp_logger(cmd_generator.nextCmd)
        transport_target = self.get_transport_target(instance, timeout, retries)
        auth_data = self.get_auth_data(instance)

        first_oid = 0
        all_binds = []
        results = defaultdict(dict)

        while first_oid < len(oids):
            try:
                # Start with snmpget command
                error_indication, error_status, error_index, var_binds = snmpget(
                    auth_data,
                    transport_target,
                    *(oids[first_oid:first_oid + self.oid_batch_size]),
                    lookupValues=enforce_constraints,
                    lookupNames=lookup_names)

                # Raise on error_indication
                self.raise_on_error_indication(error_indication, instance)

                missing_results = []
                complete_results = []

                for var in var_binds:
                    result_oid, value = var
                    if reply_invalid(value):
                        oid_tuple = result_oid.asTuple()
                        oid = ".".join([str(i) for i in oid_tuple])
                        missing_results.append(oid)
                    else:
                        complete_results.append(var)

                if missing_results:
                    # If we didn't catch the metric using snmpget, try snmpnext
                    error_indication, error_status, error_index, var_binds_table = snmpgetnext(
                        auth_data,
                        transport_target,
                        *missing_results,
                        lookupValues=enforce_constraints,
                        lookupNames=lookup_names)

                    # Raise on error_indication
                    self.raise_on_error_indication(error_indication, instance)

                    if error_status:
                        message = "{0} for instance {1}".format(error_status.prettyPrint(),
                                                                instance["ip_address"])
                        instance["service_check_error"] = message
                        self.warning(message)

                    for table_row in var_binds_table:
                        complete_results.extend(table_row)

                all_binds.extend(complete_results)

            except PySnmpError as e:
                if "service_check_error" not in instance:
                    instance["service_check_error"] = "Fail to collect some metrics: {0}".format(e)
                if "service_check_severity" not in instance:
                    instance["service_check_severity"] = Status.CRITICAL
                self.warning("Fail to collect some metrics: {0}".format(e))

            # if we fail move onto next batch
            first_oid = first_oid + self.oid_batch_size

        # if we've collected some variables, it's not that bad.
        if "service_check_severity" in instance and len(all_binds):
            instance["service_check_severity"] = Status.WARNING

        for result_oid, value in all_binds:
            if lookup_names:
                _, metric, indexes = result_oid.getMibSymbol()
                results[metric][indexes] = value
            else:
                oid = result_oid.asTuple()
                matching = ".".join([str(i) for i in oid])
                results[matching] = value
        self.log.debug("Raw results: {0}".format(results))
        return results

    def _check(self, instance):
        '''
        Perform two series of SNMP requests, one for all that have MIB asociated
        and should be looked up and one for those specified by oids
        '''

        cmd_generator, ip_address, tags, metrics, timeout, retries, enforce_constraints = self._load_conf(instance)

        tags += ['snmp_device:{0}'.format(ip_address)]

        table_oids = []
        raw_oids = []

        # Check the metrics completely defined
        for metric in metrics:
            if 'MIB' in metric:
                try:
                    assert "table" in metric or "symbol" in metric
                    to_query = metric.get("table", metric.get("symbol"))
                    table_oids.append(cmdgen.MibVariable(metric["MIB"], to_query))
                except Exception as e:
                    self.log.warning("Can't generate MIB object for variable : %s\n"
                                     "Exception: %s", metric, e)
            elif 'OID' in metric:
                raw_oids.append(metric['OID'])
            else:
                raise Exception('Unsupported metric in config file: %s' % metric)
        try:
            if table_oids:
                self.log.debug("Querying device %s for %s oids", ip_address, len(table_oids))
                table_results = self.check_table(instance, cmd_generator, table_oids, True, timeout, retries,
                                                 enforce_constraints=enforce_constraints)
                self.report_table_metrics(metrics, table_results, tags)

            if raw_oids:
                self.log.debug("Querying device %s for %s oids", ip_address, len(raw_oids))
                raw_results = self.check_table(instance, cmd_generator, raw_oids, False, timeout, retries,
                                               enforce_constraints=False)
                self.report_raw_metrics(metrics, raw_results, tags)
        except Exception as e:
            if "service_check_error" not in instance:
                instance["service_check_error"] = "Fail to collect metrics for {0} - {1}".format(instance['name'], e)
            self.warning(instance["service_check_error"])
            return [(self.SC_STATUS, Status.CRITICAL, instance["service_check_error"])]
        finally:
            # Report service checks
            tags = ["snmp_device:%s" % ip_address]
            if "service_check_error" in instance:
                status = Status.DOWN
                if "service_check_severity" in instance:
                    status = instance["service_check_severity"]
                return [(self.SC_STATUS, status, instance["service_check_error"])]

            return [(self.SC_STATUS, Status.UP, None)]

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        sc_tags = ['snmp_device:{0}'.format(instance["ip_address"])]
        custom_tags = instance.get('tags', [])
        tags = sc_tags + custom_tags

        self.service_check(sc_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )

    def report_raw_metrics(self, metrics, results, tags):
        '''
        For all the metrics that are specified as oid,
        the conf oid is going to exactly match or be a prefix of the oid sent back by the device
        Use the instance configuration to find the name to give to the metric

        Submit the results to the aggregator.
        '''

        for metric in metrics:
            forced_type = metric.get('forced_type')
            if 'OID' in metric:
                queried_oid = metric['OID']
                if queried_oid in results:
                    value = results[queried_oid]
                else:
                    for oid in results:
                        if oid.startswith(queried_oid):
                            value = results[oid]
                            break
                    else:
                        self.log.warning("No matching results found for oid %s",
                                         queried_oid)
                        continue
                name = metric.get('name', 'unnamed_metric')
                self.submit_metric(name, value, forced_type, tags)

    def report_table_metrics(self, metrics, results, tags):
        '''
        For each of the metrics specified as needing to be resolved with mib,
        gather the tags requested in the instance conf for each row.

        Submit the results to the aggregator.
        '''

        for metric in metrics:
            forced_type = metric.get('forced_type')
            if 'table' in metric:
                index_based_tags = []
                column_based_tags = []
                for metric_tag in metric.get('metric_tags', []):
                    tag_key = metric_tag['tag']
                    if 'index' in metric_tag:
                        index_based_tags.append((tag_key, metric_tag.get('index')))
                    elif 'column' in metric_tag:
                        column_based_tags.append((tag_key, metric_tag.get('column')))
                    else:
                        self.log.warning("No indication on what value to use for this tag")

                for value_to_collect in metric.get("symbols", []):
                    for index, val in results[value_to_collect].items():
                        metric_tags = tags + self.get_index_tags(index, results,
                                                                 index_based_tags,
                                                                 column_based_tags)
                        self.submit_metric(value_to_collect, val, forced_type, metric_tags)

            elif 'symbol' in metric:
                name = metric['symbol']
                result = results[name].items()
                if len(result) > 1:
                    self.log.warning("Several rows corresponding while the metric is supposed to be a scalar")
                    continue
                val = result[0][1]
                self.submit_metric(name, val, forced_type, tags)
            elif 'OID' in metric:
                pass # This one is already handled by the other batch of requests
            else:
                raise Exception('Unsupported metric in config file: %s' % metric)

    def get_index_tags(self, index, results, index_tags, column_tags):
        '''
        Gather the tags for this row of the table (index) based on the
        results (all the results from the query).
        index_tags and column_tags are the tags to gather.
         - Those specified in index_tags contain the tag_group name and the
           index of the value we want to extract from the index tuple.
           cf. 1 for ipVersion in the IP-MIB::ipSystemStatsTable for example
         - Those specified in column_tags contain the name of a column, which
           could be a potential result, to use as a tage
           cf. ifDescr in the IF-MIB::ifTable for example
        '''
        tags = []
        for idx_tag in index_tags:
            tag_group = idx_tag[0]
            try:
                tag_value = index[idx_tag[1] - 1].prettyPrint()
            except IndexError:
                self.log.warning("Not enough indexes, skipping this tag")
                continue
            tags.append("{0}:{1}".format(tag_group, tag_value))
        for col_tag in column_tags:
            tag_group = col_tag[0]
            try:
                tag_value = results[col_tag[1]][index]
            except KeyError:
                self.log.warning("Column %s not present in the table, skipping this tag", col_tag[1])
                continue
            if reply_invalid(tag_value):
                self.log.warning("Can't deduct tag from column for tag %s",
                                 tag_group)
                continue
            tag_value = tag_value.prettyPrint()
            tags.append("{0}:{1}".format(tag_group, tag_value))
        return tags

    def submit_metric(self, name, snmp_value, forced_type, tags=[]):
        '''
        Convert the values reported as pysnmp-Managed Objects to values and
        report them to the aggregator
        '''
        if reply_invalid(snmp_value):
            # Metrics not present in the queried object
            self.log.warning("No such Mib available: %s" % name)
            return

        metric_name = self.normalize(name, prefix="snmp")

        if forced_type:
            if forced_type.lower() == "gauge":
                value = int(snmp_value)
                self.gauge(metric_name, value, tags)
            elif forced_type.lower() == "counter":
                value = int(snmp_value)
                self.rate(metric_name, value, tags)
            else:
                self.warning("Invalid forced-type specified: {0} in {1}".format(forced_type, name))
                raise Exception("Invalid forced-type in config file: {0}".format(name))

            return

        # Ugly hack but couldn't find a cleaner way
        # Proper way would be to use the ASN1 method isSameTypeWith but it
        # wrongfully returns True in the case of CounterBasedGauge64
        # and Counter64 for example
        snmp_class = snmp_value.__class__.__name__
        if snmp_class in SNMP_COUNTERS:
            value = int(snmp_value)
            self.rate(metric_name, value, tags)
            return
        if snmp_class in SNMP_GAUGES:
            value = int(snmp_value)
            self.gauge(metric_name, value, tags)
            return

        self.log.warning("Unsupported metric type %s", snmp_class)
