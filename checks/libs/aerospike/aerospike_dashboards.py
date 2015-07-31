datadog_flag = True

try:
    from datadog import initialize, api
except ImportError:
    datadog_flag = False


def get_all_dashboards(api_key, api_app_key, instance_name, ns_name=None):

    global datadog_flag
    if not datadog_flag:
        return None
    options = {
        'api_key': api_key,
        'app_key': api_app_key
    }
    if ns_name is None:
        title = 'Aerospike Dashboard: ' + str(instance_name)
    else:
        title = 'Aerospike Namespace: ' + str(ns_name) + ' Dashboard: ' + str(
            instance_name)
    title = title.lower()

    try:
        initialize(**options)
        response = api.Timeboard.get_all()

        dashboards = response['dashes']
        for dash in dashboards:
            if str(dash['title']).lower() == title:
                return True
        return False
    except:
        """This except cannot be kept  specific. It has to be generic one.
        As It is used to detect failure of initialize function and erroneous
        response"""
        return None


def draw_node_dashboard(api_key, api_app_key, instance_name, node_address):

    global datadog_flag

    if datadog_flag is False:
        return None
    dashboards_response = get_all_dashboards(api_key, api_app_key,
                                             instance_name)

    if dashboards_response is None:
        return None
    else:
        if dashboards_response:
            draw_namespace_flag = False
            return 1

    options = {
        "api_key": str(api_key),
        "app_key": str(api_app_key)
    }

    initialize(**options)

    title = "Aerospike Dashboard: " + str(instance_name)
    description = "An Informative Dashboard about Aerospike Node"

    instance_name = str(instance_name).lower()

    graphs = [
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.cluster_size{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Cluster Size"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.disk_usage_free{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.disk_usage_total{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Disk Usage"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.memory_usage_free{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.memory_usage_total{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Memory Usage"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.successful_read_tps{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.total_read_tps{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Read Throughput"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.successful_write_tps{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.total_write_tps{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Write Throughput"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.node.writes_master{latency_type" +
                        ":less_than_1ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.writes_master{latency_type:" +
                        "greater_than_1ms_to_less_than_8ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.writes_master{latency_type:" +
                        "greater_than_8ms_to_less_than_64ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.writes_master{latency_type:" +
                        "greater_than_64ms,value_type:value,name:" + str(
                            instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Latency: Write Master"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.node.reads{latency_type:" +
                        "less_than_1ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.reads{latency_type:" +
                        "greater_than_1ms_to_less_than_8ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.reads{latency_type:" +
                        "greater_than_8ms_to_less_than_64ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.reads{latency_type:" +
                        "greater_than_64ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Latency: Reads"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.node.query{latency_type:" +
                        "less_than_1ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.query{latency_type:" +
                        "greater_than_1ms_to_less_than_8ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.query{latency_type:" +
                        "greater_than_8ms_to_less_than_64ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.query{latency_type:" +
                        "greater_than_64ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Latency: Query"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.node.udf{latency_type:" +
                        "less_than_1ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.udf{latency_type:" +
                        "greater_than_1ms_to_less_than_8ms," +
                        "value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.udf{latency_type:" +
                        "greater_than_8ms_to_less_than_64ms," +
                        "value_type:value,name:" + str(instance_name) +
                        "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.udf{latency_type:" +
                        "greater_than_64ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Latency: UDF"
        },
        {
            "definition": {
                "events": [],
                "requests": [
                    {
                        "q": "avg:aerospike.node.proxy{latency_type:" +
                        "less_than_1ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.proxy{latency_type:" +
                        "greater_than_1ms_to_less_than_8ms,value_type:" +
                        "value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.proxy{latency_type:" +
                        "greater_than_8ms_to_less_than_64ms," +
                        "value_type:value,name:" + str(instance_name) + "}",
                        "type": "line"
                    },
                    {
                        "q": "aerospike.node.proxy{latency_type:" +
                        "greater_than_64ms,value_type:value,name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "viz": "timeseries"
            },
            "title": "Latency: Proxy"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.objects{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Objects"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.client_connections{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "y = 15000",
                        "label": "High Critical"
                    },
                    {
                        "type": "warning bold",
                        "value": "y = 10000",
                        "label": "High Warning"
                    },
                    {
                        "type": "ok bold",
                        "value": "y = 100",
                        "label": "Low Critical"
                    }
                ]
            },
            "title": "Client Connections"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.stat_rw_timeout{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "y = 10",
                        "label": "High Warning"
                    }
                ]
            },
            "title": "Stat Read-Write Timeout"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.err_out_of_space{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "y = 1",
                        "label": "High Critical"
                    }
                ]
            },
            "title": "Out of Space Error"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.uptime{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "0 < y < 60",
                        "label": "Low Warning"
                    }
                ]
            },
            "title": "Uptime"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.migrate_progress_send{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "y = 1",
                        "label": "High Critical"
                    }
                ]
            },
            "title": "Migrate Process Send"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.migrate_progress_recv{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "error bold",
                        "value": "y = 1",
                        "label": "High Critical"
                    }
                ]
            },
            "title": "Migrate Process Receive"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.err_rw_pending_limit{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Error Read-Write Pending Limit"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.used_bytes_disk{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Used Bytes Disk"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.node.free_pct_disk{name:" +
                        str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "warning bold",
                        "value": "20 < y < 30",
                        "label": "Low Warning"
                    },
                    {
                        "type": "error bold",
                        "value": "0 < y < 20",
                        "label": "Low Critical"
                    }
                ]
            },
            "title": "Free Disk Percentage"
        }
    ]

    template_variables = [{}]

    response = api.Timeboard.create(title=title, description=description,
                         graphs=graphs, template_variables=template_variables)
    return response


