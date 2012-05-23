import xml.parsers.expat # python 2.4 compatible
import re
import subprocess

from checks import Check

class Varnish(Check):
    def __init__(self, logger):
        Check.__init__(self, logger)

    # XML parsing bits, a.k.a. Kafka in Code
    def _reset(self):
        self._current_element = ""
        self._current_metric = "varnish"
        self._current_value = 0
        self._current_str = ""
        self._current_type = ""

    def _start_element(self, name, attrs):
        self._current_element = name

    def _end_element(self, name):
        if name == "stat":
            m_name = self.normalize(self._current_metric)
            if self._current_type in ("a", "c"):
                if not self.is_metric(m_name):
                    self.counter(m_name)
            elif self._current_type in ("i", "g"):
                if not self.is_metric(m_name):
                    self.gauge(m_name)
            else:
                self.logger.warn("Unsupported stat type in %s; skipping" % self._current_type)
                self._reset()
                return # don't save
            
            # Type ok
            self.save_sample(m_name, long(self._current_value))
            # reset for next stat element
            self._reset()
            
        elif name in ("type", "ident", "name"):
            self._current_metric += "." + self._current_str
        

    def _char_data(self, data):
        self.logger.debug("Data %s [%s]" % (data, self._current_element))
        data = data.strip()
        if len(data) > 0 and self._current_element != "":
            if self._current_element == "value":
                self._current_value = long(data)
            elif self._current_element == "flag":
                self._current_type = data
            else:
                self._current_str = data

    def check(self, config):
        """Extract stats from varnishstat -x

        The text option (-1) is not reliable enough when counters get large
        VBE.media_video_prd_services_01(10.93.67.16,,8080).happy18446744073709551615

        2 types of data, "a" for counter ("c" in newer versions of varnish), "i" for gauge ("g")
        https://github.com/varnish/Varnish-Cache/blob/master/include/tbl/vsc_fields.h

        <varnishstat>
            <stat>
                <name>fetch_304</name>
                <value>0</value>
                <flag>a</flag>
                <description>Fetch no body (304)</description>
            </stat>
            <stat>
                <name>n_sess_mem</name>
                <value>334</value>
                <flag>i</flag>
                <description>N struct sess_mem</description>
            </stat>
            <stat>
                <type>LCK</type>
                <ident>vcl</ident>
                <name>creat</name>
                <value>1</value>
                <flag>a</flag>
                <description>Created locks</description>
            </stat>
        </varnishstat>
        """
        try:
            # Not configured? Not a problem.
            if config.get("varnishstat", None) is None:
                return False
            
            # Get the varnish version from varnishstat
            output, error = subprocess.Popen([config.get("varnishstat"), "-V"],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE).communicate()

            # Assumptions regarding varnish's version
            use_xml = True
            arg = "-x" # varnishstat argument
            version = 3

            m1 = re.search(r"varnish-(\d+)", output, re.MULTILINE)
            # v2 prints the version on stderr, v3 on stdout
            m2 = re.search(r"varnish-(\d+)", error, re.MULTILINE)

            if m1 is None and m2 is None:
                self.logger.warn("Cannot determine the version of varnishstat, assuming 3 or greater")
            else:
                if m1 is not None:
                    version = int(m1.group(1))
                elif m2 is not None:
                    version = int(m2.group(1))

            self.logger.debug("Varnish version: %d" % version)

            # Location of varnishstat
            if version <= 2:
                use_xml = False
                arg = "-1"

            output, error = subprocess.Popen([config.get("varnishstat"), arg],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE).communicate()
            if error and len(error) > 0:
                self.logger.error(error)
            self._parse_varnishstat(output, use_xml)
            
            return self.get_metrics()
        except:
            self.logger.exception("Cannot get varnish stats")
            return False

    def _parse_varnishstat(self, output, use_xml):
        if use_xml:
            p = xml.parsers.expat.ParserCreate()
            p.StartElementHandler = self._start_element
            p.EndElementHandler = self._end_element
            p.CharacterDataHandler = self._char_data
            self._reset()
            
            p.Parse(output, True)
        else:
            for line in output.split("\n"):
                self.logger.debug("Parsing varnish results: %s" % line)
                fields = line.split()
                if len(fields) < 3:
                    break
                name, gauge_val, rate_val = fields[0], fields[1], fields[2]
                metric_name = self.normalize(name, prefix="varnish")

                
                # Now figure out which value to pick
                try:
                    if rate_val.lower() in ("nan", "."):
                        # First time we see the metric?
                        if not self.is_metric(metric_name):
                            self.gauge(metric_name)
                        # col 2 matters
                        self.logger.debug("Varnish (gauge) %s %d" % (metric_name, int(gauge_val)))
                        self.save_sample(metric_name, int(gauge_val))
                    else:
                        # First time we see the metric?
                        if not self.is_metric(metric_name):
                            self.counter(metric_name)
                        # col 3 has a rate (since restart)
                        self.logger.debug("Varnish (rate) %s %d" % (metric_name, int(gauge_val)))
                        self.save_sample(metric_name, float(gauge_val))
                except TypeError:
                    self.logger.exception("Cannot convert varnish value")
