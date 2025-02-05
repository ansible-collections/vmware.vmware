#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vmware_guest_powerstate
short_description: Manages power states of virtual machines in vCenter
description:
    - Manages power states of virtual machines in vCenter, e.g., Power on / Power off / Restart.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    datacenter:
        description:
            - The datacenter where the VM you'd like to operate the power.
        type: str
        required: true
    state:
        description:
            - Set the state of the virtual machine.
        choices: [ powered-off, powered-on, reboot-guest, restarted, shutdown-guest, suspended, present]
        default: present
        type: str
    name:
        description:
            - Name of the virtual machine to work with.
            - Virtual machine names in vCenter are not necessarily unique, which may be problematic, see O(name_match).
            - This is required if O(moid) or O(uuid) is not supplied.
        type: str
    name_match:
        description:
            - If multiple virtual machines matching the name, use the first or last found.
        default: first
        choices: [ first, last ]
        type: str
    uuid:
        description:
            - UUID of the instance to manage if known, this is VMware's unique identifier.
            - This is required if O(name) or O(moid) is not supplied.
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
            - The folder should include the datacenter. ESX's datacenter is ha-datacenter
            - 'Examples:'
            - '   folder: /ha-datacenter/vm'
            - '   folder: ha-datacenter/vm'
            - '   folder: /datacenter1/vm'
            - '   folder: datacenter1/vm'
            - '   folder: /datacenter1/vm/folder1'
            - '   folder: datacenter1/vm/folder1'
            - '   folder: /folder1/datacenter1/vm'
            - '   folder: folder1/datacenter1/vm'
            - '   folder: /folder1/datacenter1/vm/folder2'
        type: str
        required: false
    scheduled_at:
        description:
            - Date and time in string format at which specified task needs to be performed.
            - "The required format for date and time - 'dd/mm/yyyy hh:mm'."
            - Scheduling task requires vCenter server. A standalone ESXi server does not support this option.
        type: str
        required: false
    schedule_task_name:
        description:
            - Name of schedule task.
            - Valid only if O(scheduled_at) is specified.
        type: str
        required: false
    schedule_task_description:
        description:
            - Description of schedule task.
            - Valid only if O(scheduled_at) is specified.
        type: str
        required: false
    schedule_task_enabled:
        description:
            - Flag to indicate whether the scheduled task is enabled or disabled.
        type: bool
        default: true
    force:
        description:
            - Ignore warnings and complete the actions.
            - This parameter is useful while forcing virtual machine state.
        default: false
        type: bool
    state_change_timeout:
        description:
            - If the O(state=shutdown-guest), by default the module will return immediately after sending the shutdown signal.
            - If this argument is set to a positive integer, the module will instead wait for the VM to reach the poweredoff state.
            - The value sets a timeout in seconds for the module to wait for the state change.
        default: 0
        type: int
    answer:
        description:
            - A list of questions to answer, should one or more arise while waiting for the task to complete.
            - Some common uses are to allow a cdrom to be changed even if locked, or to answer the question as to whether a VM was copied or moved.
            - Can be used if O(state=powered-on).
        suboptions:
            question:
                description:
                    - The message id, for example C(msg.uuid.altered).
                type: str
                required: true
            response:
                description:
                    - The choice key, for example C(button.uuid.copiedTheVM).
                type: str
                required: true
        type: list
        elements: dict
        required: false


extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Set the state of a virtual machine to poweroff
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    name: "{{ guest_name }}"
    state: powered-off
  register: deploy

- name: Set the state of a virtual machine to poweron using MoID
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    moid: vm-42
    state: powered-on
  register: deploy

- name: Set the state of a virtual machine to poweroff at given scheduled time
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    name: "{{ guest_name }}"
    state: powered-off
    scheduled_at: "09/01/2018 10:18"
    schedule_task_name: "task_00001"
    schedule_task_description: "Sample task to poweroff VM"
    schedule_task_enabled: true
  register: deploy_at_schedule_datetime

