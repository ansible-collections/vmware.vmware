#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: host
short_description: Manage VMware ESXi host status in vCenter
description:
    - Manage VMware ESXi host status in vCenter, including host location and connection status.

author:
    - Ansible Cloud Team (@ansible-collections)

options:
    cluster:
        description:
            - The name of the cluster to be managed.
        type: str
        required: true
        aliases: [cluster_name]
    datacenter:
        description:
            - The name of the datacenter.
        type: str
        required: true
        aliases: [datacenter_name]
    folder:
        description:
            - Name of the folder under which host to add.
            - If O(cluster_name) is not set, then this parameter is required.
        type: str
  add_connected:
        description:
            - If set to V(true), then the host should be connected as soon as it is added.
            - This parameter is ignored if not O(state=present).
        default: true
        type: bool
  esxi_hostname:
        description:
            - ESXi hostname to manage.
        required: true
        type: str
  esxi_username:
        description:
            - ESXi username.
            - Required for adding a host.
            - Optional for reconnect. If both O(esxi_username) and O(esxi_password) are used
            - Unused for removing.
            - No longer a required parameter from version 2.5.
        type: str
  esxi_password:
        description:
            - ESXi password.
            - Required for adding a host.
            - Optional for reconnect.
            - Unused for removing.
            - No longer a required parameter from version 2.5.
        type: str
  state:
        description:
            - If set to V(present), add the host if host is absent.
            - If set to V(present), update the location of the host if host already exists.
            - If set to V(absent), remove the host if host is present.
            - If set to V(absent), do nothing if host already does not exists.
            - If set to V(add_or_reconnect), add the host if it's absent else reconnect it and update the location.
            - If set to V(reconnect), then reconnect the host if it's present and update the location.
            - If set to V(disconnected), disconnect the host if the host already exists.
        default: present
        choices: ['present', 'absent', 'add_or_reconnect', 'reconnect', 'disconnected']
        type: str
  esxi_ssl_thumbprint:
        description:
            - "Specifying the hostsystem certificate's thumbprint."
            - "Use following command to get hostsystem certificate's thumbprint - "
            - "# openssl x509 -in /etc/vmware/ssl/rui.crt -fingerprint -sha1 -noout"
        default: ''
        type: str
        aliases: ['ssl_thumbprint']
  fetch_ssl_thumbprint:
        description:
            - Fetch the thumbprint of the host's SSL certificate.
            - This basically disables the host certificate verification (check if it was signed by a recognized CA).
            - Disable this option if you want to allow only hosts with valid certificates to be added to vCenter.
            - If this option is set to V(false) and the certificate can't be verified, an add or reconnect will fail.
            - Unused when O(esxi_ssl_thumbprint) is set.
            - Optional for reconnect, but only used if O(esxi_username) and O(esxi_password) are used.
            - Unused for removing.
        type: bool
        default: true
  force_connection:
        description:
            - Force the connection if the host is already being managed by another vCenter server.
        type: bool
        default: true
  reconnect_disconnected:
        description:
            - Reconnect disconnected hosts.
            - This is only used if O(state=present) and if the host already exists.
        type: bool
        default: true

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Create Cluster
  vmware.vmware.cluster:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: datacenter
    cluster_name: cluster

- name: Delete Cluster
  vmware.vmware.cluster:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: datacenter
    name: cluster
    state: absent
'''

RETURN = r'''
cluster:
    description:
        - Identifying information about the cluster
        - If the cluster was removed, only the name is returned
    returned: On success
    type: dict
    sample: {
        "cluster": {
            "moid": "domain-c111111",
            "name": "example-cluster"
        },
    }
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import (
    TaskError,
    RunningTaskMonitor
)


