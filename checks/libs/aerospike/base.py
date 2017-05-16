# stdlib

import calendar
from collections import deque
from datetime import datetime

# project
import citrusleaf as cl
from constants import NOT_SUPPORTED
from constants import queue_limit
from constants import TPS_HISTORY_LIMIT
from constants import UNABLE_TO_CONNECT
import convertor


"""Variable definitions"""


statistics_history = {}
ts = datetime.utcnow()
ts = int(calendar.timegm(ts.timetuple()) * 1e3 + ts.microsecond / 1e3)
read_tps_history = deque([dict(x=ts, secondary=None, y=None)],
                         maxlen=TPS_HISTORY_LIMIT)
write_tps_history = deque([dict(x=ts, secondary=None, y=None)],
                          maxlen=TPS_HISTORY_LIMIT)
node_alert_attributes = {
    "free-pct-disk": {
        "status": "success",
        "error": "Free disk space is below 5 percent now",
        "warning": "Free disk space is below 10 percent now",
        "success": "Free disk space is above 10 percent now"
    },
    "client_connections": {
        "status": "success",
        "error": "Client connections are above 95 percent of limit now",
        "warning": "Client connections are above 90 percent of limit now",
        "success": "Client connections are below 90 percent of limit now"
    },
    "queue": {
        "status": "success",
        "error": "",
        "warning": "Transactions pending in queue are greater than " +
        str(queue_limit) + " now",
        "success": "Transactions pending in queue are less than " +
        str(queue_limit) + " now"
    },
    "node_status": {
        "status": "success",
        "error": "Node is down",
        "warning": "",
        "success": "Node is up now"
    }
}
namespace_alert_attributes = {
    "available_pct": {
        "status": "success",
        "error": "Contiguous Disk space available for new writes on" +
        " namespace is below 10 percent",
        "warning": "Contiguous Disk space available for new writes on" +
        " namespace is below 20 percent",
        "success": "Contiguous Disk space available for new writes on" +
        "namespace is above 20 percent now"
    },
    "free-pct-disk": {
        "status": "success",
        "error": "Used disk space for namespace is above stop writes limit",
        "warning": "",
        "success": "Used disk space for namespace is below stop writes " +
        "limit now"
    },
    "free-pct-memory": {
        "status": "success",
        "error": "Used memory space for namespace is above stop writes limit",
        "warning": "",
        "success": "Used memory space for namespace is below stop writes " +
        "limit now"
    },
    "free-pct-disk-HW": {
        "status": "success",
        "error": "",
        "warning": "Used disk space for namespace is above high water mark",
        "success": "Used disk space for namespace is below high water mark now"
    },
    "free-pct-memory-HW": {
        "status": "success",
        "error": "",
        "warning": "Used memory space for namespace is above high water mark",
        "success": "Used memory space for namespace is below high water " +
        "mark now"
    }
}
namespace_alerts = dict()
log_messages = []

# clear log messages


def clear_log_messages():

    global log_messages
    del log_messages[:]

# add message to log_message list


def add_log_message(message, error_flag=False):

    global log_messages
    log_messages.append(dict(message=message, error_flag=error_flag))

# get log messages


def get_log_messages():

    global log_messages
    return log_messages

"""Node Metrics"""


# returns node information; {} for invalid
def get_node_info(ip, port, user=None, password=None):

    add_log_message(
        'function: get_node_info   |input:- ip:%s,port:%s,user:%s,password:%s'
        % (ip, port, user, password))
    if user is None:
        info = cl.citrusleaf_info(ip, port)
    else:
        info = cl.citrusleaf_info(ip, port, user=user, password=str(password))
    if (
            info in cl.ERROR_CODES or
            info == {'security error - not authenticated': ''}):
        add_log_message(
            'Node Info received from server: %s' % (info), error_flag=True)
        add_log_message(
            'function: get_node_info   |output:- {}', error_flag=True)
        return {}
    add_log_message('function: get_node_info   |output:- %s' % (info))
    return info

# returns node statistics; {node_status='off'} for invalid