- name: Wait for the virtual machine to shutdown
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    name: "{{ guest_name }}"
    state: shutdown-guest
    state_change_timeout: 200
  register: deploy

- name: Automatically answer if a question locked a virtual machine
  block:
    - name: Power on a virtual machine without the answer param
      community.vmware.vmware_guest_powerstate:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        validate_certs: false
        folder: "{{ f1 }}"
        name: "{{ vm_name }}"
        state: powered-on
  rescue:
    - name: Power on a virtual machine with the answer param
      community.vmware.vmware_guest_powerstate:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        validate_certs: false
        folder: "{{ f1 }}"
        name: "{{ vm_name }}"
        answer:
          - question: "msg.uuid.altered"
            response: "button.uuid.copiedTheVM"
        state: powered-on
'''

RETURN = r''' # '''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from random import randint
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.vmware.plugins.module_utils import vmware
from ansible.module_utils._text import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)


class VmwareGuestPowerstateModule(ModulePyvmomiBase):
    def __init__(self, module):
        super(VmwareGuestPowerstateModule, self).__init__(module)

        self.result = dict(changed=False)

    def get_vm(self):
        """
        Finds and gets VM according to the specified name/uuid/moid
        Returns:
            tuple, vm object and PyVmomi object if found 
        """
        if self.module.params['folder']:
            self.module.params['folder'] = self.module.params['folder'].rstrip('/')

        pyv = vmware.PyVmomi(self.module)

        vm = pyv.get_vm()

        if not vm:
            id = self.module.params.get('uuid') or self.module.params.get('moid') or self.module.params.get('name')
            self.module.fail_json(msg="Unable to set power state for non-existing virtual machine : '%s'" % id)

        return (vm, pyv)

    def configure_vm_powerstate(self, vm, pyv):
        """
        Configures a VMs powerstate
        """
        if not self.current_state_matches_desired_state(vm, pyv):  
            scheduled_at = self.module.params.get('scheduled_at', None)
            if scheduled_at:
                self.configure_vm_scheduled_powerstate(vm, pyv, scheduled_at)
            else:
                # Check if a virtual machine is locked by a question
                if vmware.check_answer_question_status(vm) and self.module.params['answer']:
                    self.configure_vm_answerable_powerstate(vm)
                else:
                    self.result = vmware.set_vm_power_state(pyv.content, vm, self.module.params['state'], self.module.params['force'], self.module.params['state_change_timeout'],
                                                self.module.params['answer'])
                self.result['answer'] = self.module.params['answer']
        
        self.result['moid'] = vm._GetMoId()
        self.result['name'] = vm.name
        self.result['instance'] = vmware.gather_vm_facts(pyv.content, vm)

    def configure_vm_scheduled_powerstate(self, vm, pyv, scheduled_at):
        """
        Configures a VM powerstate when scheduled task option is set
        """
        if not pyv.is_vcenter():
            self.module.fail_json(msg="Scheduling task requires vCenter, hostname %s "
                                "is an ESXi server." % self.module.params.get('hostname'))
        powerstate = {
            'present': vim.VirtualMachine.PowerOn,
            'powered-off': vim.VirtualMachine.PowerOff,
            'powered-on': vim.VirtualMachine.PowerOn,
            'reboot-guest': vim.VirtualMachine.RebootGuest,
            'restarted': vim.VirtualMachine.Reset,
            'shutdown-guest': vim.VirtualMachine.ShutdownGuest,
            'suspended': vim.VirtualMachine.Suspend,
        }
        try:
            scheduled_date = datetime.strptime(scheduled_at, '%d/%m/%Y %H:%M')
        except ValueError as e:
            self.module.fail_json(msg="Failed to convert given date and time string to Python datetime object,"
                                "please specify string in 'dd/mm/yyyy hh:mm' format: %s" % to_native(e))
        schedule_task_spec = vim.scheduler.ScheduledTaskSpec()
        schedule_task_spec.name = self.module.params['schedule_task_name'] or 'task_%s' % str(randint(10000, 99999))
        schedule_task_spec.description = self.module.params['schedule_task_description'] or 'Schedule task for vm %s for ' \
                                                'operation %s at %s' % (vm.name, self.module.params['state'], scheduled_at)
        schedule_task_spec.scheduler = vim.scheduler.OnceTaskScheduler()
        schedule_task_spec.scheduler.runAt = scheduled_date
        schedule_task_spec.action = vim.action.MethodAction()
        schedule_task_spec.action.name = powerstate[self.module.params['state']]
        schedule_task_spec.enabled = self.module.params['schedule_task_enabled']

        try:
            pyv.content.scheduledTaskManager.CreateScheduledTask(vm, schedule_task_spec)
            # As this is async task, we create scheduled task and mark state to changed.
            self.result['changed'] = True
        except vim.fault.InvalidName as e:
            self.module.fail_json(msg="Failed to create scheduled task %s for %s : %s" % (self.module.params.get('state'),
                                                                                    vm.name,
                                                                                    to_native(e.msg)))
        except vim.fault.DuplicateName as e:
            self.module.fail_json(msg="Failed to create scheduled task %s as specified task "
                                "name is invalid: %s" % (self.module.params.get('state'),
                                                            to_native(e.msg)))
        except vmodl.fault.InvalidArgument as e:
            self.module.fail_json(msg="Failed to create scheduled task %s as specifications "
                                "given are invalid: %s" % (self.module.params.get('state'),
                                                            to_native(e.msg)))
            
    def configure_vm_answerable_powerstate(self, vm):
        """
        Configures a VM powerstate when answer option is set
        """
        try:
            responses = vmware.make_answer_response(vm, self.module.params['answer'])
            vmware.answer_question(vm, responses)
        except Exception as e:
            self.module.fail_json(msg="%s" % e)

        # Wait until a virtual machine is unlocked
        while True:
            if vmware.check_answer_question_status(vm) is False:
                break

        self.result['changed'] = True
    
    def current_state_matches_desired_state(self, vm, pyv):
        """
        Checks the hosts current power state and compares it to the desired power state setting.
        Returns:
            bool, true if they match, otherwise false
        """
        facts = vmware.gather_vm_facts(pyv.content, vm)
        state = self.module.params['state']
        if state == 'present':
            state = 'poweredon'
        desired_state = state.replace('_', '').replace('-', '').lower()
        current_state = facts['hw_power_status'].lower()

        if current_state == desired_state:
            return True
        
        return False


