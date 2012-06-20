"""
Performance tests to help profile dogstatsd. It does away with threads for easy
profiling.
"""

from dogstatsd import MetricsAggregator
from multiprocessing import Process


flush_count = 10
loops_per_flush = 10000
metric_count = 5


aggregator = MetricsAggregator('my.host')

for _ in xrange(flush_count):
    for i in xrange(loops_per_flush):
        # Counters
        for j in xrange(metric_count):
            aggregator.submit('counter.%s:%s|c' % (j, i))
            aggregator.submit('gauge.%s:%s|g' % (j, i))
            aggregator.submit('histogram.%s:%s|h' % (j, i))
    aggregator.flush()