def get_node_statistics(info):

    add_log_message('function: get_node_statistics  |input:- info:%s' % (info))
    statistics = info.get("statistics", None)
    if statistics is None:
        add_log_message('Node statistics are None!',
                        error_flag=True)
        add_log_message(
            'function: get_node_statistics   |output:- {node_status: off}',
            error_flag=True)
        return dict(node_status="off")
    statistics = convertor.text_to_list(statistics)
    statistics = convertor.list_to_dict(statistics)
    statistics['timestamp'] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    cluster_integrity = statistics.get('cluster_integrity', None)
    if str(cluster_integrity).lower() == 'true':
        statistics['cluster_integrity'] = 1
    else:
        statistics['cluster_integrity'] = 0
    add_log_message('function: get_node_statistics   |output:- %s'
                    % (statistics))
    return statistics

# returns node memory stats; {free-bytes-memory='n/s'} for invalid


def get_memory_stats(statistics):

    add_log_message(
        'function: get_memory_stats  |input:- stats:%s' %
        (statistics))
    memory_stats = dict()
    try:
        memory_stats['used-bytes-memory'] = int(
            statistics.get('used-bytes-memory', NOT_SUPPORTED))
        memory_stats['total-bytes-memory'] = int(
            statistics.get('total-bytes-memory', NOT_SUPPORTED))
        memory_stats['free-bytes-memory'] = memory_stats[
            'total-bytes-memory'] - memory_stats['used-bytes-memory']
    except ValueError:
        memory_stats['free-bytes-memory'] = NOT_SUPPORTED
        memory_stats['total-bytes-memory'] = NOT_SUPPORTED
    add_log_message(
        'function: get_memory_stats  |output:- %s' %
        (memory_stats))
    return memory_stats

# returns node disk stats; {free-bytes-disk='n/s'} for invalid


def get_disk_stats(statistics):

    add_log_message(
        'function: get_disk_stats  |input:- stats:%s' %
        (statistics))
    disk_stats = dict()
    try:
        disk_stats['used-bytes-disk'] = int(statistics.get('used-bytes-disk',
                                                           NOT_SUPPORTED))
        disk_stats['total-bytes-disk'] = int(statistics.get('total-bytes-disk',
                                                            NOT_SUPPORTED))
        disk_stats['free-bytes-disk'] = disk_stats[
            'total-bytes-disk'] - disk_stats['used-bytes-disk']
    except ValueError:
        disk_stats['free-bytes-disk'] = NOT_SUPPORTED
        disk_stats['total-bytes-disk'] = NOT_SUPPORTED
    add_log_message('function: get_disk_stats  |output:- %s' % (disk_stats))
    return disk_stats

# returns node free-bytes-disk value; n/s for invalid


def get_free_disk_stats(statistics):

    disk_stats = get_disk_stats(statistics)
    return disk_stats['free-bytes-disk']

# returns node free-bytes-memory value; n/s for invalid


def get_free_memory_stats(statistics):

    memory_stats = get_memory_stats(statistics)
    return memory_stats['free-bytes-memory']

# returns node toal-bytes-disk value; n/s for invalid


def get_total_disk_stats(statistics):

    disk_stats = get_disk_stats(statistics)
    return disk_stats['total-bytes-disk']

# returns node total-bytes-memory value; n/s for invalid


def get_total_memory_stats(statistics):

    memory_stats = get_memory_stats(statistics)
    return memory_stats['total-bytes-memory']

# returns number of nodes in cluster; None for invalid


def get_no_of_nodes(statistics):

    return statistics.get('cluster_size', None)

# returns node latency; {} for invalid


