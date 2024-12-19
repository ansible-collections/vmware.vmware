# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: esxi_hosts
short_description: Create an inventory containing VMware ESXi hosts
author:
    - Ansible Cloud Team (@ansible-collections)
description:
    - Create a dynamic inventory of VMware ESXi hosts from a vCenter environment.
    - Uses any file which ends with esxi_hosts.yml, esxi_hosts.yaml, vmware_esxi_hosts.yml, or vmware_esxi_hosts.yaml as a YAML configuration file.

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
    - vmware.vmware.plugin_base_options
    - ansible.builtin.inventory_cache
    - ansible.builtin.constructed

requirements:
    - vSphere Automation SDK (when gather_tags is True)

options:
    gather_tags:
        description:
            - If true, gather any tags attached to the associated ESXi hosts
            - Requires 'vSphere Automation SDK' library to be installed on the Ansible controller machine.
        default: false
        type: bool
    hostnames:
        description:
            - A list of templates evaluated in order to compose inventory_hostname.
            - Each value in the list should be a jinja template. You can see the examples section for more details.
            - Templates that result in an empty string or None value are ignored and the next template is evaluated.
            - You can use hostvars such as properties specified in O(properties) as variables in the template.
        type: list
        elements: string
        default: ['name']
    properties:
        description:
            - Specify a list of VMware schema properties associated with the ESXi hostsystem to collect and return as hostvars.
            - Each value in the list can be a path to a specific property in hostsystem object or a path to a collection of hostsystem objects.
            - Please make sure that if you use a property in another parameter that it is included in this option.
            - Some properties are always returned, such as name, customValue, and summary.runtime.powerState
            - Use V(all) to return all properties available for the ESXi host.
        type: list
        elements: string
        default: ['name', 'customValue', 'summary.runtime.powerState']
    flatten_nested_properties:
        description:
            - If true, flatten any nested properties into their dot notation names.
            - For example 'summary["runtime"]["powerState"]' would become "summary.runtime.powerState"
        type: bool
        default: false
    keyed_groups:
        description:
            - Use the values of ESXi host properties or other hostvars to create and populate groups.
        type: list
        default: [{key: 'summary.runtime.powerState', separator: ''}]
    search_paths:
        description:
            - Specify a list of paths that should be searched recursively for hosts.
            - This effectively allows you to only include hosts in certain datacenters, clusters, or folders.
            - >-
                Filtering is done before the initial host gathering query. If you have a large number of hosts, specifying
                a subset of paths to search can help speed up the inventory plugin.
            - The default value is an empty list, which means all paths (i.e. all datacenters) will be searched.
        type: list
        elements: str
        default: []
    group_by_paths:
        description:
            - If true, groups will be created based on the ESXI hosts' paths.
            - >-
              Paths will be sanitized to match Ansible group name standards.
              For example, any slashes or dashes in the paths will be replaced by underscores in the group names.
            - A group is created for each step down in the path, with the group from the step above containing subsequent groups.
            - For example, a path /DC-01/hosts/Cluster will create groups 'DC_01' which contains group 'DC_01_hosts' which contains group 'DC_01_hosts_Cluster'
        default: false
        type: bool
    group_by_paths_prefix:
        description:
            - If O(group_by_paths) is true, set this variable if you want to add a prefix to any groups created based on paths.
            - By default, no prefix is added to the group names.
        default: ''
        type: str
    sanitize_property_names:
        description:
            - If true, sanitize ESXi host property names so they can safely be referenced within Ansible playbooks.
            - This option also transforms property names to snake case. For example, powerState would become power_state.
        type: bool
        default: false
"""

EXAMPLES = r"""
# Below are examples of inventory configuration files that can be used with this plugin.
# To test these and see the resulting inventory, save the snippet in a file named hosts.vmware_esxi.yml and run:
# ansible-inventory -i hosts.vmware_esxi.yml --list


# Simple configuration with in-file authentication parameters
plugin: vmware.vmware.esxi_hosts
hostname: 10.65.223.31
username: administrator@vsphere.local
password: Esxi@123$%
validate_certs: false


# More complex configuration. Authentication parameters are assumed to be set as environment variables.
plugin: vmware.vmware.esxi_hosts

# Create groups based on host paths
group_by_paths: true

# Create a group with hosts that support vMotion using the vmotionSupported property
properties: ["name", "capability"]
groups:
  vmotion_supported: capability.vmotionSupported

# Only gather hosts found in certain paths
search_paths:
  - /DC1/host/ClusterA
  - /DC1/host/ClusterC
  - /DC3

# Set custom inventory hostnames based on attributes
hostnames:
  - "'ESXi - ' + name + ' - ' + management_ip"
  - "'ESXi - ' + name"