def main():
    argument_spec = vmware.vmware_argument_spec()
    argument_spec.update(
        datacenter=dict(type='str', required=True),
        state=dict(type='str', default='present',
                   choices=['present', 'powered-off', 'powered-on', 'reboot-guest', 'restarted', 'shutdown-guest', 'suspended']),
        name=dict(type='str'),
        name_match=dict(type='str', choices=['first', 'last'], default='first'),
        uuid=dict(type='str'),
        moid=dict(type='str'),
        use_instance_uuid=dict(type='bool', default=False),
        folder=dict(type='str', required=False),
        force=dict(type='bool', default=False),
        scheduled_at=dict(type='str', required=False),
        schedule_task_name=dict(type='str', required=False),
        schedule_task_description=dict(type='str', required=False),
        schedule_task_enabled=dict(type='bool', default=True),
        state_change_timeout=dict(type='int', default=0),
        answer=dict(type='list',
                    required=False,
                    elements='dict',
                    options=dict(
                        question=dict(type='str', required=True),
                        response=dict(type='str', required=True)
                    ))
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False,
        mutually_exclusive=[
            ['name', 'uuid', 'moid'],
            ['scheduled_at', 'answer']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    vmware_guest_powerstate = VmwareGuestPowerstateModule(module)
    vm, pyv = vmware_guest_powerstate.get_vm()
    vmware_guest_powerstate.configure_vm_powerstate(vm, pyv)
    result = vmware_guest_powerstate.result
    
    if result.get('failed') is True:
        module.fail_json(**result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()