def get_node_latency(ip, port, user=None, password=None):

    msg1 = 'function: get_node_latency   |input:- ip:'
    msg2 = '%s,port:%s,user:%s,password:%s' % (ip, port, user, password)
    add_log_message(msg1 + msg2)
    latency = dict()
    if user is None:
        result = cl.citrusleaf_info(ip, port, "latency:")
    else:
        result = cl.citrusleaf_info(ip, port, "latency:", user=user,
                                    password=str(password))

    if result in cl.ERROR_CODES or "error" in result:
        add_log_message(
            'Node Latency received from server: %s' %
            (result),
            error_flag=True)
        add_log_message(
            'function: get_node_latency   |output:- {}', error_flag=True)
        return {}

    rows = convertor.text_to_list(result)
    for i in range(0, len(rows), 2):

        if not rows[i]:
            continue
        ind = rows[i].index(':')
        op = rows[i][:ind]
        if op == "writes_reply":
            continue
        rows[i] = rows[i][ind + 1:]

        keys = convertor.text_to_list(rows[i], ",")
        values = convertor.text_to_list(rows[i + 1], ",")

        keys[0] = keys[0].split("-")[0]
        ops_per_sec = float(values[1])

        latency[op] = {'timestamp': convertor.time_average(values[0], keys[0]),
                       'data': [],
                       'ops/sec': ops_per_sec
                       }

        less_than_1 = 0.0 if ops_per_sec == 0 else 100.0

        previous_key = ""
        previous_value = 0.0
        for key, value in zip(
                list(reversed(keys))[:len(keys) - 2], list(reversed(
                    values))[:len(keys) - 2]):
            pct = float(value) - previous_value
            previous_value = float(value)
            original_key = key
            if previous_key != "":
                key = "greater than " + key[1:] + " to less than "
                key = key + previous_key[1:]
            else:
                key = "greater than " + key[1:]
            previous_key = original_key
            less_than_1 -= pct
            value = ops_per_sec * pct / 100
            latency[op]['data'] = [{key: dict(
                value=value, pct=pct)}] + latency[op]['data']

        less_than_1_value = ops_per_sec * less_than_1 / 100
        latency[op]['data'] = [{"less than 1ms": dict(
            value=less_than_1_value, pct=less_than_1)}] + latency[op]['data']
    add_log_message('function: get_node_latency   |output:- %s' % (latency))
    return latency

# returns node tps parameter value ; {} for invalid


