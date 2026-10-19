#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vm_hardware_version
short_description: Specify the virtual hardware version for virtual machine.
description:
    - This module is used to ensure a virtual hardware version for a virtual machine.
    - If the current version does not match the desired state, the virtual machine will be upgraded.
    - The module can optionally perform power cycles and snapshots as part of the upgrade process.
    - Downgrades are not supported by the module. There is a process documented by Broadcom to
      downgrade a VM. It requires a snapshot of the VM at the desired HW version.

author:
    - Mike Morency (@mikemorency)

options:
    version:
        description:
            - The hardware version that the VM should be upgraded to.
            - This can be an integer, like V(19), or a string formatted as C(vmx-<version>), like V(vmx-19).
            - If set to V(latest), the VM is upgraded to the highest hardware version supported by the
              VM's compute resource (host or cluster).
            - The version must be one that the VM can be upgraded to in your environment. Otherwise, the module
              will fail and return the list of available versions.
            - If the version is lower than the VM's current version, the module will fail.
        type: str
        required: true

    datacenter:
        description:
            - The name of the datacenter that contains the VM.
            - This is only used to build the full folder path when O(folder) is a relative path.
        type: str
        aliases: [ datacenter_name ]
    name:
        description:
            - The name of the VM to manage.
            - VM names in vCenter are not necessarily unique. If multiple VMs have the same name, use O(name_match)
              to select one, or use O(folder) to limit the search.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    name_match:
        description:
            - If multiple VMs match the given name, use the first or last one found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - The UUID of the VM to manage.
            - By default, this is the BIOS UUID. Set O(use_instance_uuid) to V(true) to use the vCenter instance
              UUID instead.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    moid:
        description:
            - The managed object ID (MOID) of the VM to manage, for example V(vm-1234).
            - The MOID is only unique within a single vCenter instance.
            - Exactly one of O(name), O(uuid), or O(moid) is required.
        type: str
    use_instance_uuid:
        description:
            - Whether O(uuid) is the vCenter instance UUID rather than the BIOS UUID.
        default: false
        type: bool
    folder:
        description:
            - The absolute or relative path of the folder to search for the VM.
            - This is used to narrow the search when O(name) or O(moid) is supplied. It is ignored when O(uuid) is used.
            - The path can be given with or without the C(<datacenter>/vm/) prefix,
              for example V(datacenter_name/vm/path/to/folder) or V(path/to/folder).
        type: str
        required: false
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, the module will try to determine whether the path is absolute or relative.
            - This option is useful when your environment has a complex folder structure and the module
              incorrectly prepends the datacenter name or other folder names to the path.
        type: bool
        required: false
        default: false

    allow_power_cycling:
        description:
            - Whether to allow the module to power off the VM, if it is powered on, so that the upgrade can be applied.
              If the VM was powered off by the module, it is powered back on after the upgrade.
            - If this is false and the VM is powered on, the module will fail.
            - The power off is a "hard" power off, not a guest OS shutdown. To shut down the guest gracefully instead,
              run this module in check mode to see if an upgrade is needed, use the M(vmware.vmware.vm_powerstate) module
              to shut down the VM, and then run this module again to apply the upgrade.
            - If the snapshot or upgrade fails after the VM has been powered off, the VM is left powered off.
        type: bool
        required: false
        default: false
    snapshot_before_upgrade:
        description:
            - If true, a snapshot of the VM is taken before the upgrade starts. If the VM needs to be powered off,
              the snapshot is taken after the power off.
            - The snapshot does not include the VM's memory and the guest file system is not quiesced.
            - If a snapshot is taken, its ID and name are returned in RV(snapshot).
            - Snapshots can be managed further using the M(vmware.vmware.vm_snapshot) module(s).
        type: bool
        required: false
        default: false
    timeout:
        description:
            - The time, in seconds, to wait for each vSphere task (power off, snapshot, upgrade, power on)
              to complete.
            - This timeout applies to each task individually, not to the module run as a whole.
        type: int
        required: false
        default: 600

    ignore_downgrades:
        description:
            - If true, the module will report no change and exit normally if a downgrade is requested.
            - If false, the module will raise an error if a downgrade is requested, since it is not supported.
            - This is useful when processing output from another module, such as M(vmware.vmware.vm_info). See
              the examples for more information.
        type: bool
        default: false

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
# By default, this module fails if the requested version is lower than the VM's current version.
# Set ignore_downgrades to true to treat a VM that is already at a higher version as unchanged,
# so the requested version acts as a minimum.
# Power cycling is not allowed, so VMs that are powered on and need an upgrade will cause a failure.
- name: Gather the hardware version of all VMs in a folder
  vmware.vmware.vm_info:
    folder: /DC01/vm/app-servers
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - config.version
  register: _vm_info

