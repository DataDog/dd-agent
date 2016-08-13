# stdlib
from collections import defaultdict

# 3p
from mock import Mock
from pyVmomi import vim  # pylint: disable=E0611
import simplejson as json

# datadog
from tests.checks.common import AgentCheckTest, Fixtures


class MockedMOR(Mock):
    """
    Helper, generate a mocked Managed Object Reference (MOR) from the given attributes.
    """
    def __init__(self, **kwargs):
        # Deserialize `spec`
        if 'spec' in kwargs:
            kwargs['spec'] = getattr(vim, kwargs['spec'])

        # Mocking
        super(MockedMOR, self).__init__(**kwargs)

        # Handle special attributes
        name = kwargs.get('name')
        is_labeled = kwargs.get('label', False)

        self.name = name
        self.customValue = []

        if is_labeled:
            self.customValue.append(Mock(value="DatadogMonitored"))


def create_topology(topology_json):
    """
    Helper, recursively generate a vCenter topology from a JSON description.
    Return a `MockedMOR` object.

    Examples:
      ```
      topology_desc = "
        {
          "childEntity": [
            {
              "hostFolder": {
                "childEntity": [
                  {
                    "spec": "ClusterComputeResource",
                    "name": "compute_resource1"
                  }
                ]
              },
              "spec": "Datacenter",
              "name": "datacenter1"
            }
          ],
          "spec": "Folder",
          "name": "rootFolder"
        }
      "

      topo = create_topology(topology_desc)

      assert isinstance(topo, Folder)
      assert isinstance(topo.childEntity[0].name) == "compute_resource1"
      ```
    """
    def rec_build(topology_desc):
        """
        Build MORs recursively.
        """
        parsed_topology = {}

        for field, value in topology_desc.iteritems():
            parsed_value = value
            if isinstance(value, dict):
                parsed_value = rec_build(value)
            elif isinstance(value, list):
                parsed_value = [rec_build(obj) for obj in value]
            else:
                parsed_value = value
            parsed_topology[field] = parsed_value

        return MockedMOR(**parsed_topology)

    return rec_build(json.loads(Fixtures.read_file(topology_json)))


class TestvSphereUnit(AgentCheckTest):
    """
    Unit tests for vSphere AgentCheck.
    """
    CHECK_NAME = "vsphere"

    def assertMOR(self, name=None, spec=None, tags=None, count=None):
        """
        Helper, assertion on vCenter Manage Object References.
        """
        candidates = []

        for mor in self._mor_list:
            if name is not None and name != mor['hostname']:
                continue

            if spec is not None and spec != mor['mor_type']:
                continue

            if tags is not None and set(tags) != set(mor['tags']):
                continue

            candidates.append(mor)

        # Assertions
        if count:
            self.assertEquals(len(candidates), count)
        else:
            self.assertTrue(len(candidates))

    def setUp(self):
        """
        Initialize and patch the check, i.e.
        * disable threading
        * create a unique container for MORs independent of the instance key
        """
        # Initialize
        config = {}
        self.load_check(config)

        # Disable threading
        self.check.pool = Mock(apply_async=lambda func, args: func(*args))

        # Create a container for MORs
        self._mor_list = []
        self.check.morlist_raw = defaultdict(lambda: self._mor_list)

    def test_exclude_host(self):
        """
        Exclude hosts/vms not compliant with the user's `*_include` configuration.
        """
        # Method to test
        is_excluded = self.check._is_excluded

        # Sample(s)
        include_regexes = {
            'host_include': "f[o]+",
            'vm_include': "f[o]+",
        }

        # OK
        included_host = MockedMOR(spec="HostSystem", name="foo")
        included_vm = MockedMOR(spec="VirtualMachine", name="foo")

        self.assertFalse(is_excluded(included_host, include_regexes, None))
        self.assertFalse(is_excluded(included_vm, include_regexes, None))

        # Not OK!
        excluded_host = MockedMOR(spec="HostSystem", name="bar")
        excluded_vm = MockedMOR(spec="VirtualMachine", name="bar")

        self.assertTrue(is_excluded(excluded_host, include_regexes, None))
        self.assertTrue(is_excluded(excluded_vm, include_regexes, None))

    def test_exclude_non_labeled_vm(self):
        """
        Exclude "non-labeled" virtual machines when the user configuration instructs to.
        """
        # Method to test
        is_excluded = self.check._is_excluded

        # Sample(s)
        include_regexes = None
        include_only_marked = True

        # OK
        included_vm = MockedMOR(spec="VirtualMachine", name="foo", label=True)
        self.assertFalse(is_excluded(included_vm, include_regexes, include_only_marked))

        # Not OK
        included_vm = MockedMOR(spec="VirtualMachine", name="foo")
        self.assertTrue(is_excluded(included_vm, include_regexes, include_only_marked))

    def test_mor_discovery(self):
        """
        Explore the vCenter infrastructure to discover hosts, virtual machines.

        Input topology:
            ```
            rootFolder
                - datacenter1
                  - compute_resource1
                      - host1                   # Filtered out
                      - host2
                - folder1
                    - datacenter2
                      - compute_resource2
                          - host3
                            - vm1               # Not labeled
                            - vm2               # Filtered out
                            - vm3               # Powered off
                            - vm4
            ```
        """
        # Method to test
        discover_mor = self.check._discover_mor

        # Samples
        vcenter_topology = create_topology('vsphere_topology.json')
        tags = [u"toto"]
        include_regexes = {
            'host_include': "host[2-9]",
            'vm_include': "vm[^2]",
        }
        include_only_marked = True

        # Discover hosts and virtual machines
        discover_mor(123, vcenter_topology, tags, include_regexes, include_only_marked)

        # Assertions
        self.assertMOR(count=3)

        # ... on hosts
        self.assertMOR(spec="host", count=2)
        self.assertMOR(
            name="host2", spec="host",
            tags=[
                u"toto", u"vsphere_datacenter:datacenter1",
                u"vsphere_cluster:compute_resource1", u"vsphere_type:host"
            ]
        )
        self.assertMOR(
            name="host3", spec="host",
            tags=[
                u"toto", u"folder1", u"vsphere_datacenter:datacenter2",
                u"vsphere_cluster:compute_resource2", u"vsphere_type:host"
            ]
        )

        # ...on VMs
        self.assertMOR(spec="vm", count=1)
        self.assertMOR(
            name="vm4", spec="vm",
            tags=[
                u"toto", u"folder1", u"vsphere_datacenter:datacenter2",
                u"vsphere_cluster:compute_resource2", u"vsphere_host:host3", u"vsphere_type:vm"
            ]
        )
