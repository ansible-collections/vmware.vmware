#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Ansible Project
# This module is also sponsored by E.T.A.I. (www.etai.fr)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: vm_snapshot_revert
short_description: Revert a virtual machine to a snapshot
description:
    - This module can be used to revert a virtual machine to a snapshot.
    - Since the virtual machine immediately begins to drift from the snapshot, this module will always
      attempt to revert the virtual machine. A change will always be reported.
    - If the snapshot is not found, the module will fail.

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
            - The name of the snapshot to revert to.
            - Either this parameter or O(snapshot_id) is required.
        type: str
    snapshot_id:
        description:
            - The ID of the snapshot to revert to.
            - Either this parameter or O(snapshot_name) is required.
        type: int
    suppress_power_on:
        description:
            - If true, the virtual machine will not be powered on after the snapshot is reverted, even if the snapshot was taken
              while the virtual machine was powered on.
        type: bool
        default: false

extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
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
  register: _create_snap

- name: Revert VM to snapshot
  vmware.vmware.vm_snapshot_revert:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    moid: "{{ _create_snap.vm.moid }}"
    snapshot_name: snap1
"""

RETURN = r"""
vm:
    description:
        - Information about the target VM
    returned: Always
    type: dict
    sample:
        moid: vm-79828,
        name: test-d9c1-vm

snapshot:
    description:
        - Information about the snapshot
    returned: Always
    type: dict
    sample:
        name: snap1
        id: 1

result:
    description:
        - Information about the vCenter task, if one was run
    returned: On change
    type: dict
    sample:
        completion_time: "2025-04-15T23:29:47.435215+00:00"
        entity_name: "test-e7e0-vm"
        error: null
        state: "success"

"""

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    RunningTaskMonitor,
)
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text


class VmSnapshotRevertModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]
        self.snapshot = self._get_snapshot_by_identifier_recursively(
            self.vm.snapshot.rootSnapshotList,
            self.module.params["snapshot_name"] or self.module.params["snapshot_id"],
        )
        if not self.snapshot:
            self.module.fail_json(
                msg="Unable to find a snapshot with the name '%s' or ID '%s'"
                % (
                    self.module.params["snapshot_name"],
                    self.module.params["snapshot_id"],
                )
            )

    def _get_snapshot_by_identifier_recursively(self, snapshot_list, snapidentifier):
        for snapshot in snapshot_list:
            if snapidentifier == snapshot.id or snapidentifier == snapshot.name:
                return snapshot
            else:
                return self._get_snapshot_by_identifier_recursively(
                    snapshot.childSnapshotList, snapidentifier
                )
        return None

    def revert_to_snapshot(self):
        task_result = {}
        try:
            task = self.snapshot.snapshot.RevertToSnapshot_Task(suppressPowerOn=self.params['suppress_power_on'])
            _, task_result = RunningTaskMonitor(   # pylint: disable=disallowed-name
                task
            ).wait_for_completion()
        except (vim.fault.FileFault, vim.fault.InsufficientResourcesFault, vim.fault.InvalidPowerState, vim.fault.InvalidState) as e:
            self.module.fail_json(
                msg="Failed to revert VM to snapshot due to invalid state: %s" % to_text(e),
                error_type=str(e.__class__.__name__),
                snapshot=dict(name=self.snapshot.name, id=self.snapshot.id),
                vm=dict(name=self.vm.name, moid=self.vm._GetMoId()),
            )
        except Exception as e:
            self.module.fail_json(msg="Unhandled exception while reverting VM to snapshot: %s" % to_text(e))

        del task_result["result"]  # delete the vm object held in this key, since its a ton of extra data
        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                name=dict(type="str"),
                name_match=dict(type="str", choices=["first", "last"], default="first"),
                uuid=dict(type="str"),
                moid=dict(type="str"),
                use_instance_uuid=dict(type="bool", default=False),
                folder=dict(type="str"),
                folder_paths_are_absolute=dict(
                    type="bool", required=False, default=False
                ),
                datacenter=dict(type="str"),
                snapshot_name=dict(type="str"),
                snapshot_id=dict(type="int"),
                suppress_power_on=dict(type="bool", default=False),
            ),
        },
        supports_check_mode=True,
        required_one_of=[["snapshot_name", "snapshot_id"], ["name", "uuid", "moid"]],
        mutually_exclusive=[("name", "uuid", "moid"), ("snapshot_name", "snapshot_id")],
    )

    result = dict(
        changed=False,
        vm=dict(name=None, moid=None),
        snapshot=dict(name=None, id=None),
    )

    vm_snapshot_revert = VmSnapshotRevertModule(module)
    result["vm"]["name"] = vm_snapshot_revert.vm.name
    result["vm"]["moid"] = vm_snapshot_revert.vm._GetMoId()
    result["snapshot"]["name"] = vm_snapshot_revert.snapshot.name
    result["snapshot"]["id"] = vm_snapshot_revert.snapshot.id
    result["changed"] = True

    if not module.check_mode:
        result["result"] = vm_snapshot_revert.revert_to_snapshot()

    module.exit_json(**result)


if __name__ == "__main__":
    main()
