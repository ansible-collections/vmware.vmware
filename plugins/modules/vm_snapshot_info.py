#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Ansible Project
# This module is also sponsored by E.T.A.I. (www.etai.fr)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_snapshot_info
short_description: Gathers information about a VMs snapshots
description:
    - This module can be used to gather information about a virtual machine's snapshots.
author:
    - Ansible Cloud Team (@ansible-collections)
options:
    name:
        description:
        - Name of the virtual machine to work with.
        - This is required parameter, if O(uuid) or O(moid) is not supplied.
        type: str
    name_match:
        description:
        - If multiple VMs with the same name exist, use the first or last found.
        default: 'first'
        choices: ['first', 'last']
        type: str
    uuid:
        description:
        - UUID of the instance to manage. This is VMware's BIOS UUID by default.
        - This is required if O(name) or O(moid) parameter is not supplied.
        type: str
    moid:
        description:
        - Managed Object ID of the virtual machine to manage.
        - This is required if O(name) or O(uuid) is not supplied.
        type: str
    use_instance_uuid:
        description:
        - Whether to use the VMware instance UUID rather than the BIOS UUID.
        default: false
        type: bool
    folder:
        description:
        - Absolute or relative folder path to search for the virtual machine.
        - This parameter is required if O(name) is supplied.
        - For example 'datacenter name/vm/path/to/folder' or 'path/to/folder'
        type: str
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, modules will try to intelligently determine if the path is absolute
              or relative.
            - This option is useful when your environment has a complex folder structure. By default,
              modules will try to intelligently determine if the path is absolute or relative.
              They may mistakenly prepend the datacenter name or other folder names, and this option
              can be used to avoid this.
        type: bool
        required: false
        default: false
    datacenter:
        description:
        - Datacenter to search for the virtual machine.
        type: str
    gather_current_snapshot:
        description:
        - If true, the metadata for the VM's current snapshot is returned in RV(current_snapshot).
        type: bool
        default: true
    gather_all_snapshots:
        description:
        - If true, the metadata for all of the VM's snapshots is returned in RV(snapshots).
        type: bool
        default: true

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Gather all snapshot info for a VM
  vmware.vmware.vm_snapshot_info:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: "{{ datacenter_name }}"
    folder: "/{{ datacenter_name }}/vm/"
    name: "{{ guest_name }}"

- name: Gather only the current snapshot info for a VM using its MoID
  vmware.vmware.vm_snapshot_info:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    moid: vm-42
    gather_all_snapshots: false
    gather_current_snapshot: true
'''

RETURN = r'''
vm:
    description:
        - Information about the target VM
    returned: Always
    type: dict
    sample:
        moid: vm-79828,
        name: test-d9c1-vm

current_snapshot:
    description:
        - Metadata about the VM's current snapshot.
        - Empty if O(gather_current_snapshot) is true but the VM has no snapshots.
    returned: When O(gather_current_snapshot) is true
    type: dict
    sample:
        creation_time: "2024-12-24T15:27:37.041577+00:00"
        description: "Snapshot 4 example"
        id: 4
        name: "snapshot4"
        state: "poweredOff"
        quiesced: false
        parent_id: 3
        child_ids: [5, 6]

snapshots:
    description:
        - Metadata about all of the VM's snapshots.
        - Each entry includes RV(snapshots[].parent_id) and RV(snapshots[].child_ids), so the flattened
          list can be walked as a tree. RV(snapshots[].parent_id) is null for root snapshots.
        - Empty if O(gather_all_snapshots) is true but the VM has no snapshots.
    returned: When O(gather_all_snapshots) is true
    type: list
    elements: dict
    sample:
        [
            {
                creation_time: "2024-12-24T15:27:37.041577+00:00",
                description: "Snapshot 4 example",
                id: 4,
                name: "snapshot4",
                state: "poweredOff",
                quiesced: false,
                parent_id: 3,
                child_ids: [5, 6]
            }
        ]
'''

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vm_snapshot import (
    serialize_snapshot_obj_to_json,
    get_snapshot_tree_by_snapshot_ref,
    list_snapshots_recursively,
)
from ansible.module_utils.basic import AnsibleModule


class VmSnapshotInfoModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]

    def gather_current_snapshot_info(self):
        """
        Resolve the VM's currentSnapshot reference to its tree node and serialize it.
        Returns an empty dict if the VM has no snapshots.
        """
        if not self.vm.snapshot:
            return dict()

        current_snapshot_tree, parent_id = get_snapshot_tree_by_snapshot_ref(
            self.vm.snapshot.rootSnapshotList,
            self.vm.snapshot.currentSnapshot
        )
        return serialize_snapshot_obj_to_json(current_snapshot_tree, parent_id=parent_id)

    def gather_all_snapshots_info(self):
        """
        Flatten and serialize the VM's entire snapshot tree.
        Returns an empty list if the VM has no snapshots.
        """
        if not self.vm.snapshot:
            return []

        return list_snapshots_recursively(self.vm.snapshot.rootSnapshotList)


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                name=dict(type='str'),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str'),
                folder_paths_are_absolute=dict(type='bool', required=False, default=False),
                datacenter=dict(type='str'),
                gather_current_snapshot=dict(type='bool', default=True),
                gather_all_snapshots=dict(type='bool', default=True),
            )
        },
        supports_check_mode=True,
        required_together=[
            ['name', 'folder']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
        mutually_exclusive=[
            ('name', 'uuid', 'moid')
        ]
    )

    vm_snapshot_info = VmSnapshotInfoModule(module)
    result = {
        'vm': {
            'moid': vm_snapshot_info.vm._GetMoId(),
            'name': vm_snapshot_info.vm.name
        }
    }

    if module.params['gather_current_snapshot']:
        result['current_snapshot'] = vm_snapshot_info.gather_current_snapshot_info()

    if module.params['gather_all_snapshots']:
        result['snapshots'] = vm_snapshot_info.gather_all_snapshots_info()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
