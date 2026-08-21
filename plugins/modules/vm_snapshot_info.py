#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Project
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
    snapshot_name:
        description:
            - The name of a specific snapshot to gather information about.
            - If neither O(snapshot_name) nor O(snapshot_id) is provided, information about every
              snapshot on the VM is returned.
            - Mutually exclusive with O(snapshot_id).
        type: str
    snapshot_id:
        description:
            - The ID of a specific snapshot to gather information about.
            - If neither O(snapshot_name) nor O(snapshot_id) is provided, information about every
              snapshot on the VM is returned.
            - Mutually exclusive with O(snapshot_name).
        type: int

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

- name: Gather info about a single snapshot by name
  vmware.vmware.vm_snapshot_info:
    moid: vm-42
    snapshot_name: "snapshot4"

- name: Gather info about a single snapshot by ID, without the current snapshot
  vmware.vmware.vm_snapshot_info:
    moid: vm-42
    snapshot_id: 4
    gather_current_snapshot: false
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
        - Empty if the VM has no snapshots.
    returned: Always
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
        - Metadata about the VM's snapshots in a flattened list.
        - When O(snapshot_name) or O(snapshot_id) is set, this is a single-item list describing
          only the requested snapshot. Otherwise it lists every snapshot on the VM.
        - Each entry includes C(parent_id) and C(child_ids), so the flattened
          list can be walked as a tree. C(parent_id) is null for root snapshots.
        - Empty if the VM has no snapshots.
    returned: Always
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

snapshots_tree:
    description:
        - Metadata about the VM's snapshots, arranged as a nested tree instead of the
          flattened list.
        - The value is a dict keyed by snapshot ID. Each entry contains a C(children) key holding
          that snapshot's children in the same keyed-dict structure.
        - When O(snapshot_name) or O(snapshot_id) is set, this holds only the requested snapshot
          and its C(children) is empty.
        - Snapshot IDs are integers, but because the return value is serialized to JSON the keys
          are rendered as strings.
        - Empty if the VM has no snapshots.
    returned: Always
    type: dict
    sample:
        "3":
            creation_time: "2024-12-24T15:27:37.041577+00:00"
            description: "Snapshot 3 example"
            id: 3
            name: "snapshot3"
            state: "poweredOff"
            quiesced: false
            parent_id: null
            child_ids: [4]
            children:
                "4":
                    creation_time: "2024-12-24T15:28:37.041577+00:00"
                    description: "Snapshot 4 example"
                    id: 4
                    name: "snapshot4"
                    state: "poweredOff"
                    quiesced: false
                    parent_id: 3
                    child_ids: []
                    children: {}
'''

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._snapshot import (
    serialize_snapshot_obj_to_json,
    get_snapshot_by_identifier_recursively,
    flatten_snapshot_tree,
    build_nested_snapshot_tree,
)
from ansible.module_utils.basic import AnsibleModule


class VmSnapshotInfoModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]

    def gather_snapshot_info(self):
        """
        Read vm.snapshot exactly once - each access re-fetches the whole snapshot tree from
        vCenter - and derive every representation this module reports from that single in-memory
        copy. The tree returned by vCenter is a graph of data objects, so walking it (here and in
        the _snapshot helpers) makes no additional calls; it can be traversed as many times as
        needed for free.

        When O(snapshot_name) or O(snapshot_id) is given, only the matching snapshot is reported
        in 'snapshots'/'snapshots_tree'; otherwise every snapshot is reported. The requested
        snapshot is taken from the flattened list so its parent_id and child_ids are correct.
        Returns:
            A dict with keys:
              'current'        - the serialized current snapshot dict, or an empty dict if the
                                 VM has no snapshots or no current snapshot
              'snapshots'      - flat list of serialized snapshot dicts (depth-first) when
                                 reporting every snapshot, or a single-item list when a specific
                                 snapshot is requested
              'snapshots_tree' - nested dict keyed by snapshot ID, each value a serialized snapshot
                                 dict plus a 'children' key holding the same structure for its
                                 children. Holds only the requested snapshot, with no children
                                 expanded, when a specific snapshot is requested
        """
        snapshot_info = self.vm.snapshot
        if not snapshot_info:
            return {'current': {}, 'snapshots': [], 'snapshots_tree': {}}

        result = {'current': self._gather_current_snapshot(snapshot_info)}

        if self.params['snapshot_name'] is None and self.params['snapshot_id'] is None:
            result['snapshots'] = flatten_snapshot_tree(snapshot_info.rootSnapshotList)
            result['snapshots_tree'] = build_nested_snapshot_tree(snapshot_info.rootSnapshotList)
        else:
            result['snapshots'], result['snapshots_tree'] = self._gather_requested_snapshot(snapshot_info)

        return result

    def _gather_current_snapshot(self, snapshot_info):
        """
        Return the serialized current snapshot, or an empty dict if the VM has no current snapshot.
        """
        if snapshot_info.currentSnapshot is None:
            return {}

        current_object = get_snapshot_by_identifier_recursively(
            snapshot_trees=snapshot_info.rootSnapshotList,
            snap_ref=snapshot_info.currentSnapshot
        )
        return serialize_snapshot_obj_to_json(current_object)

    def _gather_requested_snapshot(self, snapshot_info):
        """
        Return the ('snapshots', 'snapshots_tree') pair describing only the snapshot named by
        O(snapshot_name) or O(snapshot_id). The snapshot is taken from the flattened tree so its
        parent_id and child_ids are correct.
        """
        snapshot_name = self.params['snapshot_name']
        snapshot_id = self.params['snapshot_id']

        match = next(
            (node for node in flatten_snapshot_tree(snapshot_info.rootSnapshotList)
             if (snapshot_name is not None and node['name'] == snapshot_name)
             or (snapshot_id is not None and node['id'] == snapshot_id)),
            None
        )
        if match is None:
            return [], []

        return [match], {match['id']: {**match, 'children': {}}}


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
                snapshot_name=dict(type='str'),
                snapshot_id=dict(type='int'),
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
            ('name', 'uuid', 'moid'),
            ('snapshot_name', 'snapshot_id'),
        ]
    )

    vm_snapshot_info = VmSnapshotInfoModule(module)
    snapshot_info = vm_snapshot_info.gather_snapshot_info()

    result = {
        'vm': {
            'moid': vm_snapshot_info.vm._GetMoId(),
            'name': vm_snapshot_info.vm.name
        },
        'current_snapshot': snapshot_info['current'],
        'snapshots': snapshot_info['snapshots'],
        'snapshots_tree': snapshot_info['snapshots_tree'],
    }

    module.exit_json(**result)


if __name__ == '__main__':
    main()
