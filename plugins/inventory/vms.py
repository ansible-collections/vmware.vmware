# Copyright: (c) 2024, Ansible Cloud Team
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
name: vms
short_description: Create an inventory containing VMware VMs
author:
    - Ansible Cloud Team (@ansible-collections)
description:
    - Create a dynamic inventory of VMware VMs from a vCenter or ESXi environment.
    - Uses any file which ends with vms.yml, vms.yaml, vmware_vms.yml, or vmware_vms.yaml as a YAML configuration file.

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
        default: [
            'name', 'config.cpuHotAddEnabled', 'config.cpuHotRemoveEnabled',
            'config.instanceUuid', 'config.hardware.numCPU', 'config.template',
            'config.name', 'config.uuid', 'guest.hostName', 'guest.ipAddress',
            'guest.guestId', 'guest.guestState', 'runtime.maxMemoryUsage',
            'customValue', 'summary.runtime.powerState', 'config.guestId'
        ]
    keyed_groups:
        default: [
            {key: 'config.guestId', separator: ''},
            {key: 'summary.runtime.powerState', separator: ''},
        ]
"""

EXAMPLES = r"""
# Below are examples of inventory configuration files that can be used with this plugin.
# To test these and see the resulting inventory, save the snippet in a file named hosts.vmware_vms.yml and run:
# ansible-inventory -i hosts.vmware_vms.yml --list


# Simple configuration with in-file authentication parameters
---
plugin: vmware.vmware.vms
hostname: 10.65.223.31
username: administrator@vsphere.local
password: Esxi@123$%
validate_certs: false
...

# More complex configuration. Authentication parameters are assumed to be set as environment variables.
---
plugin: vmware.vmware.vms
# Create groups based on host paths
group_by_paths: true
# Create a group with VMs that support CPU hot add using the cpuHotAddEnabled property,
# and groups based on VMware tools
properties: ["name", "config", "guest"]
groups:
  cpu_hot_add_enabled: config.cpuHotAddEnabled
keyed_groups:
  - key: guest.toolsStatus
    separator: ""
  - key: guest.toolsRunningStatus
    separator: ""
# Only gather VMs found in certain paths
search_paths:
  - /DC1/vm/ClusterA
  - /DC1/vm/ClusterC
  - /DC3
# Filter out VMs using jinja patterns. For example, filter out powered off VMs
filter_expressions:
  - 'summary.runtime.powerState == "poweredOff"'
# Set custom inventory hostnames based on attributes
hostnames:
  - "'VM - ' + name + ' - ' + guest.ipAddress"
  - "'VM - ' + name + ' - ' + config.instanceUuid"
# Use compose to set variables for the hosts that we find
compose:
  ansible_user: "'root'"
  ansible_connection: "'ssh'"
  # assuming path is something like /MyDC/vms/MyCluster
  datacenter: "(path | split('/'))[1]"
  cluster: "(path | split('/'))[3]"
...

# Use Tags and Tag Categories to create groups
---
plugin: vmware.vmware.vms
gather_tags: true
keyed_groups:
  - key: tags_by_category.OS
    prefix: "vmware_tag_os_category_"
    separator: ""
...

# customizing hostnames based on VM's FQDN. The second hostnames template acts as a fallback mechanism.
---
plugin: vmware.vmware.vms
hostnames:
  - 'config.name+"."+guest.ipStack.0.dnsConfig.domainName'
  - 'config.name'
properties:
  - 'config.name'
  - 'config.guestId'
  - 'guest.hostName'
  - 'guest.ipAddress'
  - 'guest.guestFamily'
  - 'guest.ipStack'
...

# Select a specific IP address for use by ansible when multiple NICs are present on the VM
---
plugin: vmware.vmware.vms
compose:
  # Set the IP address used by ansible to one that starts by 10.42. or 10.43.
  ansible_host: >-
    guest.net
    | selectattr('ipAddress')
    | map(attribute='ipAddress')
    | flatten
    | select('match', '^10.42.*|^10.43.*')
    | list
    | first
properties:
  - guest.net
...

# Group hosts using Jinja2 conditionals
---
plugin: vmware.vmware.vms
properties:
  - 'config.datastoreUrl'
groups:
  slow_storage: "'Nas01' in config.datastoreUrl[0].name"
  fast_storage: "'SSD' in config.datastoreUrl[0].name"
...
"""

try:
    from pyVmomi import vim
except ImportError:
    # Already handled in base class
    pass

from ansible_collections.vmware.vmware.plugins.inventory_utils._base import (
    VmwareInventoryHost,
    VmwareInventoryBase
)


class VmInventoryHost(VmwareInventoryHost):
    def __init__(self):
        super().__init__()
        self._guest_ip = None

    @property
    def guest_ip(self):
        if self._guest_ip:
            return self._guest_ip

        try:
            self._guest_ip = self.properties['guest']['ipAddress']
        except KeyError:
            self._guest_ip = ""

        return self._guest_ip

    def get_tags(self, rest_client):
        return rest_client.get_tags_by_vm_moid(self.object._GetMoId())


class InventoryModule(VmwareInventoryBase):

    NAME = "vmware.vmware.vms"

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
                    "vms.yml",
                    "vms.yaml",
                    "vmware_vms.yaml",
                    "vmware_vms.yml"
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

        if "summary.runtime.powerState" not in properties_param:
            properties_param.append("summary.runtime.powerState")

        return properties_param

    def populate_from_cache(self, cache_data):
        """
        Populate inventory data from cache
        """
        for inventory_hostname, vm_properties in cache_data.items():
            vm = VmInventoryHost.create_from_cache(
                inventory_hostname=inventory_hostname,
                properties=vm_properties
            )
            self.__update_inventory(vm)

    def populate_from_vcenter(self, config_data):
        """
        Populate inventory data from vCenter
        """
        hostvars = {}
        properties_to_gather = self.parse_properties_param()
        self.initialize_pyvmomi_client(config_data)
        if self.get_option("gather_tags"):
            self.initialize_rest_client(config_data)

        for vm_object in self.get_objects_by_type(vim_type=[vim.VirtualMachine]):
            vm = VmInventoryHost.create_from_object(
                vmware_object=vm_object,
                properties_to_gather=properties_to_gather,
                pyvmomi_client=self.pyvmomi_client
            )

            if self.get_option("gather_tags"):
                self.add_tags_to_object_properties(vm)

            self.set_inventory_hostname(vm)
            if vm.inventory_hostname not in hostvars:
                hostvars[vm.inventory_hostname] = vm.properties
                self.__update_inventory(vm)

        return hostvars

    def __update_inventory(self, vm):
        if self.host_should_be_filtered_out(vm):
            return
        self.add_host_to_inventory(vm)
        self.add_host_to_groups_based_on_path(vm)
        self.set_host_variables_from_host_properties(vm)

    def add_host_to_inventory(self, vm: VmInventoryHost):
        """
        Add the host to the inventory and any groups that the user wants to create based on inventory
        parameters like groups or keyed groups.
        """
        strict = self.get_option("strict")
        self.inventory.add_host(vm.inventory_hostname)
        self.inventory.set_variable(vm.inventory_hostname, "ansible_host", vm.guest_ip)

        self._set_composite_vars(
            self.get_option("compose"), vm.properties, vm.inventory_hostname, strict=strict)
        self._add_host_to_composed_groups(
            self.get_option("groups"), vm.properties, vm.inventory_hostname, strict=strict)
        self._add_host_to_keyed_groups(
            self.get_option("keyed_groups"), vm.properties, vm.inventory_hostname, strict=strict)