- name: Upgrade powered off VMs that are below hardware version 19
  vmware.vmware.vm_hardware_version:
    folder: /DC01/vm/app-servers
    name: "{{ item.name }}"
    version: vmx-19
    ignore_downgrades: true
  loop: "{{ _vm_info.vms }}"
  loop_control:
    label: "{{ item.name }} ({{ item.config.version }})"

# If the VM is powered on, the module will fail unless power cycling is allowed.
# The VM is hard powered off, upgraded, and then powered back on.
- name: Upgrade a VM to the latest supported hardware version, power cycling it if needed
  vmware.vmware.vm_hardware_version:
    name: app-server-01
    version: latest
    allow_power_cycling: true

# The snapshot is taken after the VM is powered off and before the upgrade starts.
# The snapshot does not include memory, so it can be used to return to the old hardware version
# if there is a problem with the upgrade.
- name: Upgrade a VM, taking a snapshot before the upgrade
  vmware.vmware.vm_hardware_version:
    name: app-server-01
    version: 21
    allow_power_cycling: true
    snapshot_before_upgrade: true
  register: _upgrade

- name: Show the snapshot that was taken before the upgrade
  ansible.builtin.debug:
    msg: "Snapshot {{ _upgrade.snapshot.name }} (ID {{ _upgrade.snapshot.id }}) was created"
  when: _upgrade.snapshot

# Large VMs or busy environments may need more time for each task (power off, snapshot,
# upgrade, power on) to complete
- name: Upgrade a VM with a snapshot, allowing up to 30 minutes for each task
  vmware.vmware.vm_hardware_version:
    name: large-db-01
    version: latest
    allow_power_cycling: true
    snapshot_before_upgrade: true
    timeout: 1800

# Check mode reports if an upgrade is needed and if the VM would be power cycled,
# without making any changes
- name: Check if an upgrade is needed and if it would power cycle the VM
  vmware.vmware.vm_hardware_version:
    name: app-server-01
    version: latest
    allow_power_cycling: true
  check_mode: true
  register: _hw_check

- name: Report the pending upgrade
  ansible.builtin.debug:
    msg: >-
      {{ _hw_check.vm.name }} would be upgraded from {{ _hw_check.diff.before.version }}
      to {{ _hw_check.diff.after.version }}.
      Power cycle required: {{ _hw_check.power_cycled }}
  when: _hw_check.changed

# This module performs a hard power off. To shut down the guest OS gracefully instead,
# use check mode to see if an upgrade is needed, shut down the guest with the
# vm_powerstate module, upgrade the VM, and then power it back on.
- name: Check if the VM needs a hardware upgrade
  vmware.vmware.vm_hardware_version:
    name: app-server-01
    version: latest
  check_mode: true
  register: _hw_check

- name: Upgrade the VM hardware with a graceful shutdown
  when: _hw_check.changed
  block:
    - name: Shut down the guest OS
      vmware.vmware.vm_powerstate:
        moid: "{{ _hw_check.vm.moid }}"
        state: shutdown-guest

    - name: Upgrade the VM hardware version, taking a snapshot first
      vmware.vmware.vm_hardware_version:
        moid: "{{ _hw_check.vm.moid }}"
        version: latest
        snapshot_before_upgrade: true

    - name: Power the VM back on
      vmware.vmware.vm_powerstate:
        moid: "{{ _hw_check.vm.moid }}"
        state: powered-on
