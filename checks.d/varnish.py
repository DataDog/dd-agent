# stdlib
import xml.parsers.expat # python 2.4 compatible
import re
import subprocess

# project
from checks import AgentCheck

class Varnish(AgentCheck):
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
                self.rate(m_name, long(self._current_value))
            elif self._current_type in ("i", "g"):
                self.gauge(m_name, long(self._current_value))
            else:
                # Unsupported data type, ignore
                self._reset()
                return # don't save

            # reset for next stat element
            self._reset()
        elif name in ("type", "ident", "name"):
            self._current_metric += "." + self._current_str

    def _char_data(self, data):
        self.log.debug("Data %s [%s]" % (data, self._current_element))
        data = data.strip()
        if len(data) > 0 and self._current_element != "":
            if self._current_element == "value":
                self._current_value = long(data)
            elif self._current_element == "flag":
                self._current_type = data
            else:
                self._current_str = data

    def check(self, instance):
        """Extract stats from varnishstat -x

        The text option (-1) is not reliable enough when counters get large.
        VBE.media_video_prd_services_01(10.93.67.16,,8080).happy18446744073709551615

        2 types of data, "a" for counter ("c" in newer versions of varnish), "i" for gauge ("g")
        https://github.com/varnish/Varnish-Cache/blob/master/include/tbl/vsc_fields.h

        Bitmaps are not supported.

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
        # Not configured? Not a problem.
        if instance.get("varnishstat", None) is None:
            raise Exception("varnishstat is not configured")
        tags = instance.get('tags', [])
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))
        name = instance.get('name')

        # Get the varnish version from varnishstat
        output, error = subprocess.Popen([instance.get("varnishstat"), "-V"],
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
            self.log.warn("Cannot determine the version of varnishstat, assuming 3 or greater")
            self.warning("Cannot determine the version of varnishstat, assuming 3 or greater")
        else:
            if m1 is not None:
                version = int(m1.group(1))
            elif m2 is not None:
                version = int(m2.group(1))

        self.log.debug("Varnish version: %d" % version)

        # Location of varnishstat
        if version <= 2:
            use_xml = False
            arg = "-1"

        cmd = [instance.get("varnishstat"), arg]
        if name is not None:
            cmd.extend(['-n', name])
            tags += [u'varnish_name:%s' % name]
        else:
            tags += [u'varnish_name:default']
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
            output, error = proc.communicate()
        except Exception:
            self.log.error(u"Failed to run %s" % repr(cmd))
            raise
        if error and len(error) > 0:
            self.log.error(error)
        self._parse_varnishstat(output, use_xml, tags)

    def _parse_varnishstat(self, output, use_xml, tags=None):
        tags = tags or []
        if use_xml:
            p = xml.parsers.expat.ParserCreate()
            p.StartElementHandler = self._start_element
            p.EndElementHandler = self._end_element
            p.CharacterDataHandler = self._char_data
            self._reset()
            p.Parse(output, True)
        else:
            for line in output.split("\n"):
                self.log.debug("Parsing varnish results: %s" % line)
                fields = line.split()
                if len(fields) < 3:
                    break
                name, gauge_val, rate_val = fields[0], fields[1], fields[2]
                metric_name = self.normalize(name, prefix="varnish")

                # Now figure out which value to pick
                if rate_val.lower() in ("nan", "."):
                    # col 2 matters
                    self.log.debug("Varnish (gauge) %s %d" % (metric_name, int(gauge_val)))
                    self.gauge(metric_name, int(gauge_val), tags=tags)
                else:
                    # col 3 has a rate (since restart)
                    self.log.debug("Varnish (rate) %s %d" % (metric_name, int(gauge_val)))
                    self.rate(metric_name, float(gauge_val), tags=tags)

   