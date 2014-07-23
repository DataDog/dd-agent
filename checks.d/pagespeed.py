# stdlib
import re
import urllib2
import urlparse

# project
from util import headers
from checks import AgentCheck
from checks.utils import add_basic_auth

class Pagespeed(AgentCheck):
    """Tracks basic ngx_pagespeed/mod_pagespeed metrics via the status module
    * cache_hits
    * cache_misses
    * cache_fallbacks
    * cache_expirations
    * cache_inserts
    * cache_deletes
    * instrumentation_filter_script_added_count
    * cache_extensions
    * not_cacheable
    * critical_css_beacon_filter_script_added_count
    * critical_css_no_beacon_due_to_missing_data
    * critical_css_skipped_due_to_charset
    * critical_images_beacon_filter_script_added_count
    * css_file_count_reduction
    * css_filter_blocks_rewritten
    * css_filter_parse_failures
    * css_filter_fallback_rewrites
    * css_filter_fallback_failures
    * css_filter_rewrites_dropped
    * css_filter_total_bytes_saved
    * css_filter_total_original_bytes
    * css_filter_uses
    * flatten_imports_charset_mismatch
    * flatten_imports_invalid_url
    * flatten_imports_limit_exceeded
    * flatten_imports_minify_failed
    * flatten_imports_recursion
    * flatten_imports_complex_queries
    * css_imports_to_links
    * css_elements_moved
    * domain_rewrites
    * google_analytics_page_load_count
    * google_analytics_rewritten_count
    * image_file_count_reduction
    * image_rewrites
    * image_norewrites_high_resolution
    * image_rewrites_dropped_intentionally
    * image_rewrites_dropped_mime_type_unknown
    * image_rewrites_dropped_server_write_fail
    * image_rewrites_dropped_nosaving_resize
    * image_rewrites_dropped_nosaving_noresize
    * image_rewrites_dropped_due_to_load
    * image_rewrites_squashing_for_mobile_screen
    * image_rewrite_total_bytes_saved
    * image_rewrite_total_original_bytes
    * image_rewrite_uses
    * image_inline
    * image_webp_rewrites
    * image_ongoing_rewrites
    * image_webp_conversion_gif_timeouts
    * image_webp_conversion_png_timeouts
    * image_webp_conversion_jpeg_timeouts
    * image_webp_alpha_timeouts
    * image_webp_opaque_timeouts
    * in_place_oversized_opt_stream
    * in_place_uncacheable_rewrites
    * inserted_ga_snippets
    * javascript_blocks_minified
    * javascript_libraries_identified
    * javascript_minification_failures
    * javascript_total_bytes_saved
    * javascript_total_original_bytes
    * javascript_minify_uses
    * javascript_reducing_minifications
    * javascript_minification_disabled
    * javascript_did_not_shrink
    * javascript_failed_to_write
    * js_file_count_reduction
    * num_local_storage_cache_candidates_found
    * num_local_storage_cache_stored_total
    * num_local_storage_cache_stored_images
    * num_local_storage_cache_stored_css
    * num_local_storage_cache_candidates_added
    * num_local_storage_cache_candidates_removed
    * converted_meta_tags
    * num_distributed_rewrite_successes
    * num_distributed_rewrite_failures
    * num_deadline_alarm_invocations
    * url_trims
    * url_trim_saved_bytes
    * resource_url_domain_rejections
    * rewrite_cached_output_missed_deadline
    * rewrite_cached_output_hits
    * rewrite_cached_output_misses
    * resource_404_count
    * slurp_404_count
    * total_page_load_ms
    * page_load_count
    * resource_fetches_cached
    * resource_fetch_construct_successes
    * resource_fetch_construct_failures
    * num_flushes
    * num_fallback_responses_served
    * num_conditional_refreshes
    * ipro_served
    * ipro_not_in_cache
    * ipro_not_rewritable
    * total_fetch_count
    * total_rewrite_count
    * num_rewrites_executed
    * num_rewrites_dropped
    * num_resource_fetch_successes
    * num_resource_fetch_failures
    * html-worker-queue-depth
    * rewrite-worker-queue-depth
    * low-priority-worked-queue-depth
    * cache_batcher_dropped_gets
    * critical_images_valid_count
    * critical_images_expired_count
    * critical_images_not_found_count
    * critical_css_valid_count
    * critical_css_expired_count
    * critical_css_not_found_count
    * critical_selectors_valid_count
    * critical_selectors_expired_count
    * critical_selectors_not_found_count
    * pcache-cohorts-clientstate_deletes
    * pcache-cohorts-clientstate_hits
    * pcache-cohorts-clientstate_inserts
    * pcache-cohorts-clientstate_misses
    * cache_flush_count
    * cache_flush_timestamp_ms
    * memcache_timeouts
    * memcache_last_error_checkpoint_ms
    * memcache_error_burst_size
    * file_cache_disk_checks
    * file_cache_cleanups
    * file_cache_evictions
    * file_cache_bytes_freed_in_cleanup
    * file_cache_deletes
    * file_cache_hits
    * file_cache_inserts
    * file_cache_misses
    * lru_cache_deletes
    * lru_cache_hits
    * lru_cache_inserts
    * lru_cache_misses
    * shm_cache_deletes
    * shm_cache_hits
    * shm_cache_inserts
    * shm_cache_misses
    * memcached_deletes
    * memcached_hits
    * memcached_inserts
    * memcached_misses
    * compressed_cache_corrupt_payloads
    * compressed_cache_original_size
    * compressed_cache_compressed_size
    * serf_fetch_request_count
    * serf_fetch_bytes_count
    * serf_fetch_time_duration_ms
    * serf_fetch_cancel_count
    * serf_fetch_active_count
    * serf_fetch_timeout_count
    * serf_fetch_failure_count
    * serf_fetch_cert_errors
    * pcache-cohorts-beacon_cohort_deletes
    * pcache-cohorts-beacon_cohort_hits
    * pcache-cohorts-beacon_cohort_inserts
    * pcache-cohorts-beacon_cohort_misses
    * pcache-cohorts-dom_deletes
    * pcache-cohorts-dom_hits
    * pcache-cohorts-dom_inserts
    * pcache-cohorts-dom_misses
    * child_shutdown_count

    Requires php-fpm pools to have the status option.
    See http://www.php.net/manual/de/install.fpm.configuration.php#pm.status-path for more details

    """

    def check(self, instance):
        if 'pagespeed_status_url' not in instance:
            raise Exception('pagespeed instance missing "pagespeed_status_url" value.')
        tags = instance.get('tags', [])
        
        response, content_type = self._get_data(instance)
        metrics = self.parse_text(response, tags)
        
        funcs = {
            'gauge': self.gauge,
            'rate': self.rate,
            'increment': self.increment
        }
        for row in metrics:
            try:
                name, value, tags, metric_type = row
                func = funcs[metric_type]
                func(name, value, tags)
            except Exception:
                self.log.error(u'Could not submit metric: %s' % repr(row))

    def _get_data(self, instance):
        url = instance.get('pagespeed_status_url')
        req = urllib2.Request(url, None, headers(self.agentConfig))
        if 'pagespeed_status_user' in instance and 'pagespeed_status_password' in instance:
            add_basic_auth(req, instance['pagespeed_status_user'], instance['pagespeed_status_password'])

        # Submit a service check for status page availability.
        parsed_url = urlparse.urlparse(url)
        pagespeed_status_host = parsed_url.hostname
        pagespeed_status_port = parsed_url.port or 80
        service_check_name = 'pagespeed_status.can_connect'
        service_check_tags = ['host:%s' % pagespeed_status_host, 'port:%s' % pagespeed_status_port]
        try:
            response = urllib2.urlopen(req)
        except Exception:
            self.service_check(service_check_name, AgentCheck.CRITICAL)
            raise
        else:
            self.service_check(service_check_name, AgentCheck.OK)

        body = response.read()
        resp_headers = response.info()
        return body, resp_headers.get('Content-Type', 'text/plain')

    @classmethod
    def parse_text(cls, response, tags):

        GAUGES = {
            'cache_hits': 'pagespeed.cache.hits',
            'cache_misses': 'pagespeed.cache.misses',
            'cache_fallbacks': 'pagespeed.cache.fallbacks',
            'cache_expirations': 'pagespeed.cache.expirations',
            'cache_inserts': 'pagespeed.cache.inserts',
            'cache_deletes': 'pagespeed.cache.deletes',
            'instrumentation_filter_script_added_count': 'pagespeed.instrumentation_filter_script_added_count',
            'cache_extensions': 'pagespeed.cache.extensions',
            'not_cacheable': 'pagespeed.not_cacheable',
            'critical_css_beacon_filter_script_added_count': 'pagespeed.critical.css.beacon_filter_script_added_count',
            'critical_css_no_beacon_due_to_missing_data': 'pagespeed.critical.css.no_beacon_due_to_missing_data',
            'critical_css_skipped_due_to_charset': 'pagespeed.critical.css.skipped_due_to_charset',
            'critical_images_beacon_filter_script_added_count': 'pagespeed.critical.images.beacon_filter_script_added_count',
            'css_file_count_reduction': 'pagespeed.css_file_count_reduction',
            'css_filter_blocks_rewritten': 'pagespeed.css_filter.blocks_rewritten',
            'css_filter_parse_failures': 'pagespeed.css_filter.parse_failures',
            'css_filter_fallback_rewrites': 'pagespeed.css_filter.fallback_rewrites',
            'css_filter_fallback_failures': 'pagespeed.css_filter.fallback_failures',
            'css_filter_rewrites_dropped': 'pagespeed.css_filter.rewrites_dropped',
            'css_filter_total_bytes_saved': 'pagespeed.css_filter.total_bytes_saved',
            'css_filter_total_original_bytes': 'pagespeed.css_filter.total_original_bytes',
            'css_filter_uses': 'pagespeed.css_filter.uses',
            'flatten_imports_charset_mismatch': 'pagespeed.flatten_imports.charset_mismatch',
            'flatten_imports_invalid_url': 'pagespeed.flatten_imports.invalid_url',
            'flatten_imports_limit_exceeded': 'pagespeed.flatten_imports.limit_exceeded',
            'flatten_imports_minify_failed': 'pagespeed.flatten_imports.minify_failed',
            'flatten_imports_recursion': 'pagespeed.flatten_imports.recursion',
            'flatten_imports_complex_queries': 'pagespeed.flatten_imports.complex_queries',
            'css_imports_to_links': 'pagespeed.css_imports.to_links',
            'css_elements_moved': 'pagespeed.css_elements_moved',
            'domain_rewrites': 'pagespeed.domain_rewrites',
            'google_analytics_page_load_count': 'pagespeed.google_analytics.page_load_count',
            'google_analytics_rewritten_count': 'pagespeed.google_analytics.rewritten_count',
            'image_file_count_reduction': 'pagespeed.image_file_count_reduction',
            'image_rewrites': 'pagespeed.image_rewrites',
            'image_norewrites_high_resolution': 'pagespeed.image_norewrites_high_resolution',
            'image_rewrites_dropped_intentionally': 'pagespeed.image_rewrites_dropped.intentionally',
            'image_rewrites_dropped_mime_type_unknown': 'pagespeed.image_rewrites_dropped.mime_type_unknown',
            'image_rewrites_dropped_server_write_fail': 'pagespeed.image_rewrites.dropped.server_write_fail',
            'image_rewrites_dropped_nosaving_resize': 'pagespeed.image_rewrites.dropped.nosaving_resize',
            'image_rewrites_dropped_nosaving_noresize': 'pagespeed.image_rewrites.dropped.nosaving_noresize',
            'image_rewrites_dropped_due_to_load': 'pagespeed.image_rewrites.dropped.due_to_load',
            'image_rewrites_squashing_for_mobile_screen': 'pagespeed.image_rewrites.squashing_for_mobile_screen',
            'image_rewrite_total_bytes_saved': 'pagespeed.image_rewrite.total_bytes_saved',
            'image_rewrite_total_original_bytes': 'pagespeed.image_rewrite.total_original_bytes',
            'image_rewrite_uses': 'pagespeed.image_rewrite.uses',
            'image_inline': 'pagespeed.image_inline',
            'image_webp_rewrites': 'pagespeed.image_webp.rewrites',
            'image_ongoing_rewrites': 'pagespeed.image_ongoing_rewrites',
            'image_webp_conversion_gif_timeouts': 'pagespeed.image_webp.conversion_gif_timeouts',
            'image_webp_conversion_png_timeouts': 'pagespeed.image_webp.conversion_png_timeouts',
            'image_webp_conversion_jpeg_timeouts': 'pagespeed.image_webp.conversion_jpeg_timeouts',
            'image_webp_alpha_timeouts': 'pagespeed.image_webp.alpha_timeouts',
            'image_webp_opaque_timeouts': 'pagespeed.image_webp.opaque_timeouts',
            'in_place_oversized_opt_stream': 'pagespeed.in_place.oversized_opt_stream',
            'in_place_uncacheable_rewrites': 'pagespeed.in_place.uncacheable_rewrites',
            'inserted_ga_snippets': 'pagespeed.inserted_ga_snippets',
            'javascript_blocks_minified': 'pagespeed.javascript.blocks_minified',
            'javascript_libraries_identified': 'pagespeed.javascript.libraries_identified',
            'javascript_minification_failures': 'pagespeed.javascript.minification_failures',
            'javascript_total_bytes_saved': 'pagespeed.javascript.total_bytes_saved',
            'javascript_total_original_bytes': 'pagespeed.javascript.total_original_bytes',
            'javascript_minify_uses': 'pagespeed.javascript.minify_uses',
            'javascript_reducing_minifications': 'pagespeed.javascript.reducing_minifications',
            'javascript_minification_disabled': 'pagespeed.javascript.minification_disabled',
            'javascript_did_not_shrink': 'pagespeed.javascript.did_not_shrink',
            'javascript_failed_to_write': 'pagespeed.javascript.failed_to_write',
            'js_file_count_reduction': 'pagespeed.js_file_count_reduction',
            'num_local_storage_cache_candidates_found': 'pagespeed.num_local_storage_cache.candidates.found',
            'num_local_storage_cache_stored_total': 'pagespeed.num_local_storage_cache.stored.total',
            'num_local_storage_cache_stored_images': 'pagespeed.num_local_storage_cache.stored.images',
            'num_local_storage_cache_stored_css': 'pagespeed.num_local_storage_cache.stored.css',
            'num_local_storage_cache_candidates_added': 'pagespeed.num_local_storage_cache.candidates.added',
            'num_local_storage_cache_candidates_removed': 'pagespeed.num_local_storage_cache.candidates.removed',
            'converted_meta_tags': 'pagespeed.converted_meta_tags',
            'num_distributed_rewrite_successes': 'pagespeed.num_distributed_rewrite.successes',
            'num_distributed_rewrite_failures': 'pagespeed.num_distributed_rewrite.failures',
            'num_deadline_alarm_invocations': 'pagespeed.num_deadline_alarm_invocations',
            'url_trims': 'pagespeed.url_trims',
            'url_trim_saved_bytes': 'pagespeed.url_trim_saved_bytes',
            'resource_url_domain_rejections': 'pagespeed.resource_url_domain_rejections',
            'rewrite_cached_output_missed_deadline': 'pagespeed.rewrite_cached_output.missed_deadline',
            'rewrite_cached_output_hits': 'pagespeed.rewrite_cached_output.hits',
            'rewrite_cached_output_misses': 'pagespeed.rewrite_cached_output.misses',
            'resource_404_count': 'pagespeed.resource_404_count',
            'slurp_404_count': 'pagespeed.slurp_404_count',
            'total_page_load_ms': 'pagespeed.total_page_load_ms',
            'page_load_count': 'pagespeed.page_load_count',
            'resource_fetches_cached': 'pagespeed.resource_fetches_cached',
            'resource_fetch_construct_successes': 'pagespeed.resource_fetch_construct.successes',
            'resource_fetch_construct_failures': 'pagespeed.resource_fetch_construct.failures',
            'num_flushes': 'pagespeed.num_flushes',
            'num_fallback_responses_served': 'pagespeed.num_fallback_responses_served',
            'num_conditional_refreshes': 'pagespeed.num_conditional_refreshes',
            'ipro_served': 'pagespeed.ipro.served',
            'ipro_not_in_cache': 'pagespeed.ipro.not_in_cache',
            'ipro_not_rewritable': 'pagespeed.ipro.not_rewritable',
            'total_fetch_count': 'pagespeed.total_fetch_count',
            'total_rewrite_count': 'pagespeed.total_rewrite_count',
            'num_rewrites_executed': 'pagespeed.num_rewrites.executed',
            'num_rewrites_dropped': 'pagespeed.num_rewrites.dropped',
            'num_resource_fetch_successes': 'pagespeed.num_resource.fetch_successes',
            'num_resource_fetch_failures': 'pagespeed.num_resource.fetch_failures',
            'html-worker-queue-depth': 'pagespeed.html-worker-queue-depth',
            'rewrite-worker-queue-depth': 'pagespeed.rewrite-worker-queue-depth',
            'low-priority-worked-queue-depth': 'pagespeed.low-priority-worked-queue-depth',
            'cache_batcher_dropped_gets': 'pagespeed.cache_batcher_dropped_gets',
            'critical_images_valid_count': 'pagespeed.critical.images.valid_count',
            'critical_images_expired_count': 'pagespeed.critical.images.expired_count',
            'critical_images_not_found_count': 'pagespeed.critical.images.not_found_count',
            'critical_css_valid_count': 'pagespeed.critical.css.valid_count',
            'critical_css_expired_count': 'pagespeed.critical.css.expired_count',
            'critical_css_not_found_count': 'pagespeed.critical.css.not_found_count',
            'critical_selectors_valid_count': 'pagespeed.critical.selectors.valid_count',
            'critical_selectors_expired_count': 'pagespeed.critical.selectors.expired_count',
            'critical_selectors_not_found_count': 'pagespeed.critical.selectors.not_found_count',
            'pcache-cohorts-clientstate_deletes': 'pagespeed.pcache-cohorts.clientstate_deletes',
            'pcache-cohorts-clientstate_hits': 'pagespeed.pcache-cohorts.clientstate_hits',
            'pcache-cohorts-clientstate_inserts': 'pagespeed.pcache-cohorts.clientstate_inserts',
            'pcache-cohorts-clientstate_misses': 'pagespeed.pcache-cohorts.clientstate_misses',
            'cache_flush_count': 'pagespeed.cache.flush.count',
            'cache_flush_timestamp_ms': 'pagespeed.cache.flush.timestamp_ms',
            'memcache_timeouts': 'pagespeed.memcache.timeouts',
            'memcache_last_error_checkpoint_ms': 'pagespeed.memcache.last_error_checkpoint_ms',
            'memcache_error_burst_size': 'pagespeed.memcache.error_burst_size',
            'file_cache_disk_checks': 'pagespeed.file_cache.disk_checks',
            'file_cache_cleanups': 'pagespeed.file_cache.cleanups',
            'file_cache_evictions': 'pagespeed.file_cache.evictions',
            'file_cache_bytes_freed_in_cleanup': 'pagespeed.file_cache.bytes_freed_in_cleanup',
            'file_cache_deletes': 'pagespeed.file_cache.deletes',
            'file_cache_hits': 'pagespeed.file_cache.hits',
            'file_cache_inserts': 'pagespeed.file_cache.inserts',
            'file_cache_misses': 'pagespeed.file_cache.misses',
            'lru_cache_deletes': 'pagespeed.lru_cache.deletes',
            'lru_cache_hits': 'pagespeed.lru_cache.hits',
            'lru_cache_inserts': 'pagespeed.lru_cache.inserts',
            'lru_cache_misses': 'pagespeed.lru_cache.misses',
            'shm_cache_deletes': 'pagespeed.shm_cache.deletes',
            'shm_cache_hits': 'pagespeed.shm_cache.hits',
            'shm_cache_inserts': 'pagespeed.shm_cache.inserts',
            'shm_cache_misses': 'pagespeed.shm_cache.misses',
            'memcached_deletes': 'pagespeed.memcached.deletes',
            'memcached_hits': 'pagespeed.memcached.hits',
            'memcached_inserts': 'pagespeed.memcached.inserts',
            'memcached_misses': 'pagespeed.memcached.misses',
            'compressed_cache_corrupt_payloads': 'pagespeed.compressed_cache.corrupt_payloads',
            'compressed_cache_original_size': 'pagespeed.compressed_cache.original_size',
            'compressed_cache_compressed_size': 'pagespeed.compressed_cache.compressed_size',
            'serf_fetch_request_count': 'pagespeed.serf_fetch.request_count',
            'serf_fetch_bytes_count': 'pagespeed.serf_fetch.bytes_count',
            'serf_fetch_time_duration_ms': 'pagespeed.serf_fetch.time_duration_ms',
            'serf_fetch_cancel_count': 'pagespeed.serf_fetch.cancel_count',
            'serf_fetch_active_count': 'pagespeed.serf_fetch.active_count',
            'serf_fetch_timeout_count': 'pagespeed.serf_fetch.timeout_count',
            'serf_fetch_failure_count': 'pagespeed.serf_fetch.failure_count',
            'serf_fetch_cert_errors': 'pagespeed.serf_fetch.cert_errors',
            'pcache-cohorts-beacon_cohort_deletes': 'pagespeed.pcache-cohorts.beacon_cohort.deletes',
            'pcache-cohorts-beacon_cohort_hits': 'pagespeed.pcache-cohorts.beacon_cohort.hits',
            'pcache-cohorts-beacon_cohort_inserts': 'pagespeed.pcache-cohorts.beacon_cohort.inserts',
            'pcache-cohorts-beacon_cohort_misses': 'pagespeed.pcache-cohorts.beacon_cohort.misses',
            'pcache-cohorts-dom_deletes': 'pagespeed.pcache-cohorts.dom_deletes',
            'pcache-cohorts-dom_hits': 'pagespeed.pcache-cohorts.dom_hits',
            'pcache-cohorts-dom_inserts': 'pagespeed.pcache-cohorts.dom_inserts',
            'pcache-cohorts-dom_misses': 'pagespeed.pcache-cohorts.dom_misses',
            'child_shutdown_count': 'pagespeed.child_shutdown_count'
        }

        RATES = {
        
        }

        INCREMENTS = {
        
        }

        output = []
        # Loop through and extract the numerical values
        for line in response.split('\n'):
            values = line.split(': ')
            if len(values) == 2: # match
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Send metric as a gauge, if applicable
                if metric in GAUGES:
                    metric_name = GAUGES[metric]
                    output.append((metric_name, value, tags, 'gauge'))

                # Send metric as a rate, if applicable
                if metric in RATES:
                    metric_name = RATES[metric]
                    output.append((metric_name, value, tags, 'rate'))

                # Send metric as a increment, if applicable
                if metric in INCREMENTS:
                    metric_name = INCREMENTS[metric]
                    output.append((metric_name, value, tags, 'increment'))

        return output