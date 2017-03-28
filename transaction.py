# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from datetime import datetime, timedelta
import logging
from operator import attrgetter
import sys
import time

# 3rd party
from tornado import ioloop

# project
from checks.check_status import ForwarderStatus
from util import plural

log = logging.getLogger(__name__)

FLUSH_LOGGING_PERIOD = 20
FLUSH_LOGGING_INITIAL = 5

class Transaction(object):

    def __init__(self):

        self._id = None
        self._error_count = 0
        self._next_flush = datetime.utcnow()
        self._size = None

    def get_id(self):
        return self._id

    def set_id(self, new_id):
        assert self._id is None
        self._id = new_id

    def inc_error_count(self):
        self._error_count = self._error_count + 1

    def get_error_count(self):
        return self._error_count

    def get_size(self):
        if self._size is None:
            self._size = sys.getsizeof(self)

        return self._size

    def get_next_flush(self):
        return self._next_flush

    def compute_next_flush(self,max_delay):
        # Transactions are replayed, try to send them faster for newer transactions
        # Send them every MAX_WAIT_FOR_REPLAY at most
        td = timedelta(seconds=self._error_count * 20)
        if td > max_delay:
            td = max_delay

        newdate = datetime.utcnow() + td
        self._next_flush = newdate.replace(microsecond=0)

    def time_to_flush(self,now = datetime.utcnow()):
        return self._next_flush <= now

    def flush(self):
        raise NotImplementedError("To be implemented in a subclass")

