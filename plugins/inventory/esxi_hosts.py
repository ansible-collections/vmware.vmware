# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: esxi_hosts
short_description: Create an inventory containing VMware ESXi hosts
author:
    - Mike Morency (@mikemorency)
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
    properties:
        default: ['name', 'customValue', 'summary.runtime.powerState']
    keyed_groups:
        default: [{key: 'summary.runtime.powerState', separator: ''}]
    gather_path:
        description:
            - If true, the vSphere folder path of each ESXi host is computed and stored in the C(path)
              host variable.
            - If false, the C(path) attribute is not evaluated, potentially saving execution time and bandwidth.
            - This is required if C(path) referenced elsewhere in the inventory configuration, or O(group_by_paths) is C(True)
        default: true
        type: bool
"""

EXAMPLES = r"""
# Below are examples of inventory configuration files that can be used with this plugin.
# To test these and see the resulting inventory, save the snippet in a file named esxi_hosts.yml and run:
# ansible-inventory -i esxi_hosts.yml --list


# Simple configuration with in-file authentication parameters
---
plugin: vmware.vmware.esxi_hosts
hostname: 10.65.223.31
username: administrator@vsphere.local
password: Esxi@123$%
validate_certs: false
...

# More complex configuration. Authentication parameters are assumed to be set as environment variables.
---
plugin: vmware.vmware.esxi_hosts

# Create groups based on host paths
group_by_paths: true

# Create a group with hosts that support vMotion using the vmotionSupported property
properties: ["name", "capability"]
groups:
  vmotion_supported: capability.vmotionSupported

# Filter out hosts using jinja patterns. For example, filter out powered off hosts
filter_expressions:
  - 'summary.runtime.powerState == "poweredOff"'

# Only gather hosts found in certain paths
search_paths:
  - /DC1/host/ClusterA
  - /DC1/host/ClusterC
  - /DC3

# Set custom inventory hostnames based on attributes
# If more than one host has the same name, only the first host is shown in the inventory and a warning is thrown.
# If strict is true, this warning is considered a fatal error.
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
...

# Use Tags and Tag Categories to create groups
# Given the example tags below:
#
#   tags:
#     urn:vmomi:InventoryServiceTag:70f87e82-6ac6-42bc-878c-817d7b2a4520:GLOBAL: db
#     urn:vmomi:InventoryServiceTag:bb10e90b-263f-4248-be06-086df1100d6b:GLOBAL: tofu-managed
#     urn:vmomi:InventoryServiceTag:70f87e82-6ac6-42bc-878c-111111111111:GLOBAL: web
#   tags_by_category:
#     app_type:
#       - urn:vmomi:InventoryServiceTag:70f87e82-6ac6-42bc-878c-817d7b2a4520:GLOBAL: db
#       - urn:vmomi:InventoryServiceTag:70f87e82-6ac6-42bc-878c-111111111111:GLOBAL: web
#     tofu:
#       - urn:vmomi:InventoryServiceTag:bb10e90b-263f-4248-be06-086df1100d6b:GLOBAL: tofu-managed
---
plugin: vmware.vmware.esxi_hosts
gather_tags: true
keyed_groups:
  # create groups based on tag names/values, like db, web, and tofu-managed
  - key: tags.values()
    prefix: ""
    separator: ""

  # create groups based on app types, like db and web
  - key: tags_by_category.app_type | map('dict2items') | flatten | map(attribute='value')
    prefix: "vmware_tag_app_type_category_"
    separator: ""

  # create groups based on categories, like app_type or tofu
  - key: tags_by_category.keys()
    prefix: "vmware_tag_category_name_"
    separator: ""
...
"""

try:
    from pyVmomi import vim, vmodl
except ImportError:
    # Already handled in base class
    pass

from ansible_collections.vmware.vmware.plugins.inventory_utils._base import (
    VmwareInventoryBase,
    VmwareInventoryHost
)


class EsxiInventoryHost(VmwareInventoryHost):
    def __init__(self):
        super().__init__()
        self._management_ip = None

    @classmethod
    def create_from_vcenter_object(cls, vmware_object, properties_to_gather, pyvmomi_client, prop_set=None, gather_path=True):
        host = super().create_from_vcenter_object(
            vmware_object,
            properties_to_gather,
            pyvmomi_client,
            prop_set=prop_set,
            gather_path=gather_path,
        )
        host.properties['management_ip'] = host.management_ip
        return host

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

    def get_tags(self, rest_client):
        return rest_client.get_tags_by_host_moid(self.object._GetMoId())


class InventoryModule(VmwareInventoryBase):

    NAME = "vmware.vmware.esxi_hosts"

    @property
    def vim_class(self):
        return vim.HostSystem

    @property
    def rest_class(self):
        return "HostSystem"

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

        # needed to filter out disconnected or unreachable hosts in self.populate_from_vcenter
        if "summary.runtime.connectionState" not in properties_param:
            properties_param.append("summary.runtime.connectionState")

        # needed by keyed_groups default
        if "summary.runtime.powerState" not in properties_param:
            properties_param.append("summary.runtime.powerState")

        return properties_param

    def populate_from_cache(self, cache_data):
        """
        Populate inventory data from cache
        """
        hostvars = {}
        for inventory_hostname, host_properties in cache_data.items():
            esxi_host = EsxiInventoryHost.create_from_cache(
                inventory_hostname=inventory_hostname,
                properties=host_properties
            )
            self.add_host_object_from_vcenter_to_inventory(esxi_host, hostvars)

    def _host_connection_state(self, esxi_host):
        try:
            return esxi_host.properties['summary']['runtime']['connectionState']
        except KeyError:
            return esxi_host.object.summary.runtime.connectionState

    def _hydrate_inventory_host_from_vsphere_props(self, vmware_object, prop_set, properties_to_gather):
        """
        Override for the base class definition of this method. Used to fully populate an inventory host's
        properties from vSphere.
        """
        try:
            esxi_host = EsxiInventoryHost.create_from_vcenter_object(
                vmware_object=vmware_object,
                properties_to_gather=properties_to_gather,
                pyvmomi_client=self.pyvmomi_client,
                prop_set=prop_set,
                gather_path=self.get_option("gather_path"),
            )
            if self._host_connection_state(esxi_host) in ("disconnected", "notResponding"):
                return None
        except vmodl.fault.ManagedObjectNotFound:
            self._handle_managed_object_not_found_error(vmware_object=vmware_object)
            return None

        return esxi_host

    def set_default_ansible_host_var(self, vmware_host_object):
        """
            Sets the default ansible_host var. This is usually an IP that is dependent on the object type.
            This is a default because the user can override this via compose
            Args:
              vmware_host_object: EsxiInventoryHost, The host object that should be used
        """
        self.inventory.set_variable(
            vmware_host_object.inventory_hostname, "ansible_host",
            vmware_host_object.management_ip
        )
