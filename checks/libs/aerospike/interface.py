# stdlib
import time
import sys
# project
import base
from constants import ERROR_CODES

import log

sys.path.insert(1, '/usr/local/lib/python2.7/dist-packages/')


# pushes all metrics into Datadog system. Returns Namespace List


def get_metrics(obj, ip, port, username, passwd, instance_name):

    base.clear_log_messages()
    log_messages = base.get_log_messages()
    msg = "function: get_metrics   |input:- ip:"
    msg += "%s,port:%s,user:%s,password:%s" % (ip, port, username, passwd)
    log.print_log(obj, msg)
    # get data from server
    if username == 'n/s':
        info = base.get_node_info(ip, port)
        node_latency = base.get_node_latency(ip, port)
        namespaces = base.get_namespaces(ip, port)
    else:
        info = base.get_node_info(ip, port, user=username, password=passwd)
        node_latency = base.get_node_latency(ip, port, user=username,
                                             password=passwd)
        namespaces = base.get_namespaces(ip, port, user=username,
                                         password=passwd)

    # stats kept out of if for alerts to work
    stats = base.get_node_statistics(info)

    # publish node metrics
    if info != {}:
        base.extract_tps_parameter_from_statistics(stats)
        read_tps = base.get_read_tps()
        write_tps = base.get_write_tps()

        free_disk_stats = str(base.get_free_disk_stats(stats))
        free_memory_stats = str(base.get_free_memory_stats(stats))

        total_disk_stats = str(base.get_total_disk_stats(stats))
        total_memory_stats = str(base.get_total_memory_stats(stats))

        for key, value in stats.iteritems():
            obj.gauge('aerospike.node.' + str(key), str(value),
                      tags=['node:' + str(ip) + ':' + str(port), 'name:' +
                            str(instance_name)])
        no_of_nodes = base.get_no_of_nodes(stats)

        if node_latency != {}:
            for key, value in node_latency.iteritems():
                data_list = node_latency[key]['data']
                for item in data_list:
                    for k, v in item.iteritems():
                        metric_name = 'aerospike.node.' + str(key)
                        tags_pct = ['latency_type:' + str(k),
                                    'value_type:percentage',
                                    'node:' + str(ip) + ':' + str(port),
                                    'name:' + str(instance_name)]
                        tags_value = ['latency_type:' + str(k),
                                      'value_type:value',
                                      'node:' + str(ip) + ':' + str(port),
                                      'name:' + str(instance_name)]
                        obj.gauge(metric_name, v['value'], tags_value)
                        obj.gauge(metric_name, v['pct'], tags_pct)

        if free_disk_stats != 'n/s':
            obj.gauge('aerospike.disk_usage_free', free_disk_stats,
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if total_disk_stats != 'n/s':
            obj.gauge('aerospike.disk_usage_total', total_disk_stats,
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if free_memory_stats != 'n/s':
            obj.gauge('aerospike.memory_usage_free', free_memory_stats,
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if total_memory_stats != 'n/s':
            obj.gauge('aerospike.memory_usage_total', total_memory_stats,
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if no_of_nodes is not None:
            obj.gauge('aerospike.cluster_size', no_of_nodes,
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        else:
            log.print_log(obj, 'Number of Nodes are None!', error_flag=True)
        if read_tps['y'] is not None:
            obj.gauge('aerospike.successful_read_tps', read_tps['y'],
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if read_tps['secondary'] is not None:
            obj.gauge('aerospike.total_read_tps', read_tps['secondary'],
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if write_tps['y'] is not None:
            obj.gauge('aerospike.successful_write_tps', write_tps['y'],
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])
        if write_tps['secondary'] is not None:
            obj.gauge('aerospike.total_write_tps', write_tps['secondary'],
                      tags=['node:' + str(ip) + ':' + str(port),
                            'name:' + str(instance_name)])

    # publish namespace metrics and alerts
    if namespaces not in ERROR_CODES:
        base.init_namespace_list(namespaces)
        for ns in namespaces:
            if username == 'n/s':
                ns_stats = base.get_namespace_statistics(ip, port, ns)
            else:
                ns_stats = base.get_namespace_statistics(
                    ip,
                    port,
                    ns,
                    user=username,
                    password=passwd)
            if ns_stats not in ERROR_CODES:
                for key, value in ns_stats.iteritems():
                    metric_name = 'aerospike.namespace.' + \
                        str(ns) + '.' + str(key)
                    obj.gauge(
                        metric_name,
                        str(value),
                        tags=[
                            'node:' +
                            str(ip) +
                            ':' +
                            str(port),
                            'namespace:' +
                            str(ns),
                            'name:' +
                            str(instance_name)])
                ns_alerts = base.get_namespace_alerts(
                    ns,
                    ns_stats,
                    str(ip) +
                    ':' +
                    str(port))
                for alert in ns_alerts:
                    if alert is not None:
                        obj.event({
                            'timestamp': int(time.time()),
                            'event_type': 'Namespace_Alert',
                            'msg_title': str(alert['msg_title']),
                            'msg_text': str(alert['msg_text']),
                            'alert_type': str(alert['alert_type'])
                        })

    # publish node alerts
    node_alerts = base.get_node_alerts(stats, str(ip) + ':' + str(port))
    for alert in node_alerts:
        if alert is not None:
            obj.event({
                'timestamp': int(time.time()),
                'event_type': 'Node_Alert',
                'msg_title': str(alert['msg_title']),
                'msg_text': str(alert['msg_text']),
                'alert_type': str(alert['alert_type'])
            })
    log.print_log(obj, 'function: get_metrics   |output:- No return Values')

    log_messages = base.get_log_messages()
    for message in log_messages:
        log.print_log(obj, message['message'], message['error_flag'])
    return namespaces

# check for password validity


def is_valid_password(password, key):

    if len(password) != 60 or password.startswith("$2a$") == False:
        return True
    return False