'''

RETURN = r'''
vm:
    description:
        - Information about the target VM.
    returned: always
    type: dict
    sample:
        moid: vm-79828
        name: test-d9c1-vm
power_cycled:
    description:
        - Whether the VM was powered off and back on so that the upgrade could be applied.
        - In check mode, this is whether the VM would be power cycled.
        - This is always false if no upgrade is needed.
    returned: always
    type: bool
    sample: true
snapshot:
    description:
        - Information about the snapshot taken before the upgrade.
        - This is empty if no snapshot was taken, including when O(snapshot_before_upgrade) is false,
          no upgrade is needed, or the module is run in check mode.
    returned: always
    type: dict
    contains:
        id:
            description:
                - The ID of the snapshot.
            type: int
        name:
            description:
                - The name of the snapshot. The name includes the VM's hardware version before the upgrade
                  and the time the snapshot was taken.
            type: str
    sample:
        id: 12
        name: hw-upgrade-vmx-17-20251016-101500
'''
from datetime import datetime
from functools import total_ordering

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native
from ansible_collections.vmware.vmware.plugins.module_utils.vm._snapshot import (
    get_snapshot_by_identifier_recursively,
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError, RunningTaskMonitor
)


@total_ordering
class HwVersion():
    def __init__(self, version):
        if isinstance(version, HwVersion):
            version = version.version
        elif isinstance(version, str):
            version = version.replace('vmx-', '')

        self.version = int(version)

    def _coerce(self, other):
        if isinstance(other, HwVersion):
            return other
        try:
            return HwVersion(other)
        except (TypeError, ValueError):
            return None

    def __eq__(self, other):
        other = self._coerce(other)
        if other is None:
            return NotImplemented
        return self.version == other.version

    def __lt__(self, other):
        other = self._coerce(other)
        if other is None:
            return NotImplemented
        return self.version < other.version

    def __hash__(self):
        return hash(self.version)

    def __int__(self):
        return self.version

    def __str__(self):
        return "vmx-%02d" % self.version

    def __repr__(self):
        return "HwVersion(%r)" % str(self)


class VmHardwareModule(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        self.vm = self.get_vms_using_params(fail_on_missing=True)[0]
        if self.vm.config.template:
            self.module.fail_json("Managing the hardware version of a template is not supported.")

        self.current_version = HwVersion(self.vm.config.version)
        self._all_supported_versions = None

    @property
    def all_supported_versions(self):
        if self._all_supported_versions is None:
            config_option_descriptors = self.vm.environmentBrowser.QueryConfigOptionDescriptor()
            self._all_supported_versions = set()
            for option_desc in config_option_descriptors:
                if not option_desc.upgradeSupported:
                    continue
                self._all_supported_versions.add(HwVersion(option_desc.key))

        if not self._all_supported_versions:
            self.module.fail_json("There are no supported hardware versions for this VM.")

        return self._all_supported_versions

    def get_desired_version(self):
        param_version = self.params.get('version')
        if param_version == 'latest':
            return max(self.all_supported_versions)

        try:
            return HwVersion(param_version)
        except ValueError:
            self.module.fail_json(
                "The version parameter must either be an integer ('19') or a string formatted like 'vmx-19'."
            )

    def is_hw_change_needed(self, desired_version):
        if self.current_version == desired_version:
            return False

        if desired_version < self.current_version:
            if self.params.get('ignore_downgrades'):
                return False

            self.module.fail_json(
                msg="The desired hardware version cannot be less than the current version. Downgrades are not supported.",
                desired_version=str(desired_version),
                current_version=str(self.current_version)
            )

        for hw_version in self.all_supported_versions:
            if hw_version == desired_version:
                return True

        self.module.fail_json(
            msg="The desired hardware version was not found in the list of available versions.",
            desired_version=str(desired_version),
            available_versions=[str(v) for v in self.all_supported_versions]
        )

    def upgrade_vm(self, desired_version):
        self._try_to_run_task(
            task_func=self.vm.UpgradeVM_Task,
            task_kwargs=dict(version=str(desired_version)),
            action="upgrade"
        )

    def snapshot_vm(self):
        """
        Attempt to snapshot the VM before the upgrade but after its powered off.
        """
        if not self.params['snapshot_before_upgrade']:
            return dict()

        snapshot_name = "hw-upgrade-%s-%s" % (
            str(self.current_version),
            datetime.now().strftime("%Y%m%d-%H%M%S")
        )
        task_result = self._try_to_run_task(
            task_func=self.vm.CreateSnapshot_Task,
            action="take snapshot",
            task_kwargs=dict(
                name=snapshot_name,
                description=("Created by vmware.vmware.vm_hardware_version at version %s" % self.current_version),
                memory=False,
                quiesce=False
            )
        )

        snapshot_tree = get_snapshot_by_identifier_recursively(
            self.vm.snapshot.rootSnapshotList, snap_ref=task_result['result']
        )
        return dict(
            id=snapshot_tree.id,
            name=snapshot_tree.name
        )

    def _try_to_run_task(self, task_func, action, task_kwargs=None):
        """
        Attempt to run a task on the VM.

        This method will attempt to handle most task errors, and provide a better error message when possible.

        Args:
            task_func: The vSphere task function to run.
            action: The action being performed (e.g. "create", "update", "power off", "power on").
            task_kwargs: The keyword arguments to pass to the task function.

        Returns:
            The vSphere task result.
        """
        if task_kwargs is None:
            task_kwargs = dict()

        error_prefix = "Unable to %s VM." % action

        try:
            task = task_func(**task_kwargs)
            _, task_result = RunningTaskMonitor(task).wait_for_completion(  # pylint: disable=disallowed-name
                timeout=self.params['timeout']
            )
        except TaskError as e:
            self.module.fail_json(
                msg="%s %s" % (error_prefix, to_native(e)),
                error_code="TASK_ERROR",
                error_type=str(type(e.parent_error)),
                error_raw=to_native(e),
                exception=e.parent_error,
            )
        except (vmodl.RuntimeFault, vim.fault.VimFault) as e:
            self.module.fail_json(
                msg="%s %s" % (error_prefix, e.msg),
                error_code="VIM_FAULT",
                error_type=str(type(e)),
                error_raw=to_native(e),
            )

        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                datacenter=dict(type='str', aliases=['datacenter_name']),
                name=dict(type='str', required=False),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str', required=False),
                folder_paths_are_absolute=dict(type='bool', required=False, default=False),

                version=dict(type='str', required=True),
                allow_power_cycling=dict(type='bool', default=False),
                snapshot_before_upgrade=dict(type='bool', default=False),
                timeout=dict(type='int', default=600),
                ignore_downgrades=dict(type='bool', default=False),
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    vm_module = VmHardwareModule(module)
    result = dict(
        changed=False,
        power_cycled=False,
        vm=dict(
            moid=vm_module.vm._GetMoId(),
            name=vm_module.vm.name
        ),
        snapshot=dict()
    )

    desired_version = vm_module.get_desired_version()
    if vm_module.is_hw_change_needed(desired_version):
        needs_power_cycle = (vm_module.vm.summary.runtime.powerState.lower() != 'poweredoff')
        result['changed'] = True
        result['power_cycled'] = needs_power_cycle
        result['diff'] = {
            'before': {'version': str(vm_module.current_version)},
            'after': {'version': str(desired_version)}
        }

        if needs_power_cycle and not module.params['allow_power_cycling']:
            module.fail_json(
                "The VM must be powered off, or allow_power_cycling set to True, before upgrading hardware."
            )

        if not module.check_mode:
            if needs_power_cycle:
                vm_module._try_to_run_task(
                    task_func=vm_module.vm.PowerOffVM_Task,
                    action="power off"
                )

            result['snapshot'] = vm_module.snapshot_vm()
            vm_module.upgrade_vm(desired_version=desired_version)

            if needs_power_cycle:
                vm_module._try_to_run_task(
                    task_func=vm_module.vm.PowerOnVM_Task,
                    action="power on"
                )

    module.exit_json(**result)


if __name__ == '__main__':
    main()