def draw_namespace_dashboard(api_key, api_app_key, instance_name, node_address,
                             namespace):

    global datadog_flag

    if datadog_flag is False:
        return None

    options = {
        "api_key": str(api_key),
        "app_key": str(api_app_key)
    }

    initialize(**options)

    dashboards_response = get_all_dashboards(api_key, api_app_key,
                                             instance_name, ns_name=namespace)

    if dashboards_response is None:
        return None
    else:
        if dashboards_response:
            return 1

    title = "Aerospike Namespace: " + str(namespace) + " Dashboard: " + str(
        instance_name)
    description = "An Informative Dashboard about Aerospike Namespace " + str(
        namespace)

    instance_name = str(instance_name).lower()

    graphs = [
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".available_pct{name:" + str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "type": "warning bold",
                        "value": "15 < y < 20",
                        "label": "Low Warning"
                    },
                    {
                        "type": "error bold",
                        "value": "0 < y < 15",
                        "label": "Low Critical"
                    }
                ]
            },
            "title": "Available Percentage"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".hwm_breached{name:" + str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "value": "y = 1",
                        "type": "error bold",
                        "label": "High Warning"
                    }
                ]
            },
            "title": "HWM Breached"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".stop_writes{name:" + str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": [],
                "markers": [
                    {
                        "value": "y = 1",
                        "type": "error bold",
                        "label": "High Warning"
                    }
                ]
            },
            "title": "Stop Writes"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".objects{name:" + str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Objects"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".used_bytes_disk{name:" + str(instance_name) + "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Used Bytes Disk"
        },
        {
            "definition": {
                "viz": "timeseries",
                "requests": [
                    {
                        "q": "avg:aerospike.namespace." + str(namespace) +
                        ".used_bytes_memory{name:" + str(instance_name) +
                        "}",
                        "type": "line"
                    }
                ],
                "events": []
            },
            "title": "Used Bytes Memory"
        }
    ]

    template_variables = [{}]

    response = api.Timeboard.create(title=title, description=description,
                         graphs=graphs, template_variables=template_variables)
    return response
