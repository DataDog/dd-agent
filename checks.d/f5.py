"""
    @author: Kyle Carretto
    Last Update: Tue Aug 9 (2016-08-09)
"""

import os

from checks import AgentCheck
from easysnmp import Session
from easysnmp import EasySNMPTimeoutError
from easysnmp import EasySNMPUnknownObjectIDError
from easysnmp import EasySNMPNoSuchObjectError
from easysnmp import EasySNMPNoSuchInstanceError


class F5Check(AgentCheck):

    SOURCE_TYPE_NAME = 'f5'
    MIB_DIR = "/usr/local/share/snmp/mibs/"

    """
        CUSTOM_METRICS = [ ('MIB-Module::SNMP_Object', 'MetricType', [ Tags ] ) ]

        MIB-Module  :   The MIB-Module the SNMP_Object comes from
        SNMP_Object :   The object to query for
        MetricType  :   The type of metric that will be submitted to datadog
        Tags        :   A list of literal tags to apply to the metric
    """
    CUSTOM_METRICS = [
        # Active CPU Counter
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostActiveCpuCount', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuCount', 'gauge', []),

        # CPU Usage
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuSystem', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuUser', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuIdle', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuIowait', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuSoftirq', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuIrq', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuStolen', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostCpuNice', 'rate', []),

        # Memory Usage
        ('F5-BIGIP-SYSTEM-MIB::sysStatMemoryUsed', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatMemoryTotal', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostMemUsed', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostMemTotal', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostSwapUsed', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysGlobalHostSwapTotal', 'gauge', []),

        # Throughput
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientBytesIn', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientBytesOut', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerBytesIn', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerBytesOut', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientPktsIn', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientPktsOut', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerPktsIn', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerPktsOut', 'rate', []),

        # TCP Incoming Connections
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatAccepts', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatConnects', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerTotConns', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientTotConns', 'rate', []),

        # TCP Current Connections
        ('F5-BIGIP-SYSTEM-MIB::sysStatServerCurConns', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatClientCurConns', 'gauge', []),

        # TCP Error Statistics
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatAcceptfails', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatConnfails', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatExpires', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatAbandons', 'rate', []),
        ('F5-BIGIP-SYSTEM-MIB::sysStatDroppedPackets', 'rate', []),

        # TCP Closing Statistics
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatCloseWait', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatFinWait', 'gauge', []),
        ('F5-BIGIP-SYSTEM-MIB::sysTcpStatTimeWait', 'gauge', []),

        # HTTP Request Rates
        ('F5-BIGIP-SYSTEM-MIB::sysStatHttpRequests', 'rate', []),
    ]

    """
    TABLE_METRICS = [
            [ 'Human_Readable_Name', 'Table1_Name', [Tags], [ (SNMP_Variable1, MetricType), (SNMP_Variable2, MetricType) ] ]
            [ 'Human_Readable_Name', 'Table2_Name', [Tags], [ (SNMP_Variable1, MetricType), (SNMP_Variable2, MetricType) ] ]
    ]

        Human_R.N.  : Name that will be submitted to datadog (Format: F5.Human_Readable_Name.SNMP_Variable1)
        Table_Name  : SNMP Object to perform an snmp 'walk' on (Usuallt the entry object for the table)
        Tags        : What tag(s) to apply to each metric submitted
                            -A lookup will be performed to see if this is the name of a returned object
                            -If so, the value of that object will become the tag
        Variable    : The name of the snmp variable to collect
        MetricType  : What datadog metric type should that be stored as? (gauge, rate, etc.)
    """
    TABLE_METRICS = [
        [
            'LtmVirtualServers',                                # Human_R.N.
            'F5-BIGIP-LOCAL-MIB::ltmVirtualServStatEntry',      # Table_Name
            ['ltmVirtualServStatName'],                         # Tags
            [                                                   # Elements to search for
                ('ltmVirtualServStatClientPktsIn', 'rate'),
                ('ltmVirtualServStatClientPktsIn', 'rate'),
                ('ltmVirtualServStatClientBytesIn', 'rate'),
                ('ltmVirtualServStatClientPktsOut', 'rate'),
                ('ltmVirtualServStatClientBytesOut', 'rate'),
                ('ltmVirtualServStatClientMaxConns', 'gauge'),
                ('ltmVirtualServStatClientTotConns', 'rate'),
                ('ltmVirtualServStatClientCurConns', 'gauge')
            ]
        ],

        [
            'TmmStats',                                         # Human_R.N.
            'F5-BIGIP-SYSTEM-MIB::sysTmmStatEntry',             # Table_Name
            ['sysTmmStatTmmId'],                                # Tags
            [                                                   # Elements to search for
                ('sysTmmStatClientPktsIn', 'rate'),
                ('sysTmmStatClientPktsOut', 'rate'),
                ('sysTmmStatServerPktsIn', 'rate'),
                ('sysTmmStatServerPktsOut', 'rate'),
                ('sysTmmStatClientBytesIn', 'rate'),
                ('sysTmmStatClientBytesOut', 'rate'),
                ('sysTmmStatServerBytesIn', 'rate'),
                ('sysTmmStatServerBytesOut', 'rate'),
                ('sysTmmStatServerCurConns', 'gauge'),
                ('sysTmmStatServerTotConns', 'rate'),
                ('sysTmmStatClientCurConns', 'gauge'),
                ('sysTmmStatClientTotConns', 'rate'),
                ('sysTmmStatClientEvictedConns', 'rate'),
                ('sysTmmStatServerEvictedConns', 'rate'),
                ('sysTmmStatClientSlowKilled', 'rate'),
                ('sysTmmStatServerSlowKilled', 'rate'),
                ('sysTmmStatSwSyncookies', 'rate'),
                ('sysTmmStatSwSyncookieAccepts', 'rate'),
                ('sysTmmStatSwSyncookieRejects', 'rate'),
                ('sysTmmStatDroppedPackets', 'rate'),
                ('sysTmmStatIncomingPacketErrors', 'rate'),
                ('sysTmmStatOutgoingPacketErrors', 'rate'),
                ('sysTmmStatHttpRequests', 'rate'),
                ('sysTmmStatMemoryUsed', 'gauge'),
                ('sysTmmStatMemoryTotal', 'gauge')
            ]
        ],


        [
            'LtmPoolStats',                                     # Human_R.N.
            'F5-BIGIP-LOCAL-MIB::ltmPoolStatEntry',             # Table_Name
            ['ltmPoolStatName'],                                # Tags
            [                                                   # Elements to search for
                ('ltmPoolStatServerPktsIn', 'rate'),
                ('ltmPoolStatServerPktsOut', 'rate'),
                ('ltmPoolStatServerCurConns', 'gauge'),
                ('ltmPoolStatServerTotConns', 'rate'),
                ('ltmPoolStatConnqAllDepth', 'rate'),
                ('ltmPoolStatConnqAllAgeHead', 'rate'),
                ('ltmPoolStatConnqAllAgeMax', 'rate'),
                ('ltmPoolStatConnqAllAgeEma', 'rate'),
                ('ltmPoolStatConnqAllAgeEdm', 'rate'),
                ('ltmPoolStatConnqAllServiced', 'rate'),
                ('ltmPoolStatConnqDepth', 'gauge'),
                ('ltmPoolStatConnqAgeHead', 'gauge'),
                ('ltmPoolStatConnqAgeMax', 'gauge'),
                ('ltmPoolStatConnqAgeEma', 'gauge'),
                ('ltmPoolStatConnqAgeEdm', 'gauge'),
                ('ltmPoolStatConnqServiced', 'gauge'),
                ('ltmPoolStatCurSessions', 'gauge'),
                ('ltmPoolStatTotRequests', 'rate')
            ]
        ],

        [
            'DiskStats',                                        # Human_R.N.
            'F5-BIGIP-SYSTEM-MIB::sysHostDiskEntry',            # Table_Name
            ['sysHostDiskPartition'],                           # Tags
            [                                                   # Elements to search for
                ('sysHostDiskBlockSize', 'gauge'),
                ('sysHostDiskTotalBlocks', 'gauge'),
                ('sysHostDiskFreeBlocks', 'gauge'),
                ('sysHostDiskTotalNodes', 'gauge'),
                ('sysHostDiskBlockFreeNodes', 'gauge')
            ]
        ],

        [
            'LtmClientSslStats',                                # Human_R.N.
            'F5-BIGIP-LOCAL-MIB::ltmClientSslStatEntry',        # Table_Name
            ['ltmClientSslStatName'],                           # Tags
            [                                                   # Elements to search for
                ('ltmClientSslStatCurConns', 'gauge'),
                ('ltmClientSslStatEncryptedBytesIn', 'rate'),
                ('ltmClientSslStatEncryptedBytesOut', 'rate'),
                ('ltmClientSslStatDecryptedBytesIn', 'rate'),
                ('ltmClientSslStatDecryptedBytesOut', 'rate'),
                ('ltmClientSslStatSecureHandshakes', 'rate'),
                ('ltmClientSslStatInsecureHandshakeAccepts', 'rate'),
                ('ltmClientSslStatInsecureHandshakeRejects', 'rate'),
                ('ltmClientSslStatConns', 'gauge'),
                ('ltmClientSslStatCachedCets', 'gauge')
            ]
        ],

        [
            'LtmServerSslStats',                                # Human_R.N.
            'F5-BIGIP-LOCAL-MIB::ltmServerSslStatEntry',        # Table_Name
            ['ltmServerSslStatName'],                           # Tags
            [                                                   # Elements to search for
                ('ltmServerSslStatCurConns', 'gauge'),
                ('ltmServerSslStatEncryptedBytesIn', 'rate'),
                ('ltmServerSslStatEncryptedBytesOut', 'rate'),
                ('ltmServerSslStatDecryptedBytesIn', 'rate'),
                ('ltmServerSslStatDecryptedBytesOut', 'rate'),
                ('ltmServerSslStatSecureHandshakes', 'rate'),
                ('ltmServerSslStatInsecureHandshakeAccepts', 'rate'),
                ('ltmServerSslStatInsecureHandshakeRejects', 'rate'),
                ('ltmServerSslStatConns', 'gauge'),
                ('ltmServerSslStatCachedCerts', 'gauge')
            ]
        ]


    ]

    def __init__(self, name, init_config, agentConfig, instances=None):
        """Initialize the class"""
        if len(instances) < 1:                                                  # If there is less than one instance (Should never occur)
            self.log.exception("No instances found.")                           # Log an exception
            raise                                                               # Raise
        os.environ["MIBDIRS"] = str(self.MIB_DIR)
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)    # Otherwise, call the super()

    def get_session(self, host, user, authPassword, privPassword, port=161):
        """Establish a session with the target F5, and return it"""
        self.log.info("Establish session with " + str(host))        # log_level:info
        try:                                                        # Try to
            session = Session(                                      # Establish a session
                hostname=host,                                      # Use the hostname from the instance
                version=3,                                          # Default version is SNMP v3, other versions are insecure
                remote_port=port,                                   # Use the specified port, defaulting to 161
                timeout=2,                                          # Define the number of seconds before a timeout to be 2
                retries=3,                                          # Define the maximum number of retries to be 3
                security_level="auth_with_privacy",                 # Use authentication with privacy
                security_username=user,                             # Use the username from the instance
                privacy_protocol="AES",                             # Define the privacy protocol to be AES
                privacy_password=privPassword,                      # Use the privacy password from the instance
                auth_protocol="SHA",                                # Define the authentication protocol to be SHA
                auth_password=authPassword                          # Use the authentication password from the instance
            )                                                       #
            return session                                          # Otherwise, return the established snmp session with the F5
        except Exception as e:                                      # If there are any exceptions
            self.log.exception("Could not establish session")       # log_level:exception
            self.log.debug(e)                                       # log_level:debug
            raise                                                   # Raise

    def get_snmp_walk(self, session, OID):
        """Perform an SNMP Walk operation on an object and return a dictionary of the results"""
        try:
            d = {}                                                      # Initialize a dictionary
            lst = session.walk(str(OID))                                # Use the session to perform a walk
            if len(lst) < 1:                                            # If no items were returned
                self.log.warning("No items were returned while walking OID: %s", str(OID))
            for item in lst:                                            # Iterate over the items
                key = item.oid_index                                    # Group them by OID Index
                if key not in d:                                        # If the key is not yet in the dictionary
                    d[key] = []                                         # Set it's value to be an empty list
                d[key].append((item.oid, item.value, item.snmp_type))   # And append the first instance tuple (OID, Value, SNMPType)
                self.log.debug("Item found, appending to dictionary:\n\t%s", str(item))
        except Exception as e:                                          # If there is an unexpected exception
            self.log.exception("Encountered error performing SNMP walk")# log_level:exception
            self.log.debug(e)                                           # log_level:debug
        return d                                                        # Return the dictionary, where each key maps to a list of instance tuples

    def get_snmp_value(self, session, snmp_object):
        """Returns list of values for each instance of the object that was found"""
        lst = []                                                                # Initialize a list to hold all instances
        valid = True                                                            # Initialize our valid constraint
        index = -1                                                              # Set this to be -1 so that the first query is just on the given OID (Allow for custom queries)
        timeout_counter = 0                                                     # Initialize our comment timer
        while valid and timeout_counter < 4:                                    # While an index > 1 has not failed, timeout counter is reasonable, or fatal exception has not occurred
            try:                                                                # Attempt to
                if index < 0:                                                   # If the index is less than 0 (-1 should be the only possible value)
                    item = session.get(str(snmp_object))                        # Lookup the raw name with nothing appended (Custom Query)
                else:                                                           # Otherwise
                    item = session.get((str(snmp_object), index))               # Else lookup and append the current index
                index += 1                                                      # Increment the index
                if "nosuch" in item.snmp_type.lower():                          # If it returns nosuchinstance or nosuchobject
                    if index > 1:                                               # and our index is less than 1
                        valid = False                                           # Stop the loop
                else:                                                           # Otherwise
                    try:                                                        # Attempt to
                        val = self.convert_item(item.value, item.snmp_type)     # Convert the returned value
                        lst.append(val)                                         # Append it to the main list
                    except Exception as e:                                      # Catch any unexpected exception
                        self.log.exception("Could not convert item: %s", str(item)) # log_level:exception
                        self.log.debug(e)                                       # log_level:debug
                timeout_counter = 0                                             # If everything worked out, reset our timeout counter
            except EasySNMPTimeoutError as e:                                   # If our request times out
                self.log.warning(e)                                             # log_level:warning
                timeout_counter += 1                                            # Increment our timeout counter
            except EasySNMPUnknownObjectIDError as e:                           # If the object has an unknown ID
                self.log.warning(e)                                             # log_level:warning
            except EasySNMPNoSuchObjectError as e:                              # If there is no such object
                self.log.warning(e)                                             # log_level:warning
            except EasySNMPNoSuchInstanceError as e:                            # If there is no such instance
                self.log.warning(e)                                             # log_level:warning
            except Exception as e:                                              # If there is any unexpected exception
                self.log.error("Encountered error retrieving SNMP Object")      # log_level:exception
                self.log.debug(e)                                               # log_level:debug
                valid = False                                                   # Stop the loop
        return lst                                                              # Return the main list [ SNMPVariableInstance ]

    def convert_item(self, value, snmpType):
        """Attempt to convert an item from an SNMP datatype to a useable python datatype"""
        t = str(snmpType).lower()                                               # Convert the type to a lowercase string
        if "octet" in t:                                                        # If it is an octetstr
            try:                                                                # Attempt to
                return str(value)                                               # Return the value converted to a python string
            except:                                                             # If it throws an exception
                return ".".join(['%x' % (ord(c)) for c in value])               # Display the octets joined by '.' characters
        elif "int" in t or "count" in t:                                        # Otherwise, if it is an integer or counter
            return int(value)                                                   # Return it casted to an integer
        elif "str" in t:                                                        # Otherwise, if it is just a regular string
            return str(value)                                                   # Return the value converted to a python string
        elif "time" in t or "gauge" in t:                                       # Otherwise, if it is a timetick or gauge
            return float(value)                                                 # Return the value converted to a python float
        else:                                                                   # If all else fails
            self.log.warning("Returning unconverted value (%s) of type %s", value, snmpType)
            return value                                                        # Return the original value

    def get_snmp_table_metrics(self, session, host, user, TABLE_METRICS):
        """
            Iterate through the TABLE_METRICS data structure to collect metrics
            Returns a list of (MetricType, MetricName, Value, Tags)
        """
        lst = []                                                                    # Initialize a list to collect metrics in
        for e in TABLE_METRICS:                                                     # For every defined table
            if len(e) < 4:                                                          # If the length is less than 4, something is missing
                self.log.error("Length Error: Instance of table in TABLE_METRICS is less than expected (%s < 4) {%s}", len(e), e)
                continue                                                            # Skip this element
            long_name = e[0]                                                        # Get the human readable name of the table
            snmp_obj = e[1]                                                         # Get the full name of the snmp object to walk
            tbl_tags = e[2]                                                         # Get the list of tags to attempt to resolve
            snmp_vars = e[3]                                                        # Get a list of variables to filter for
            table_found = []                                                        # Create an initial list to store metrics for the table
            self.log.debug("Attempting to get metrics for table: %s", long_name)    # log_level:debug
            d = self.get_snmp_walk(session, snmp_obj)                               # Perform the SNMP Walk to get a dictionary
            for key, item in d.items():                                             # For every item pair in the dictionary
                instance_tagVals = []                                               # Initialize a list to hold found tag values
                instance_tagNames = []                                              # Initialize a list to hold found tag names
                instance_found = []                                                 # Initialize a list to hold resolved instance elements
                for element in item:                                                # For every element (Name, Value, Type) tuple.
                    if len(element) < 3:                                            # If there is less than 3 something is missing
                        self.log.error("Length Error: Element in returned dictionary is less than expected (%s < 3) {%s}", len(element), str(element))
                        continue                                                    # Skip this element
                    sType = element[2]                                              # Get the type from the element tuple
                    value = None                                                    # Default value so it may be accessed outside of the try/catch
                    try:                                                            # Try to:
                        value = self.convert_item(element[1], sType)                # Convert the value to a python type
                    except Exception as e:                                          # Catch any exceptions
                        self.log.error("Could not convert item: %s", str(element))  # log_level:error
                        self.log.debug(e)                                           # log_level:debug
                        continue                                                    # Skip the element
                    name = str(element[0])                                          # Retrieve the name of the snmp variable from the element (Name, Value, Type) tuple
                    for var in snmp_vars:                                           # For every snmp (Variable, MetricType) mapping defined in the table
                        if len(var) < 2:                                            # If there is less than 2 something is missing
                            self.log.error("Length Error: Length of variable pair defined in TABLE_METRICS is less than expected (%s < 2) {%s}", len(var), str(var))
                            continue                                                # Skip this variable
                        if var[0].lower() == name.lower():                          # If the variable we have is one that was defined, collect it
                            instance_found.append([                                 # Append the following information:
                                var[1],                                             # - MetricType from the snmp variable
                                "F5." + long_name + "." + name,                     # - MetricName from the name of the snmp variable
                                value                                               # - Value from the convert_item function above
                            ]                                                       #
                            )                                                       #
                    if name in tbl_tags and value not in instance_tagVals:          # If this variable is a tag that has not been added yet
                        self.log.debug("Found desired tag: %s", name)               # log_level:debug
                        instance_tagVals.append(str(name) + ":" + str(value))       # Add it's value to our tagskeep track of it's name so we know it was resolved
                        instance_tagNames.append(name)                              # Keep track of it's name in 'instance_tagNames' so we know it was resolved
                if len(tbl_tags) > len(instance_tagVals):                           # Check if we resolved all tags
                    for tag in tbl_tags:                                            # If not, we iterate through all desired tags
                        if tag not in instance_tagNames:                            # And determine which were not resolved based on 'instance_tagNames'
                            self.log.warning("Could not find desired tag: %s", tag) # log_level:warning
                            if tag == 'host':                                       # If the tag is the literal 'host'
                                instance_tagVals.append(host)                       # Resolve it with the host being queried
                            elif tag == 'user':                                     # If the tag is the literal 'user'
                                instance_tagVals.append(user)                       # Resolve it with the user being used
                            else:                                                   # Otherwise
                                instance_tagVals.append(tag)                        # Add the literal tag name as the value since it was not resolved
                for instance_element in instance_found:                             # Iterate through every element found for this instance
                    instance_element.append(instance_tagVals)                       # Append the tag list for this instance
                    table_found.append(instance_element)                            # Then add it to the main list of values found for the table
            lst += table_found                                                      # Append the values found for the table to the main list
        return lst                                                                  # Return the main list [(MetricType, Name, Value, Tags)]

    def get_snmp_custom_metrics(self, session, CUSTOM_METRICS):
        """
            Iterate through the defined custom metric list, and attempt to retrieve those metrics
            Returns a list of (MetricType, MetricName, Value, Tags)
        """
        lst = []                                                            # Initialize a list to collect metrics in
        for e in CUSTOM_METRICS:                                            # For every defined custom metric
            if len(e) < 3:                                                  # If the length is less than 3 something is missing
                self.log.error("Length Error: Instance of metric in CUSTOM_METRICS is less than expected (%s < 3) {%s}", len(e), str(e))
                continue                                                    # Skip this element
            snmp_obj = e[0]                                                 # Retrieve SNMP Object Name
            metric_type = e[1]                                              # Retrieve Metric Type
            tags = e[2]                                                     # Retrieve Tags
            name = snmp_obj.split(":")[-1]                                  # Split the SNMP Object Name by ':'
            vals = self.get_snmp_value(session, e[0])                       # Retrieve a list of instances for this variable
            for val in vals:                                                # For every element in the returned list
                lst.append((metric_type, "F5.Custom." + name, val, tags))   # Take the information and append it to the main list
        return lst                                                          # Return the main list [ (MetricType, MetricName, Value, Tags) ]

    def submit_metrics(self, lst, host):
        """Send metric list to datadog"""
        for e in lst:                                                   # For every metric tuple in the metric list
            try:                                                        # Attempt to
                if len(e) < 4:                                          # If the length is less than 4 something is missing
                    self.log.error("Length Error: Element length in list while trying to submit metrics is less than expected (%s < 4) {%s}", len(e), str(e))
                    continue                                            # Skip this element
                mtype = str(e[0]).lower()                               # Get the metric type and convert to lowercase
                tags = e[3]                                             # Get the list of tags from the metric tuple
                hostTag = "lb:" + str(host)                             # Create the host tag
                if hostTag not in tags:                                 # If the host tag is not yet in the list of tags
                    tags.append("lb:" + str(host))                      # Append the host tag
                self.log.debug("Submitting Metric: {%s, %s, %s, %s\t| Type: %s}", str(e[1]), str(e[2]), str(tags), str(host), str(mtype))
                if mtype == 'gauge':                                    # If it is a gauge
                    self.gauge(str(e[1]), e[2], tags, host)             # Submit the metric
                if mtype == 'increment':                                # If it is an increment
                    self.increment(str(e[1]), e[2], tags, host)         # Submit the metric
                if mtype == 'decrement':                                # If it is a decrement
                    self.decrement(str(e[1]), e[2], tags, host)         # Submit the metric
                if mtype == 'histogram':                                # If it is a histogram
                    self.histogram(str(e[1]), e[2], tags, host)         # Submit the metric
                if mtype == 'rate':                                     # If it is a rate
                    self.rate(str(e[1]), e[2], tags, host)              # Submit the metric
                if mtype == 'count':                                    # If it is a count
                    self.count(str(e[1]), e[2], tags, host)             # Submit the metric
                if mtype == 'monotonic_count':                          # If it is a monotonic count
                    self.monotonic_count(str(e[1]), e[2], tags, host)   # Submit the metric
            except Exception as err:                                    # If there is an unexpected exception
                self.log.error(err)                                     # log_level:error

    def check(self, instance):
        """Run once for each instance provided in the datadog configuration"""
        table_lst = []                                                                          # Initialize a metric list [ (MetricType, MetricName, Value, Tags) ]
        custom_lst = []                                                                         # Initialize a metric list [ (MetricType, MetricName, Value, Tags) ]
        try:                                                                                    # Attempt to
            host = instance['host']                                                             # Store host value since it is used multiple times (Tag Resolution in table_metrics)
            user = instance['user']                                                             # Store user value since it is used multiple times (Tag Resolution in table_metrics)
            session = self.get_session(                                                         # Establish a session to use for the check with the following parameters:
                host,                                                                           # - The previously looked up host
                user,                                                                           # - The previously looked up user
                instance['auth_password'],                                                      # - The authentication password from the instance
                instance['priv_password'],                                                      # - The privacy password from the instance
                instance.get('port', 161)                                                       # - The port from the instance, or the default 161
            )                                                                                   #
            table_lst = self.get_snmp_table_metrics(session, host, user, self.TABLE_METRICS)    # Retrieve all table metrics
            custom_lst = self.get_snmp_custom_metrics(session, self.CUSTOM_METRICS)             # Retrieve all custom metrics
        except KeyError as e:                                                                   # Except an exception if the key was missing
            self.log.exception("Skipping instance check, Reason: No %s defined", e)             # log_level:exception
            raise                                                                               # Raise
        self.submit_metrics(table_lst, host)                                                    # Submit the table metrics
        self.submit_metrics(custom_lst, host)                                                   # Submit the custom metrics
