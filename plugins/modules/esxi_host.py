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
    - The host must be in maintenance mode to remove it or update its placement.

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
    esxi_host_name:
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
    esxi_port:
        description:
            - The port on which the ESXi host's SSL certificate can be seen.
            - This is used when fetching the SSL thumbrpint, and is not used if
                O(ssl_thumbprint) is provided.
        type: str
        default: 443
    state:
        description:
            - If set to V(present), add the host if host is absent.
            - If set to V(present), update the location of the host if host already exists.
            - If set to V(absent), remove the host if host is present.
            - If set to V(absent), do nothing if host already does not exists.
        default: present
        choices: ['present', 'absent']
        type: str
    ssl_thumbprint:
        description:
            - Specify the host system's SSL certificate thumbprint.
            - You can run the following command on the host to get the thumbprint -
              'openssl x509 -in /etc/vmware/ssl/rui.crt -fingerprint -sha1 -noout'
            - If this is not set, the module will attempt to fetch the thumbprint from the host itself.
              This essentially skips the host certificate verification, since whatever host is presented will be trusted.
            - This option is only used when state is present.
            - If O(proxy_host) is set, the proxy is used when fetching the SSL thumbprint.
        type: str
    force_add:
        description:
            - Forces the ESXi host to be added to the vCenter server, even if it already being managed by another server.
            - The host must be in maintenance mode even if this option is enabled.
        type: bool
        default: False

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Make Sure Host Is In A Cluster
  vmware.vmware.esxi_host:
    datacenter: DC01
    cluster: MyCluster
    esxi_host_name: 1.1.1.1
    esxi_username: root
    esxi_password: mypassword!
    state: present


- name: Make Sure Host Is In A Folder (Standalone Host)
  vmware.vmware.esxi_host:
    datacenter: DC01
    folder: my/host/folder   # or DC01/host/my/host/folder
    esxi_host_name: 1.1.1.1
    esxi_username: root
    esxi_password: mypassword!
    state: present


- name: Remove Host From Cluster
  vmware.vmware.esxi_host:
    datacenter: DC01
    esxi_host_name: 1.1.1.1
    state: absent
'''

RETURN = r'''
host:
    description:
        - Identifying information about the host
        - If the state is absent and the host does not exist, only the name is returned
    returned: On success
    type: dict
    sample: {
        "host": {
            "moid": "host-111111",
            "name": "10.10.10.10"
        },
    }