class TransactionManager(object):
    """Holds any transaction derived object list and make sure they
       are all commited, without exceeding parameters (throttling, memory consumption) """

    def __init__(self, max_wait_for_replay, max_queue_size, throttling_delay,
                 max_parallelism=1, max_endpoint_errors=4):
        self._MAX_WAIT_FOR_REPLAY = max_wait_for_replay
        self._MAX_QUEUE_SIZE = max_queue_size
        self._THROTTLING_DELAY = throttling_delay
        self._MAX_PARALLELISM = max_parallelism
        self._MAX_ENDPOINT_ERRORS = max_endpoint_errors
        self._MAX_FLUSH_DURATION = timedelta(seconds=10)

        self._flush_without_ioloop = False # useful for tests

        self._transactions = []  # List of all non commited transactions
        self._total_count = 0  # Maintain size/count not to recompute it everytime
        self._total_size = 0
        self._flush_count = 0
        self._running_flushes = 0
        self._transactions_received = 0
        self._transactions_flushed = 0

        self._transactions_rejected = 0

        # Global counter to assign a number to each transaction: we may have an issue
        #  if this overlaps
        self._counter = 0

        self._trs_to_flush = None # Current transactions being flushed
        self._last_flush = datetime.utcnow() # Last flush (for throttling)

        # Error management
        self._endpoints_errors = {}
        self._finished_flushes = 0

        # Track an initial status message.
        ForwarderStatus().persist()

    def get_transactions(self):
        return self._transactions

    def print_queue_stats(self):
        log.debug("Queue size: at %s, %s transaction(s), %s KB" %
            (time.time(), self._total_count, (self._total_size/1024)))

    def get_tr_id(self):
        self._counter = self._counter + 1
        return self._counter

    def append(self,tr):

        # Give the transaction an id
        tr.set_id(self.get_tr_id())

        # Check the size
        tr_size = tr.get_size()

        log.debug("New transaction to add, total size of queue would be: %s KB" %
            ((self._total_size + tr_size) / 1024))

        if (self._total_size + tr_size) > self._MAX_QUEUE_SIZE:
            log.warn("Queue is too big, removing old transactions...")
            new_trs = sorted(self._transactions,key=attrgetter('_next_flush'), reverse = True)
            for tr2 in new_trs:
                if (self._total_size + tr_size) > self._MAX_QUEUE_SIZE:
                    self._remove(tr2)
                    log.warn("Removed transaction %s from queue" % tr2.get_id())

        # Done
        self._transactions.append(tr)
        self._total_count += 1
        self._transactions_received += 1
        self._total_size = self._total_size + tr_size

        log.debug("Transaction %s added" % (tr.get_id()))
        self.print_queue_stats()

    def _remove(self, tr):
        '''Safely remove transaction from list'''
        try:
            self._transactions.remove(tr)
        except ValueError:
            # Should not happen if we order the queue consistently, but we should catch the error anyway
            log.warn("Tried to remove transaction %s from queue but it was not in the queue anymore.", tr.get_id())
        else:
            self._total_count -= 1
            self._total_size -= tr.get_size()

    def flush(self):

        if self._trs_to_flush is not None:
            log.debug("A flush is already in progress, not doing anything")
            return

        to_flush = []
        # Do we have something to do ?
        now = datetime.utcnow()
        for tr in self._transactions:
            if tr.time_to_flush(now):
                to_flush.append(tr)

        count = len(to_flush)
        should_log = self._flush_count + 1 <= FLUSH_LOGGING_INITIAL or (self._flush_count + 1) % FLUSH_LOGGING_PERIOD == 0
        if count > 0:
            if should_log:
                log.info("Flushing %s transaction%s during flush #%s" % (count,plural(count), str(self._flush_count + 1)))
            else:
                log.debug("Flushing %s transaction%s during flush #%s" % (count,plural(count), str(self._flush_count + 1)))

            self._endpoints_errors = {}
            self._finished_flushes = 0

            # We sort LIFO-style, taking into account errors
            self._trs_to_flush = sorted(to_flush, key=lambda tr: (- tr._error_count, tr._id))
            self._flush_time = datetime.utcnow()
            self.flush_next()
        else:
            if should_log:
                log.info("No transaction to flush during flush #%s" % str(self._flush_count + 1))
            else:
                log.debug("No transaction to flush during flush #%s" % str(self._flush_count + 1))

        if self._flush_count + 1 == FLUSH_LOGGING_INITIAL:
            log.info("First flushes done, next flushes will be logged every %s flushes." % FLUSH_LOGGING_PERIOD)

        self._flush_count += 1

        ForwarderStatus(
            queue_length=self._total_count,
            queue_size=self._total_size,
            flush_count=self._flush_count,
            transactions_received=self._transactions_received,
            transactions_flushed=self._transactions_flushed,
            transactions_rejected=self._transactions_rejected).persist()

    def flush_next(self):

        if self._trs_to_flush is not None and len(self._trs_to_flush) > 0:
            # Running for too long?
            if datetime.utcnow() - self._flush_time >= self._MAX_FLUSH_DURATION:
                log.warn('Flush %s is taking more than 10s, stopping it', self._flush_count)
                for tr in self._trs_to_flush:
                    # Recompute these transactions' next flush so that if we hit the max queue size
                    # newer transactions are preserved
                    tr.compute_next_flush(self._MAX_WAIT_FOR_REPLAY)
                self._trs_to_flush = []
                return self.flush_next()

            td = self._last_flush + self._THROTTLING_DELAY - datetime.utcnow()
            delay = td.total_seconds()

            if delay <= 0 and self._running_flushes < self._MAX_PARALLELISM:
                tr = self._trs_to_flush.pop()
                self._running_flushes += 1
                self._last_flush = datetime.utcnow()
                log.debug("Flushing transaction %d", tr.get_id())
                try:
                    tr.flush()
                except Exception as e:
                    log.exception(e)
                    self.tr_error(tr)
                self.flush_next()
            # Every running flushes relaunches a flush once it's finished
            # If we are already at MAX_PARALLELISM, do nothing
            # Otherwise, schedule a flush as soon as possible (throttling)
            elif self._running_flushes < self._MAX_PARALLELISM:
                # Wait a little bit more
                tornado_ioloop = ioloop.IOLoop.current()
                if tornado_ioloop._running:
                    tornado_ioloop.add_timeout(time.time() + delay,
                                               lambda: self.flush_next())
                elif self._flush_without_ioloop:
                    # Tornado is no started (ie, unittests), do it manually: BLOCKING
                    time.sleep(delay)
                    self.flush_next()
        # Setting self._trs_to_flush to None means the flush is over.
        # So it is oly set when there is no more running flushes.
        # (which corresponds to the last flush calling flush_next)
        elif self._running_flushes == 0:
            self._trs_to_flush = None
            log.debug('Flush %s took %ss (%s transactions)',
                      self._flush_count,
                      (datetime.utcnow() - self._flush_time).total_seconds(),
                      self._finished_flushes)
        else:
            log.debug("Flush in progress, %s flushes running", self._running_flushes)

    def tr_error(self, tr):
        self._running_flushes -= 1
        self._finished_flushes += 1
        tr.inc_error_count()
        tr.compute_next_flush(self._MAX_WAIT_FOR_REPLAY)
        log.warn("Transaction %d in error (%s error%s), it will be replayed after %s",
                 tr.get_id(),
                 tr.get_error_count(),
                 plural(tr.get_error_count()),
                 tr.get_next_flush())
        self._endpoints_errors[tr._endpoint] = self._endpoints_errors.get(tr._endpoint, 0) + 1
        # Endpoint failed too many times, it's probably an enpoint issue
        # Let's avoid blocking on it
        if self._endpoints_errors[tr._endpoint] == self._MAX_ENDPOINT_ERRORS:
            new_trs_to_flush = []
            for transaction in self._trs_to_flush:
                if transaction._endpoint != tr._endpoint:
                    new_trs_to_flush.append(transaction)
                else:
                    transaction.compute_next_flush(self._MAX_WAIT_FOR_REPLAY)
            log.debug('Endpoint %s seems down, removed %s transaction from current flush',
                      tr._endpoint,
                      len(self._trs_to_flush) - len(new_trs_to_flush))

            self._trs_to_flush = new_trs_to_flush

    def tr_error_reject_request(self, tr):
        self._running_flushes -= 1
        self._finished_flushes += 1
        tr.inc_error_count()
        log.warn("Transaction %d is %sKB, it has been rejected as too large. "
                 "It will not be replayed.",
                 tr.get_id(),
                 tr.get_size() / 1024)
        self._remove(tr)
        self._transactions_flushed += 1
        self.print_queue_stats()
        self._transactions_rejected += 1
        ForwarderStatus(
            queue_length=self._total_count,
            queue_size=self._total_size,
            flush_count=self._flush_count,
            transactions_received=self._transactions_received,
            transactions_flushed=self._transactions_flushed,
            transactions_rejected=self._transactions_rejected).persist()

    def tr_success(self, tr):
        self._running_flushes -= 1
        self._finished_flushes += 1
        log.debug("Transaction %d completed",  tr.get_id())
        self._remove(tr)
        self._transactions_flushed += 1
        self.print_queue_stats()