def extract_tps_parameter_from_statistics(statistics):

    global statistics_history, read_tps_history, write_tps_history

    add_log_message(
        'function: extract_tps_parameter_from_statistics  |input:- stats:%s'
        % (statistics))

    if statistics.get("node_status") == "off":
        add_log_message('Received Node status OFF in statistics',
                        error_flag=True)
        add_log_message(
            'function: extract_tps_parameter_from_statistics  |output:- {}',
            error_flag=True)
        return {}

    old_stat_read_reqs = statistics_history.get('stat_read_reqs',
                                                NOT_SUPPORTED)
    old_stat_read_success = statistics_history.get('stat_read_success',
                                                   NOT_SUPPORTED)
    old_stat_write_reqs = statistics_history.get('stat_write_reqs',
                                                 NOT_SUPPORTED)
    old_stat_write_success = statistics_history.get('stat_write_success',
                                                    NOT_SUPPORTED)

    new_stat_read_reqs = statistics.get('stat_read_reqs', NOT_SUPPORTED)
    new_stat_read_success = statistics.get('stat_read_success', NOT_SUPPORTED)
    new_stat_write_reqs = statistics.get('stat_write_reqs', NOT_SUPPORTED)
    new_stat_write_success = statistics.get('stat_write_success',
                                            NOT_SUPPORTED)

    add_log_message('O_S_R_R:%s  O_S_R_S:%s  O_S_W_R:%s  O_S_W_S:%s'
                    % (str(old_stat_read_reqs), str(old_stat_read_success),
                       str(old_stat_write_reqs), str(old_stat_write_success)))
    add_log_message('N_S_R_R:%s  N_S_R_S:%s  N_S_W_R:%s  N_S_W_S:%s'
                    % (str(new_stat_read_reqs), str(new_stat_read_success),
                       str(new_stat_write_reqs), str(new_stat_write_success)))

    timestamp = datetime.utcnow()
    timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                          timestamp.microsecond / 1e3)

    if True not in map(lambda x: x == NOT_SUPPORTED,
                       [new_stat_write_reqs,
                        old_stat_write_reqs,
                        new_stat_write_success,
                        old_stat_write_success]):
        total_write_tps = int(new_stat_write_reqs) - int(old_stat_write_reqs)
        success_write_tps = int(new_stat_write_success) - int(
            old_stat_write_success)

        old_timestamp = write_tps_history[-1]['x']
        time_delta = timestamp - datetime.utcfromtimestamp(
            old_timestamp / 1000.0)
        time_difference = (time_delta.days * 86400) + (
            time_delta.seconds) + (time_delta.microseconds / 1000000.0)

        total_write_tps = total_write_tps / time_difference
        total_write_tps = round(
            total_write_tps,
            1) if total_write_tps < 1 else round(total_write_tps)
        success_write_tps = success_write_tps / time_difference
        success_write_tps = round(
            success_write_tps,
            1) if success_write_tps < 1 else round(success_write_tps)
        if success_write_tps < 0:
            success_write_tps = 0
        if total_write_tps < 0:
            total_write_tps = 0
        add_log_message('S_W_T:%s  T_W_T:%s  T_D:%s'
                        % (str(success_write_tps), str(total_write_tps),
                           str(time_difference)))
        write_tps_history.append(
            dict(
                x=timestamp_posix,
                secondary=total_write_tps,
                y=success_write_tps))
    else:
        write_tps_history.append(dict(x=timestamp_posix,
                                      secondary=None, y=None))

    if True not in map(lambda x: x == NOT_SUPPORTED,
                       [new_stat_read_reqs,
                        old_stat_read_reqs,
                        new_stat_read_success,
                        old_stat_read_success]):
        total_read_tps = int(new_stat_read_reqs) - int(old_stat_read_reqs)
        success_read_tps = int(new_stat_read_success) - int(
            old_stat_read_success)
        old_timestamp = read_tps_history[-1]['x']

        time_delta = timestamp - datetime.utcfromtimestamp(
            old_timestamp / 1000.0)
        time_difference = (time_delta.days * 86400) + (time_delta.seconds) + (
            time_delta.microseconds / 1000000.0)
        total_read_tps = total_read_tps / time_difference
        total_read_tps = round(
            total_read_tps,
            1) if total_read_tps < 1 else round(total_read_tps)
        success_read_tps = success_read_tps / time_difference
        success_read_tps = round(
            success_read_tps,
            1) if success_read_tps < 1 else round(success_read_tps)
        if success_read_tps < 0:
            success_read_tps = 0
        if total_read_tps < 0:
            total_read_tps = 0
        add_log_message(
            'S_R_T:%s  T_R_T:%s  T_D:%s' %
            (str(success_read_tps),
             str(total_read_tps),
                str(time_difference)))
        read_tps_history.append(
            dict(
                x=timestamp_posix,
                secondary=total_read_tps,
                y=success_read_tps))
    else:
        read_tps_history.append(dict(x=timestamp_posix,
                                     secondary=None, y=None))
    statistics_history = statistics
    add_log_message(
        'function: extract_tps_parameter_from_statistics  |' +
        'output:- No return Values')

# returns node read_tps values


def get_read_tps():

    read_tps = read_tps_history[-1]
    return read_tps

# returns node write_tps values


def get_write_tps():

    write_tps = write_tps_history[-1]
    return write_tps

"""Node Alerts"""

# calculates node disk alert; returns None for no alert


