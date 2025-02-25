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
module: vmware_guest_snapshot
short_description: Manages virtual machines snapshots in vCenter
description:
    - This module can be used to create, delete and update snapshot(s) of the given virtual machine.
author:
    - Loic Blot (@nerzhul) <loic.blot@unix-experience.fr>
options:
   state:
     description:
     - Manage snapshot(s) attached to a specific virtual machine.
     - If set to V(present) and snapshot absent, then will create a new snapshot with the given name.
     - If set to V(absent) and snapshot present, then snapshot with the given name is removed.
     - If set to V(rename) and snapshot present, then snapshot will be given new name and description.
     - If set to V(revert) and snapshot present, then virtual machine state is reverted to the given snapshot.
     - If set to V(remove_all) and snapshot(s) present, then all snapshot(s) will be removed.
     choices: ['present', 'absent', 'rename', 'revert', 'remove_all']
     default: 'present'
     type: str
   name:
     description:
     - Name of the virtual machine to work with.
     - This is required parameter, if O(uuid) or O(moid) is not supplied.
     type: str
   name_match:
     description:
     - If multiple VMs matching the name, use the first or last found.
     default: 'first'
     choices: ['first', 'last']
     type: str
   uuid:
     description:
     - UUID of the instance to manage if known, this is VMware's BIOS UUID by default.
     - This is required if O(name) or O(moid) parameter is not supplied.
     type: str
   moid:
     description:
     - Managed Object ID of the instance to manage if known, this is a unique identifier only within a single vCenter instance.
     - This is required if O(name) or O(uuid) is not supplied.
     type: str
   use_instance_uuid:
     description:
     - Whether to use the VMware instance UUID rather than the BIOS UUID.
     default: false
     type: bool
   folder:
     description:
     - Destination folder, absolute or relative path to find an existing guest.
     - This parameter is required if O(name) is supplied.
     - Should be the full folder path, with or without the 'datacenter/vm/' prefix
     - For example 'datacenter name/vm/path/to/folder' or 'path/to/folder'
     type: str
   datacenter:
     description:
     - Destination datacenter for the deploy operation.
     required: true
     type: str
   snapshot_name:
     description:
     - Sets the snapshot name to manage.
     - This param or O(snapshot_id) is required only if O(state) is not C(remove_all)
     type: str
   snapshot_id:
     description:
     - Sets the snapshot id to manage.
     - This param is available when O(state=absent) or O(state=revert).
     type: int
     version_added: 3.10.0
   description:
     description:
     - Define an arbitrary description to attach to snapshot.
     default: ''
     type: str
   quiesce:
     description:
     - If set to V(true) and virtual machine is powered on, it will quiesce the file system in virtual machine.
     - Note that VMware Tools are required for this flag.
     - If virtual machine is powered off or VMware Tools are not available, then this flag is set to V(false).
     - If virtual machine does not provide capability to take quiesce snapshot, then this flag is set to V(false).
     type: bool
     default: false
   memory_dump:
     description:
     - If set to V(true), memory dump of virtual machine is also included in snapshot.
     - Note that memory snapshots take time and resources, this will take longer time to create.
     - If virtual machine does not provide capability to take memory snapshot, then this flag is set to V(false).
     type: bool
     default: false
   remove_children:
     description:
     - If set to V(true) and O(state=absent), then entire snapshot subtree is set for removal.
     type: bool
     default: false
   new_snapshot_name:
     description:
     - Value to rename the existing snapshot to.
     type: str
   new_description:
     description:
     - Value to change the description of an existing snapshot to.
     type: str



extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
  - name: Create a snapshot
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: present
      snapshot_name: snap1
      description: snap1_description

  - name: Remove a snapshot
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: absent
      snapshot_name: snap1

  - name: Revert to a snapshot
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: revert
      snapshot_name: snap1

  - name: Remove all snapshots of a VM
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: remove_all

  - name: Remove all snapshots of a VM using MoID
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      moid: vm-42
      state: remove_all

  - name: Take snapshot of a VM using quiesce and memory flag on
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: present
      snapshot_name: dummy_vm_snap_0001
      quiesce: true
      memory_dump: true

  - name: Remove a snapshot and snapshot subtree
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: absent
      remove_children: true
      snapshot_name: snap1

  - name: Remove a snapshot with a snapshot id
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      snapshot_id: 10
      state: absent

  - name: Rename a snapshot
    vmware.vmware.vm_snapshot:
      hostname: "{{ vcenter_hostname }}"
      username: "{{ vcenter_username }}"
      password: "{{ vcenter_password }}"
      datacenter: "{{ datacenter_name }}"
      folder: "/{{ datacenter_name }}/vm/"
      name: "{{ guest_name }}"
      state: rename
      snapshot_name: current_snap_name
      new_snapshot_name: im_renamed
      new_description: "{{ new_snapshot_description }}"
'''

RETURN = r'''
snapshot_results:
    description: metadata about the virtual machine snapshots
    returned: always
    type: dict
    sample: {
      "current_snapshot": {
          "creation_time": "2019-04-09T14:40:26.617427+00:00",
          "description": "Snapshot 4 example",
          "id": 4,
          "name": "snapshot4",
          "state": "poweredOff"
      },
      "snapshots": [
          {
              "creation_time": "2019-04-09T14:38:24.667543+00:00",
              "description": "Snapshot 3 example",
              "id": 3,
              "name": "snapshot3",
              "state": "poweredOff"
          },
          {
              "creation_time": "2019-04-09T14:40:26.617427+00:00",
              "description": "Snapshot 4 example",
              "id": 4,
              "name": "snapshot4",
              "state": "poweredOff"
          }
      ]
    }