# Use compose to set variables for the hosts that we find
compose:
  ansible_user: "'root'"
  ansible_connection: "'ssh'"
  # assuming path is something like /MyDC/host/MyCluster
  datacenter: "(path | split('/'))[1]"
  cluster: "(path | split('/'))[3]"
"""

try:
    from pyVmomi import vim
except ImportError:
    # Already handled in base class
    pass

from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.vmware.vmware.plugins.inventory_utils._base import VmwareInventoryBase
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import (
    get_folder_path_of_vsphere_object
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_facts import (
    vmware_obj_to_json,
    flatten_dict
)


class EsxiInventoryHost():
    def __init__(self):
        self.object = None
        self.inventory_hostname = None
        self.path = ''
        self.properties = dict()
        self._management_ip = None

    @classmethod
    def create_from_cache(cls, inventory_hostname, host_properties):
        """
        Create the class from the inventory cache. We don't want to refresh the data or make any calls to vCenter.
        Properties are populated from whatever we had previously cached.
        """
        host = cls()
        host.inventory_hostname = inventory_hostname
        host.properties = host_properties
        return host

    @classmethod
    def create_from_object(cls, host_object, properties_to_gather, pyvmomi_client):
        """
        Create the class from a host object that we got from pyvmomi. The host properties will be populated
        from the object and additional calls to vCenter
        """
        host = cls()
        host.object = host_object
        host.path = get_folder_path_of_vsphere_object(host_object)
        host.properties = host._set_properties_from_pyvmomi(properties_to_gather, pyvmomi_client)
        return host

    def _set_properties_from_pyvmomi(self, properties_to_gather, pyvmomi_client):
        properties = vmware_obj_to_json(self.object, properties_to_gather)
        properties['path'] = self.path
        properties['management_ip'] = self.management_ip

        # Custom values
        if hasattr(self.object, "customValue"):
            properties['customValue'] = dict()
            field_mgr = pyvmomi_client.custom_field_mgr
            for cust_value in self.object.customValue:
                properties['customValue'][
                    [y.name for y in field_mgr if y.key == cust_value.key][0]
                ] = cust_value.value

        return properties

    def sanitize_properties(self):
        self.properties = camel_dict_to_snake_dict(self.properties)

    def flatten_properties(self):
        self.properties = flatten_dict(self.properties)

    @property
    def management_ip(self):
        # We already looked up the management IP from vcenter this session, so
        # reuse that value
        if self._management_ip is not None:
            return self._management_ip

        # If this is an object created from the cache, we won't be able to access
        # vcenter. But we stored the management IP in the properties when we originally
        # created the object (before the cache) so use that value
        try:
            return self.properties['management_ip']
        except KeyError:
            pass

        # Finally, try to find the IP from vcenter. It might not exist, in which case we
        # return an empty string
        try:
            vnic_manager = self.object.configManager.virtualNicManager
            net_config = vnic_manager.QueryNetConfig("management")
            for nic in net_config.candidateVnic:
                if nic.key in net_config.selectedVnic:
                    self._management_ip = nic.spec.ip.ipAddress
        except Exception:
            self._management_ip = ""

        return self._management_ip


class InventoryModule(VmwareInventoryBase):

    NAME = "vmware.vmware.esxi_hosts"

    def verify_file(self, path):
        """
        Checks the plugin configuration file format and name, and returns True
        if everything is valid.
        Args:
            path: Path to the configuration YAML file
        Returns:
            True if everything is correct, else False
        """
        if super(InventoryModule, self).verify_file(path):
            return path.endswith(
                (
                    "esxi_hosts.yml",
                    "esxi_hosts.yaml",
                    "vmware_esxi_hosts.yaml",
                    "vmware_esxi_hosts.yml"
                )
            )
        return False

    def parse(self, inventory, loader, path, cache=True):
        """
        Parses the inventory file options and creates an inventory based on those inputs
        """
        super(InventoryModule, self).parse(inventory, loader, path, cache=cache)
        cache_key = self.get_cache_key(path)
        result_was_cached, results = self.get_cached_result(cache, cache_key)

        if result_was_cached:
            self.populate_from_cache(results)
        else:
            results = self.populate_from_vcenter(self._read_config_data(path))

        self.update_cached_result(cache, cache_key, results)

    def parse_properties_param(self):
        """
        The properties option can be a variety of inputs from the user and we need to
        manipulate it into a list of properties that can be used later.
        Returns:
          A list of property names that should be returned in the inventory. An empty
          list means all properties should be collected
        """
        properties_param = self.get_option("properties")
        if not isinstance(properties_param, list):
            properties_param = [properties_param]

        if "all" in properties_param:
            return []

        if "name" not in properties_param:
            properties_param.append("name")

        if "summary.runtime.connectionState" not in properties_param:
            properties_param.append("summary.runtime.connectionState")

        return properties_param

    def populate_from_cache(self, cache_data):
        """
        Populate inventory data from cache
        """
        for inventory_hostname, host_properties in cache_data.items():
            esxi_host = EsxiInventoryHost.create_from_cache(
                inventory_hostname=inventory_hostname,
                host_properties=host_properties
            )
            self.__update_inventory(esxi_host)

    def populate_from_vcenter(self, config_data):
        """
        Populate inventory data from vCenter
        """
        hostvars = {}
        properties_to_gather = self.parse_properties_param()
        self.initialize_pyvmomi_client(config_data)
        if self.get_option("gather_tags"):
            self.initialize_rest_client(config_data)

        for host_object in self.get_objects_by_type(vim_type=[vim.HostSystem]):
            if host_object.runtime.connectionState in ("disconnected", "notResponding"):
                continue

            esxi_host = EsxiInventoryHost.create_from_object(
                host_object=host_object,
                properties_to_gather=properties_to_gather,
                pyvmomi_client=self.pyvmomi_client
            )

            if self.get_option("gather_tags"):
                tags, tags_by_category = self.gather_tags(esxi_host.object._GetMoId())
                esxi_host.properties["tags"] = tags
                esxi_host.properties["tags_by_category"] = tags_by_category

            self.set_inventory_hostname(esxi_host)
            if esxi_host.inventory_hostname not in hostvars:
                hostvars[esxi_host.inventory_hostname] = esxi_host.properties
                self.__update_inventory(esxi_host)

        return hostvars

    def __update_inventory(self, esxi_host):
        self.add_host_to_inventory(esxi_host)
        self.add_host_to_groups_based_on_path(esxi_host)
        self.set_host_variables_from_host_properties(esxi_host)

    def set_inventory_hostname(self, esxi_host):
        """
        The user can specify a list of jinja templates, and the first valid template should be used for the
        host's inventory hostname. The inventory hostname is mostly for decorative purposes since the
        ansible_host value takes precedence when trying to connect.
        """
        hostname = None
        errors = []

        for hostname_pattern in self.get_option("hostnames"):
            try:
                hostname = self._compose(template=hostname_pattern, variables=esxi_host.properties)
            except Exception as e:
                if self.get_option("strict"):
                    raise AnsibleError(
                        "Could not compose %s as hostnames - %s"
                        % (hostname_pattern, to_native(e))
                    )

                errors.append((hostname_pattern, str(e)))
            if hostname:
                esxi_host.inventory_hostname = hostname
                return

        raise AnsibleError(
            "Could not template any hostname for host, errors for each preference: %s"
            % (", ".join(["%s: %s" % (pref, err) for pref, err in errors]))
        )

    def add_host_to_inventory(self, esxi_host: EsxiInventoryHost):
        """
        Add the host to the inventory and any groups that the user wants to create based on inventory
        parameters like groups or keyed groups.
        """
        strict = self.get_option("strict")
        self.inventory.add_host(esxi_host.inventory_hostname)
        self.inventory.set_variable(esxi_host.inventory_hostname, "ansible_host", esxi_host.management_ip)

        self._set_composite_vars(
            self.get_option("compose"), esxi_host.properties, esxi_host.inventory_hostname, strict=strict)
        self._add_host_to_composed_groups(
            self.get_option("groups"), esxi_host.properties, esxi_host.inventory_hostname, strict=strict)
        self._add_host_to_keyed_groups(
            self.get_option("keyed_groups"), esxi_host.properties, esxi_host.inventory_hostname, strict=strict)

    def add_host_to_groups_based_on_path(self, esxi_host: EsxiInventoryHost):
        """
        If the user desires, create groups based on each ESXi host's path. A group is created for each
        step down in the path, with the group from the step above containing subsequent groups.
        Optionally, the user can add a prefix to the groups created by this process.
        The final group in the path will be where the ESXi host is added.
        """
        if not self.get_option("group_by_paths"):
            return

        path_parts = esxi_host.path.split('/')
        group_name_parts = []
        last_created_group = None

        if self.get_option("group_by_paths_prefix"):
            group_name_parts = [self.get_option("group_by_paths_prefix")]

        for path_part in path_parts:
            if not path_part:
                continue
            group_name_parts.append(path_part)
            group_name = self._sanitize_group_name('_'.join(group_name_parts))
            group = self.inventory.add_group(group_name)

            if last_created_group:
                self.inventory.add_child(last_created_group, group)
            last_created_group = group

        if last_created_group:
            self.inventory.add_host(esxi_host.inventory_hostname, last_created_group)

    def set_host_variables_from_host_properties(self, esxi_host):
        if self.get_option("sanitize_property_names"):
            esxi_host.sanitize_properties()

        if self.get_option("flatten_nested_properties"):
            esxi_host.flatten_properties()

        for k, v in esxi_host.properties.items():
            self.inventory.set_variable(esxi_host.inventory_hostname, k, v)