def get_disk_alert(statistics, node_address):

    global node_alert_attributes
    disk = statistics.get('free-pct-disk', None)
    total_disk = statistics.get('total-bytes-disk', None)

    if total_disk is None or disk is None or int(total_disk) <= 0:
        return None
    try:
        if int(disk) < 5:
            status = 'error'
        elif int(disk) < 10:
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        add_log_message(
            'function: get_disk_alert- Exception for int conversion of %s'
            % (disk), error_flag=True)
        return None
    if str(node_alert_attributes['free-pct-disk']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        node_alert_attributes['free-pct-disk']['status'] = str(status)
        return dict(alert_type=str(status), timestamp=str(timestamp_posix),
                    msg_text=str(node_address) + ':' +
                    str(node_alert_attributes['free-pct-disk'][status]),
                    msg_title='Node status Notification')
    return None

# calculates node status alert; returns None for no alert


def get_node_status_alert(statistics, node_address):

    global node_alert_attributes
    node = statistics.get('node_status', None)

    if node is 'off':
        status = 'error'
    else:
        status = 'success'
    if str(node_alert_attributes['node_status']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        node_alert_attributes['node_status']['status'] = str(status)
        return dict(alert_type=str(status), timestamp=str(timestamp_posix),
                    msg_text=str(node_address) + ':' +
                    str(node_alert_attributes['node_status'][status]),
                    msg_title='Node status Notification')
    return None

# calculates node client connections alert; returns None for no alert


def get_client_conn_alert(statistics, node_address):

    global node_alert_attributes
    client_connections = statistics.get('client_connections', None)
    proto_fd_max = statistics.get('proto-fd-max', None)

    if client_connections is None or proto_fd_max is None:
        return None

    try:
        if 100 * (int(client_connections) / int(proto_fd_max)) > 95:
            status = 'error'
        elif 100 * (int(client_connections) / int(proto_fd_max)) > 90:
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        add_log_message(
            'function: get_client_conn_alert- Exception for int conversion' +
            ' of %s or %s' % (client_connections, proto_fd_max),
            error_flag=True)
        return None
    if str(node_alert_attributes['client_connections']['status']) != str(
            status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        node_alert_attributes['node_status']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ':' +
                    str(node_alert_attributes['client_connections'][status]),
                    msg_title='Client connections Notification')
    return None

# calculates queue size alert; returns None for no alert


def get_queue_alert(statistics, node_address):

    global node_alert_attributes
    queue = statistics.get('queue', None)
    if queue is None:
        return None
    try:
        if int(queue) > 10000:
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        add_log_message(
            'function: get_queue_alert- Exception for int conversion of %s'
            % (queue), error_flag=True)
        return None
    if str(node_alert_attributes['queue']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        node_alert_attributes['node_status']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ':' +
                    str(node_alert_attributes['queue'][status]),
                    msg_title='Queue Notification')
    return None

# gathers all node alerts; returns [None, None..] list for no alerts


def get_node_alerts(statistics, node_address):

    add_log_message(
        'function: get_node_alerts  |input:- statistics:%s,node_address:%s'
        % (statistics, node_address))
    alert_list = [
        get_node_status_alert(statistics, node_address),
        get_disk_alert(statistics, node_address),
        get_client_conn_alert(statistics, node_address),
        get_queue_alert(statistics, node_address)
    ]
    add_log_message('function: get_node_alerts  |output:- %s' % (alert_list))
    return alert_list


"""Namespace Metrics"""

# get namespaces ; -1 in erroneous condition


def get_namespaces(ip, port, user=None, password=None):

    add_log_message(
        'function: get_namespaces   |input:- ip:%s,port:%s,user:%s,password:%s'
        % (ip, port, user, password))
    if user is None:
        ns_list = cl.citrusleaf_info(ip, port, 'namespaces')
    else:
        ns_list = cl.citrusleaf_info(ip, port, 'namespaces', user=user,
                                     password=str(password))
    if ns_list in cl.ERROR_CODES:
        add_log_message('Namespaces List received from server: %s'
                        % ns_list, error_flag=True)
        add_log_message('function: get_namespaces   |output:- %s'
                        % (UNABLE_TO_CONNECT), error_flag=True)
        return UNABLE_TO_CONNECT
    add_log_message('function: get_namespaces   |output:- %s'
                    % (set(convertor.text_to_list(ns_list, ';'))))
    return set(convertor.text_to_list(ns_list, ';'))


def init_namespace_list(ns_list):

    add_log_message('function: init_namespace_list   |input:- %s' % (ns_list))
    add_log_message('Namespace_Alerts before:  %s' % (namespace_alerts))
    if namespace_alerts == {}:
        for ns in ns_list:
            namespace_alerts[ns] = namespace_alert_attributes
    else:
        for ns in ns_list:
            if ns not in namespace_alerts:
                namespace_alerts[ns] = namespace_alert_attributes
    add_log_message('Namespace_Alerts after:  %s' % (namespace_alerts))
    add_log_message('function: init_namespace_list   |output:- ' +
                    'No return Values')


# get namespace statistics; -1 in erroneous condition
def get_namespace_statistics(ip, port, namespace, user=None, password=None):

    msg1 = 'function: get_namespace_statistics   |input:- '
    msg2 = 'ip:%s,port:%s,namespace:%s,user:%s,password:%s' % (
        ip, port, namespace, user, password)
    add_log_message(msg1 + msg2)
    if user is None:
        ns_stats = cl.citrusleaf_info(ip, port, 'namespace/%s' % namespace)
        ns_configs = cl.citrusleaf_info(
            ip,
            port,
            'get-config:context=namespace;id=%s' %
            namespace)
    else:
        ns_stats = cl.citrusleaf_info(ip, port, 'namespace/%s' % namespace,
                                      user=user, password=str(password))
        ns_configs = cl.citrusleaf_info(
            ip,
            port,
            'get-config:context=namespace;id=%s' %
            namespace,
            user=user,
            password=str(password))
    if ns_stats in cl.ERROR_CODES:
        add_log_message('Namespace statistics returned from server: %s'
                        % (ns_stats), error_flag=True)
        add_log_message('function: get_namespace_statistics   |output:- %s'
                        % (UNABLE_TO_CONNECT), error_flag=True)
        return UNABLE_TO_CONNECT
    stats = convertor.list_to_dict(convertor.text_to_list(ns_stats))
    configs = convertor.list_to_dict(convertor.text_to_list(ns_configs))
    diff = set(stats.keys()) - set(configs.keys())
    actual_stats = dict()
    for key in diff:
        actual_stats[key] = stats[key]
    hwm_breached = actual_stats.get('hwm-breached', None)
    if str(hwm_breached).lower() == 'true':
        actual_stats['hwm-breached'] = 1
    else:
        actual_stats['hwm-breached'] = 0
    stop_writes = actual_stats.get('stop-writes', None)
    if str(stop_writes).lower() is 'true':
        actual_stats['stop-writes'] = 1
    else:
        actual_stats['stop-writes'] = 0
    add_log_message(
        'function: get_namespace_statistics   |output:- %s' %
        (actual_stats))
    return actual_stats


"""Namespace Alerts"""


def get_available_pct_alert(ns, ns_stats, node_address):

    available_pct = ns_stats.get('available_pct', None)
    if available_pct is None:
        return None
    try:
        if int(available_pct) < 10:
            status = 'error'
        elif int(available_pct) < 20:
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        msg1 = 'function: get_available_pct_alert- Exception for int '
        msg2 = 'conversion of %s' % (available_pct)
        add_log_message(msg1 + msg2, error_flag=True)
        return None
    if str(namespace_alerts[ns]['available_pct']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        namespace_alerts[ns]['available_pct']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ';' + str(ns) + '-' +
                    str(namespace_alerts[ns]['available_pct'][status]),
                    msg_title='Namespace Disk Available Notification')
    return None


def get_free_pct_disk_alert(ns, ns_stats, node_address):

    free_disk = ns_stats.get('free-pct-disk', None)
    stop_writes = ns_stats.get('stop-writes-pct', None)
    if free_disk is None or stop_writes is None:
        return
    try:
        used_disk = int(100 - int(free_disk))
        if int(used_disk) > int(stop_writes):
            status = 'error'
        else:
            status = 'success'
    except ValueError:
        msg1 = 'function: get_free_pct_disk_alert- Exception for int '
        msg2 = 'conversion of %s or %s or %s' % (
            free_disk, used_disk, stop_writes)
        add_log_message(msg1 + msg2, error_flag=True)
        return None
    if str(namespace_alerts[ns]['free-pct-disk']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        namespace_alerts[ns]['free-pct-disk']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ';' + str(ns) + '-' +
                    str(namespace_alerts[ns]['free-pct-disk'][status]),
                    msg_title='Namespace Disk Available Notification')
    return None


def get_free_pct_memory_alert(ns, ns_stats, node_address):

    free_memory = ns_stats.get('free-pct-memory')
    stop_writes = ns_stats.get('stop-writes-pct')
    if free_memory is None or stop_writes is None:
        return
    try:
        used_memory = int(100 - int(free_memory))
        if int(used_memory) > int(stop_writes):
            status = 'error'
        else:
            status = 'success'
    except ValueError:
        msg1 = 'function: get_free_pct_memory_alert- Exception for int'
        msg2 = 'conversion of %s or %s or %s' % (
            free_memory, used_memory, stop_writes)
        add_log_message(msg1 + msg2, error_flag=True)
        return None
    if str(namespace_alerts[ns]['free-pct-memory']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        namespace_alerts[ns]['free-pct-memory']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ';' + str(ns) + '-' +
                    str(namespace_alerts[ns]['free-pct-memory'][status]),
                    msg_title='Namespace Memory Available Notification')
    return None


def get_free_pct_disk_HW_alert(ns, ns_stats, node_address):

    free_disk = ns_stats.get('free-pct-disk', None)
    high_water = ns_stats.get('high-water-disk-pct', None)
    if free_disk is None or high_water is None:
        return None
    try:
        used_disk = int(100 - int(free_disk))
        if int(used_disk) > int(high_water):
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        msg1 = 'function: get_free_pct_disk_HW_alert- Exception for int '
        msg2 = 'conversion of %s or %s or %s' % (
            free_disk, used_disk, high_water)
        add_log_message(msg1 + msg2, error_flag=True)
        return None
    if str(namespace_alerts[ns]['free-pct-disk-HW']['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        namespace_alerts[ns]['free-pct-disk-HW']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ';' + str(ns) + '-' +
                    str(namespace_alerts[ns]['free-pct-disk-HW'][status]),
                    msg_title='Namespace Disk Available Notification')
    return None


def get_free_pct_memory_HW_alert(ns, ns_stats, node_address):

    free_memory = ns_stats.get('free-pct-memory')
    high_water = ns_stats.get('high-water-memory-pct')
    if free_memory is None or high_water is None:
        return None
    try:
        used_memory = int(100 - int(free_memory))
        if int(used_memory) > int(high_water):
            status = 'warning'
        else:
            status = 'success'
    except ValueError:
        msg1 = 'function: get_free_pct_memory_HW_alert- Exception for int '
        msg2 = 'conversion of %s or %s or %s' % (
            free_memory, used_memory, high_water)
        add_log_message(msg1 + msg2, error_flag=True)
        return None
    if str(namespace_alerts[ns]['free-pct-memory-HW']
           ['status']) != str(status):
        timestamp = datetime.utcnow()
        timestamp_posix = int(calendar.timegm(timestamp.timetuple()) * 1e3 +
                              timestamp.microsecond / 1e3)
        namespace_alerts[ns]['free-pct-memory-HW']['status'] = str(status)
        return dict(timestamp=str(timestamp_posix), alert_type=str(status),
                    msg_text=str(node_address) + ';' + str(ns) + '-' +
                    str(namespace_alerts[ns]['free-pct-memory-HW'][status]),
                    msg_title='Namespace Memory Available Notification')
    return None


def get_namespace_alerts(ns, ns_stats, node_address):

    add_log_message(
        'function: get_namespace_alerts   |input:- namespace:%s,' % (ns) +
        'namespace_stats:%s,node_address:%s' % (ns_stats, node_address))
    ns_alert_list = [
        get_available_pct_alert(ns, ns_stats, node_address),
        get_free_pct_disk_alert(ns, ns_stats, node_address),
        get_free_pct_memory_alert(ns, ns_stats, node_address),
        get_free_pct_disk_HW_alert(ns, ns_stats, node_address),
        get_free_pct_memory_HW_alert(ns, ns_stats, node_address)
    ]
    add_log_message(
        'function: get_namespace_alerts   |output:- %s' %
        (ns_alert_list))
    return ns_alert_list
