# stdlib

# project

from aerospike import aerospike_dashboards
from aerospike import citrusleaf as cl
from aerospike import interface
from aerospike import log
from aerospike.constants import ERROR_CODES
from aerospike.constants import HASH_KEY

from checks import AgentCheck

# global variables
bcrypt_flag = True
try:
    import bcrypt
except ImportError:
    bcrypt_flag = False


class Aerospike(AgentCheck):

    # function to create pre-defined Aerospike Dashboards.
    def create_timeboard(
            self, api_key, api_application_key, instance_name, node_address,
            ns_list):

        response = aerospike_dashboards.draw_node_dashboard(
            api_key, api_application_key, instance_name, node_address)
        if response is None:
            self.log.error(
                'Unable to Create Node Dashboard due to error' +
                ' while importing Dogapi and/or Datadog')
        if ns_list in ERROR_CODES:
            self.log.error(
                'Namespace List is Empty, cannot create namespace Dashboards.')
            return
        for ns in ns_list:
            response = aerospike_dashboards.draw_namespace_dashboard(
                api_key, api_application_key, instance_name, node_address, ns)
            if response is None:
                self.log.error(
                    'Unable to Create Namespace: ' + str(ns) +
                    ' Dashboard due to error while' +
                    ' importing Dogapi and/or Datadog')

    def check(self, instance):

        global bcrypt_flag
        # get instance variables
        ip = str(instance['ip'])
        port = str(instance['port'])
        user = instance['user']
        password = str(instance['password'])
        cls_mode = instance['cluster_mode']
        # debug_mode = instance['debug_mode']
        instance_name = str(instance['cluster_name'])
        api_key = str(instance['api_key'])
        api_application_key = str(instance['api_application_key'])

        if cls_mode:
            log.print_log(
                self,
                'Using Aerospike Datadog Coneector in clustered mode...')
        else:
            log.print_log(
                self,
                'Using Aerospike Datadog Coneector in non-clustered mode...')

        # bcrypt check for secured Aerospike
        if user != 'n/s':
            if bcrypt_flag:
                valid_pwd = interface.is_valid_password(password, HASH_KEY)
                if valid_pwd:
                    password = bcrypt.hashpw(password, HASH_KEY)
                else:
                    log.print_log(self, 'Problem with bcrypt', error_flag=True)
            else:
                log.print_log(self, 'bcrypt not installed', error_flag=True)

        # Non-clustered mode check
        if cls_mode is False:
            cl.set_logger(self)
            ns_list = interface.get_metrics(
                self, ip, port, user, password, instance_name)
            self.create_timeboard(
                api_key, api_application_key, instance_name,
                str(ip) + ':' + str(port), ns_list)

if __name__ == '__main__':

    check, instances = Aerospike.from_yaml('/path/to/conf.d/aerospike.yaml')
    for instance in instances:
        check.check(instance)