'''

import ssl
import socket
import hashlib

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
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import (
    format_folder_path_as_host_fq_path
)


class VmwareHost(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.datacenter = self.get_datacenter_by_name_or_moid(self.params.get('datacenter'), fail_on_missing=True)
        self.cluster = None
        self.folder = None
        if self.params['cluster']:
            self.cluster = self.get_cluster_by_name_or_moid(self.params.get('cluster'), fail_on_missing=True, datacenter=self.datacenter)
        elif self.params['folder']:
            if self.params['folder'].startswith(self.params['datacenter']) or self.params['folder'].startswith('/' + self.params['datacenter']):
                path = self.params['folder']
            else:
                path = format_folder_path_as_host_fq_path(self.params['folder'], self.params['datacenter'])
            self.folder = self.get_folder_by_absolute_path(folder_path=path, fail_on_missing=True)

        self.host = self.get_esxi_host_by_name_or_moid(identifier=self.params['esxi_host_name'])

    def __host_parent_type_is_folder(self):
        if isinstance(self.host.parent, vim.ClusterComputeResource):
            # the parent is a cluster
            return False
        else:
            return True

    def validate_maintenance_mode(func):
        """
            Decorator function that adds a maintenance mode check before the wrapped method is called.
        """
        def wrapper(self):
            if not self.host.runtime.inMaintenanceMode:
                self.module.fail_json(msg='Host is not in maintenance mode. It must be in maintenance mode before it can be removed.')
            func(self)
        return wrapper

    def create_host_connect_spec(self):
        """
        Function to return Host connection specification
        Returns: host connection specification
        """
        # Get the thumbprint of the SSL certificate
        ssl_thumbprint = self.params['ssl_thumbprint']
        if not ssl_thumbprint:
            ssl_thumbprint = self.get_host_ssl_thumbprint()

        host_connect_spec = vim.host.ConnectSpec()
        host_connect_spec.sslThumbprint = ssl_thumbprint
        host_connect_spec.hostName = self.params['esxi_host_name']
        host_connect_spec.userName = self.params['esxi_username']
        host_connect_spec.password = self.params['esxi_password']
        host_connect_spec.force = self.params['force_add']
        return host_connect_spec

    def add_host(self):
        host_connect_spec = self.create_host_connect_spec()
        _kwargs = {'spec': host_connect_spec, 'license': None}
        if self.folder:
            task = self.folder.AddStandaloneHost(
                **_kwargs, addConnected=self.params['add_connected'], compResSpec=None)
        else:
            task = self.cluster.AddHost_Task(
                **_kwargs, asConnected=self.params['add_connected'], resourcePool=None)
        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to add host %s due to exception %s" % (self.params['esxi_host_name'], to_native(generic_exc))
            ))
        self.host = task_result['result']
        del task_result['result']
        return task_result

    @validate_maintenance_mode
    def remove_host(self):
        if self.__host_parent_type_is_folder():
            task = self.host.parent.Destroy_Task()
        else:
            task = self.host.Destroy_Task()

        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to remove host %s due to exception %s" % (self.params['esxi_host_name'], to_native(generic_exc))
            ))

        return task_result

    @validate_maintenance_mode
    def move_host(self):
        """
            Move the host to a new folder or cluster
        """
        if self.folder:
            if self.__host_parent_type_is_folder():
                task = self.folder.MoveIntoFolder_Task([self.host.parent])
            else:
                task = self.folder.MoveIntoFolder_Task([self.host])
        else:
            task = self.cluster.MoveHostInto_Task(host=self.host, resourcePool=None)
        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Failed to move host %s due to exception %s" % (self.params['esxi_host_name'], to_native(generic_exc))
            ))
        return task_result

    def host_needs_to_be_moved(self):
        """
            Returns true if the host is in the wrong cluster or folder, when compared to the inputs
            the user provided.
            Note that a standalone host (one in a folder) has a ComputeResource as a parent, and the
            parent of that is the folder.
            Returns:
                True if host needs to be moved
        """
        if self.cluster:
            if self.host.parent._GetMoId() == self.cluster._GetMoId():
                return False

        if self.folder:
            if self.host.parent.parent._GetMoId() == self.folder._GetMoId():
                return False

        return True

    def get_host_ssl_thumbprint(self):
        host_fqdn = self.params['esxi_host_name']
        host_port = self.params['esxi_port']
        if self.params['proxy_host']:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect((self.params['proxy_host'], self.params['proxy_port']))
            command = "CONNECT %s:%d HTTP/1.0\r\n\r\n" % (host_fqdn, host_port)
            sock.send(command.encode())
            buf = sock.recv(8192).decode()
            if buf.split()[1] != '200':
                self.module.fail_json(msg="Failed to connect to the proxy")
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            der_cert_bin = ctx.wrap_socket(sock, server_hostname=host_fqdn).getpeercert(True)
            sock.close()
        else:
            try:
                pem = ssl.get_server_certificate((host_fqdn, host_port))
            except Exception:
                self.module.fail_json(msg=f"Cannot connect to host to fetch thumbprint: {host_fqdn}")
            der_cert_bin = ssl.PEM_cert_to_DER_cert(pem)

        if der_cert_bin:
            string = str(hashlib.sha1(der_cert_bin).hexdigest())
            return ':'.join(a + b for a, b in zip(string[::2], string[1::2]))
        else:
            self.module.fail_json(msg=f"Unable to fetch SSL thumbprint for host: {host_fqdn}")

def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                cluster=dict(type='str', required=False, aliases=['cluster_name']),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                folder=dict(type='str', required=False),
                state=dict(type='str', default='present', choices=['absent', 'present']),

                add_connected=dict(type='bool', default=True),
                esxi_host_name=dict(type='str', required=True),
                esxi_username=dict(type='str', required=False),
                esxi_password=dict(type='str', required=False, no_log=True),
                esxi_port=dict(type='str', default='443'),
                ssl_thumbprint=dict(type='str', required=False),
                force_add=dict(type='bool', default=False),
            )
        },
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ('esxi_username', 'esxi_password'), False),
            ('state', 'present', ('cluster', 'folder'), True)
        ],
        mutually_exclusive=[
            ('cluster', 'folder'),
            ('fetch_ssl_thumbprint', 'ssl_thumbprint')
        ]
    )


    result = dict(changed=False, host=dict(name=module.params['esxi_host_name']))

    vmware_host = VmwareHost(module)

    if module.params['state'] == 'present':
        if not vmware_host.host:
            result['changed'] = True
            result['result'] = vmware_host.add_host()
        elif vmware_host.host_needs_to_be_moved():
            result['changed'] = True
            result['result'] = vmware_host.move_host()
        result['host']['moid'] = vmware_host.host._GetMoId()

    if module.params['state'] == 'absent':
        if vmware_host.host:
            result['changed'] = True
            result['host']['moid'] = vmware_host.host._GetMoId()
            result['result'] = vmware_host.remove_host()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