'''

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import format_folder_path_as_vm_fq_path
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import TaskError, RunningTaskMonitor
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text, to_native
from ansible_collections.community.vmware.plugins.module_utils.vmware import list_snapshots


class VmSnapshotModule(ModulePyvmomiBase):
    def __init__(self, module):
        super(ModulePyvmomiBase, self).__init__(module)
        self.result = dict(
            changed=False,
            renamed=False
        )

        if self.vm.snapshot is None:
            self.snap_object = None
        else:
            self.snap_object = self.get_snapshots_recursively()
            if len(self.snap_object) == 1:
                self.snap_object = self.snap_object[0].snapshot
            else:
                self.snap_object = None
        vm_list = self.get_vm_using_params(fail_on_missing=True)
        self.vm = vm_list[0]
        self.vm_id = self.module.params.get('uuid') or self.module.params.get('name') or self.module.params.get('moid')
        if not self.vm:
            module.fail_json(msg="Unable to manage snapshots for non-existing VM %s" % self.vm_id)

        if not (module.params['snapshot_name'] or module.params['snapshot_id']) and module.params['state'] != 'remove_all':
            module.fail_json(msg="snapshot_name param required when state is '%(state)s'" % module.params)

    def get_snapshots_by_name_recursively(self, snapshots, snapname):
        snap_obj = []
        for snapshot in snapshots:
            if snapshot.name == snapname:
                snap_obj.append(snapshot)
            else:
                snap_obj = snap_obj + self.get_snapshots_by_name_recursively(snapshot.childSnapshotList, snapname)
        return snap_obj

    def get_snapshots_by_id_recursively(self, snapshots, snapid):
        snap_obj = []
        for snapshot in snapshots:
            if snapshot.id == snapid:
                snap_obj.append(snapshot)
            else:
                snap_obj = snap_obj + self.get_snapshots_by_id_recursively(snapshot.childSnapshotList, snapid)
        return snap_obj
    
    def get_snapshots_recursively(self):
        if self.module.params["snapshot_name"]:
            return self.get_snapshots_by_name_recursively(self.vm.snapshot.rootSnapshotList,
                                                              self.module.params["snapshot_name"])
        elif self.module.params["snapshot_id"] and self.module.params["state"] in ['absent', 'revert']:
            return self.get_snapshots_by_id_recursively(self.vm.snapshot.rootSnapshotList,
                                                            self.module.params["snapshot_id"])

    def snapshot_vm(self):
        if self.snap_object:
            self.module.exit_json(changed=False,
                                    msg="Snapshot named [%(snapshot_name)s] already exists" % self.module.params)

        memory_dump = self.module.params['memory_dump'] and self.vm.capability.memorySnapshotsSupported
        quiesce = self.module.params['quiesce'] and self.vm.capability.quiescedSnapshotsSupported
        try:
            return self.vm.CreateSnapshot(self.module.params["snapshot_name"],
                                     self.module.params["description"],
                                     memory_dump,
                                     quiesce)
        except vim.fault.RestrictedVersion as e:
            self.module.fail_json(msg="Failed to take snapshot due to VMware Licence"
                                      " restriction : %s" % to_native(e.msg))
        except Exception as e:
            self.module.fail_json(msg="Failed to create snapshot of virtual machine"
                                      " %s due to %s" % (self.module.params['name'], to_native(e)))

    def rename_snapshot(self):
        if self.module.params["new_snapshot_name"] and self.module.params["new_description"]:
            task = self.snap_object.RenameSnapshot(name=self.module.params["new_snapshot_name"],
                                            description=self.module.params["new_description"])
        elif self.module.params["new_snapshot_name"]:
            task = self.snap_object.RenameSnapshot(name=self.module.params["new_snapshot_name"])
        else:
            task = self.snap_object.RenameSnapshot(description=self.module.params["new_description"])
        
        self.result['changed'] = True
        self.result['renamed'] = True
        return task

    def apply_snapshot_op(self):
        if self.module.params["state"] in ["absent", "revert", "rename"] and self.snap_object is None:
            self.module.fail_json(
                msg="Couldn't find any snapshots with specified name: %s on VM: %s" %
                    (self.module.params["snapshot_name"] or self.module.params["snapshot_id"], self.vm_id))
        
        snapshot_state_function = {
            'present': self.snapshot_vm,
            'rename': self.rename_snapshot,
            'absent': lambda: self.snap_object.RemoveSnapshot_Task(self.module.params.get('remove_children', False)),
            'revert': self.snap_object.RevertToSnapshot_Task,
            'remove_all': self.vm.RemoveAllSnapshots
        }

        try:
            task = snapshot_state_function[self.module.params['state']]()
        except Exception as e:
            self.module.fail_json(msg=to_text(e))
        
        if not task:
            return
        
        try:
            _, task_result = RunningTaskMonitor(task).wait_for_completion(vm=self.vm)
        except TaskError as e:
            self.module.fail_json(msg=to_text(e))
        
        self.result['changed'] = True
        self.result['snapshot_results'] = list_snapshots(self.vm)


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                state=dict(default='present', choices=['present', 'absent', 'rename', 'revert', 'remove_all']),
                name=dict(type='str'),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str'),
                datacenter=dict(required=True, type='str'),
                snapshot_name=dict(type='str'),
                snapshot_id=dict(type='int'),
                description=dict(type='str', default=''),
                quiesce=dict(type='bool', default=False),
                memory_dump=dict(type='bool', default=False),
                remove_children=dict(type='bool', default=False),
                new_snapshot_name=dict(type='str'),
                new_description=dict(type='str'),
            )
        },
        required_together=[
            ['name', 'folder']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
        mutually_exclusive=[
            ['snapshot_name', 'snapshot_id'],
            ['name', 'uuid', 'moid']
        ]
    )

    if module.params['folder']:
        module.params['folder'] = format_folder_path_as_vm_fq_path(
            module.params['folder'],
            module.params['datacenter']
        )

    vm_snapshot = VmSnapshotModule(module)
    vm_snapshot.apply_snapshot_op()
    module.exit_json(**vm_snapshot.result)


if __name__ == '__main__':
    main()