class VmwareHost(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params.get('datacenter'), fail_on_missing=True)
        self.cluster = self.get_cluster_by_name_or_moid(self.params.get('cluster'), fail_on_missing=True, datacenter=self.datacenter)

    def get_host(self):
        host = self.get_esxi_host_by_name_or_moid(identifier=self.params['esxi_hostname'])
        if not host:
            return None

        if self.params['state'] == 'present' and host.parent != self.cluster:
            self.module.fail_json(msg=(
                'Host is already joined to another cluster %s' % host.parent.name
            ))

        return host

    def state_add_host(self):
        """Add ESXi host to a cluster of folder in vCenter"""
        changed = True
        result = None

        if self.module.check_mode:
            result = "Host would be connected to vCenter '%s'" % self.vcenter
        else:
            host_connect_spec = self.get_host_connect_spec()
            as_connected = self.params.get('add_connected')
            esxi_license = None
            resource_pool = None
            task = None
            if self.folder_name:
                self.folder = self.search_folder(self.folder_name)
                task = self.folder.AddStandaloneHost(
                    spec=host_connect_spec, compResSpec=resource_pool,
                    addConnected=as_connected, license=esxi_license
                )
            elif self.cluster_name:
                self.host, self.cluster = self.search_cluster(
                    self.datacenter_name,
                    self.cluster_name,
                    self.esxi_hostname
                )
                task = self.cluster.AddHost_Task(
                    spec=host_connect_spec, asConnected=as_connected,
                    resourcePool=resource_pool, license=esxi_license
                )

            try:
                changed, result = wait_for_task(task)
                result = "Host connected to vCenter '%s'" % self.vcenter
            except TaskError as task_error:
                self.module.fail_json(
                    msg="Failed to add host to vCenter '%s' : %s" % (self.vcenter, to_native(task_error))
                )

        self.module.exit_json(changed=changed, result=result)

    def reconnect_host(self, host_object):
        reconnecthost_args = {}
        reconnecthost_args['reconnectSpec'] = vim.HostSystem.ReconnectSpec()
        reconnecthost_args['reconnectSpec'].syncState = True

        if self.esxi_username and self.esxi_password:
            # Build the connection spec as well and fetch thumbprint if enabled
            # Useful if you reinstalled a host and it uses a new self-signed certificate
            reconnecthost_args['cnxSpec'] = self.get_host_connect_spec()
        try:
            task = host_object.ReconnectHost_Task(**reconnecthost_args)
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to exit maintenance mode on %s due to exception %s" %
                (self.params['esxi_host_name'], to_native(generic_exc))
            ))

        return task_result

    def remove_host(self):
        if not self.host:
            return

        if not self.host.runtime.inMaintenanceMode:
            self.module.fail_json('Host is not in maintenance mode. It must be in maintenance mode before it can be removed.')

        if self.folder_name:
            task = self.host_parent_compute_resource.Destroy_Task()
        elif self.cluster_name:
            task = self.host.Destroy_Task()

        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to exit maintenance mode on %s due to exception %s" %
                (self.params['esxi_host_name'], to_native(generic_exc))
            ))

        return task_result

   def state_update_host(self):
        """Move host to a cluster or a folder, or vice versa"""
        changed = True
        result = None
        reconnect = False

        # Check if the host is disconnected if reconnect disconnected hosts is true
        if self.reconnect_disconnected and self.host_update.runtime.connectionState == 'disconnected':
            reconnect = True

        # Check parent type
        parent_type = self.get_parent_type(self.host_update)

        if self.folder_name:
            if self.module.check_mode:
                if reconnect or self.state == 'add_or_reconnect' or self.state == 'reconnect':
                    result = "Host would be reconnected and moved to folder '%s'" % self.folder_name
                else:
                    result = "Host would be moved to folder '%s'" % self.folder_name
            else:
                # Reconnect the host if disconnected or if specified by state
                if reconnect or self.state == 'add_or_reconnect' or self.state == 'reconnect':
                    self.reconnect_host(self.host_update)
                try:
                    task = None
                    try:
                        if parent_type == 'folder':
                            # Move ESXi host from folder to folder
                            task = self.folder.MoveIntoFolder_Task([self.host_update.parent])
                        elif parent_type == 'cluster':
                            self.put_host_in_maintenance_mode(self.host_update)
                            # Move ESXi host from cluster to folder
                            task = self.folder.MoveIntoFolder_Task([self.host_update])
                    except vim.fault.DuplicateName as duplicate_name:
                        self.module.fail_json(
                            msg="The folder already contains an object with the specified name : %s" %
                            to_native(duplicate_name)
                        )
                    except vim.fault.InvalidFolder as invalid_folder:
                        self.module.fail_json(
                            msg="The parent of this folder is in the list of objects : %s" %
                            to_native(invalid_folder)
                        )
                    except vim.fault.InvalidState as invalid_state:
                        self.module.fail_json(
                            msg="Failed to move host, this can be due to either of following :"
                            " 1. The host is not part of the same datacenter, 2. The host is not in maintenance mode : %s" %
                            to_native(invalid_state)
                        )
                    except vmodl.fault.NotSupported as not_supported:
                        self.module.fail_json(
                            msg="The target folder is not a host folder : %s" %
                            to_native(not_supported)
                        )
                    except vim.fault.DisallowedOperationOnFailoverHost as failover_host:
                        self.module.fail_json(
                            msg="The host is configured as a failover host : %s" %
                            to_native(failover_host)
                        )
                    except vim.fault.VmAlreadyExistsInDatacenter as already_exists:
                        self.module.fail_json(
                            msg="The host's virtual machines are already registered to a host in "
                            "the destination datacenter : %s" % to_native(already_exists)
                        )
                    changed, result = wait_for_task(task)
                except TaskError as task_error_exception:
                    task_error = task_error_exception.args[0]
                    self.module.fail_json(
                        msg="Failed to move host %s to folder %s due to %s" %
                        (self.esxi_hostname, self.folder_name, to_native(task_error))
                    )
                if reconnect or self.state == 'add_or_reconnect' or self.state == 'reconnect':
                    result = "Host reconnected and moved to folder '%s'" % self.folder_name
                else:
                    result = "Host moved to folder '%s'" % self.folder_name
        elif self.cluster_name:
            if self.module.check_mode:
                result = "Host would be moved to cluster '%s'" % self.cluster_name
            else:
                if parent_type == 'cluster':
                    # Put host in maintenance mode if moved from another cluster
                    self.put_host_in_maintenance_mode(self.host_update)
                resource_pool = None
                try:
                    try:
                        task = self.cluster.MoveHostInto_Task(
                            host=self.host_update, resourcePool=resource_pool
                        )
                    except vim.fault.TooManyHosts as too_many_hosts:
                        self.module.fail_json(
                            msg="No additional hosts can be added to the cluster : %s" % to_native(too_many_hosts)
                        )
                    except vim.fault.InvalidState as invalid_state:
                        self.module.fail_json(
                            msg="The host is already part of a cluster and is not in maintenance mode : %s" %
                            to_native(invalid_state)
                        )
                    except vmodl.fault.InvalidArgument as invalid_argument:
                        self.module.fail_json(
                            msg="Failed to move host, this can be due to either of following :"
                            " 1. The host is is not a part of the same datacenter as the cluster,"
                            " 2. The source and destination clusters are the same : %s" %
                            to_native(invalid_argument)
                        )
                    changed, result = wait_for_task(task)
                except TaskError as task_error_exception:
                    task_error = task_error_exception.args[0]
                    self.module.fail_json(
                        msg="Failed to move host to cluster '%s' due to : %s" %
                        (self.cluster_name, to_native(task_error))
                    )
                if reconnect or self.state == 'add_or_reconnect' or self.state == 'reconnect':
                    result = "Host reconnected and moved to cluster '%s'" % self.cluster_name
                else:
                    result = "Host moved to cluster '%s'" % self.cluster_name

        self.module.exit_json(changed=changed, msg=str(result))


    def disconnect_host(self, host_object):
        if not self.host:
            self.module.fail_json(msg="Host is not currently present in vCenter")

        if self.host.runtime.connectionState == 'disconnected':
            return

        try:
            task = host_object.DisconnectHost_Task()
        except Exception as e:
            self.module.fail_json(msg="Failed to disconnect host from vCenter: %s" % to_native(e))
        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to exit maintenance mode on %s due to exception %s" %
                (self.params['esxi_host_name'], to_native(generic_exc))
            ))
        return task_result

def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                cluster=dict(type='str', required=True, aliases=['cluster_name', 'name']),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                state=dict(type='str', default='present', choices=['absent', 'present']),
            )
        },
        supports_check_mode=True,
    )

    vmware_cluster = VMwareCluster(module)
    if vmware_cluster.actual_state_matches_desired_state():
        module.exit_json(changed=False, cluster=vmware_cluster.get_cluster_outputs())

    if module.check_mode:
        module.exit_json(changed=True, cluster=vmware_cluster.get_cluster_outputs())

    vmware_cluster.update_state()
    module.exit_json(changed=True, cluster=vmware_cluster.get_cluster_outputs())


if __name__ == '__main__':
    main()
