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
        choices: [ powered-off, powered-on, reboot-guest, restarted, shutdown-guest, suspended]
        default: powered-on
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
            - Should be the full folder path, with or without the 'datacenter/vm/' prefix
            - For example 'datacenter name/vm/path/to/folder' or 'path/to/folder'
        type: str
        required: false
    scheduled_at:
        description:
            - Date and time in string format at which specified task needs to be performed.
            - "The required format for date and time - 'dd/mm/yyyy hh:mm'."
            - Scheduling task requires vCenter server. A standalone ESXi server does not support this option.
        type: str
        required: false
    scheduled_task_name:
        description:
            - Name of scheduled task.
            - Valid only if O(scheduled_at) is specified.
        type: str
        required: false
    scheduled_task_description:
        description:
            - Description of scheduled task.
            - Valid only if O(scheduled_at) is specified.
        type: str
        required: false
    scheduled_task_enabled:
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
    timeout:
        description:
            - If the O(state) is V(shutdown-guest), by default the module will return immediately after sending the shutdown signal.
            - If this argument is set to a positive integer, the module will instead wait for the VM to reach the poweredoff state.
            - The value sets a timeout in seconds for the module to wait for the state change.
        default: 0
        type: int
    question_answers:
        description:
            - A list of questions to answer, should one or more arise while waiting for the task to complete.
            - Some common uses are to allow a cdrom to be changed even if locked, or to answer the question as to whether a VM was copied or moved.
            - Can be used if O(state) is V(powered-on).
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
    datacenter: "{{ vm_datacenter }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    name: "{{ guest_name }}"
    state: powered-off
  register: deploy

- name: Set the state of a virtual machine to poweron using MoID
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: "{{ vm_datacenter }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    moid: vm-42
    state: powered-on
  register: deploy

- name: Set the state of a virtual machine to poweroff at given scheduled time
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: "{{ vm_datacenter }}"
    folder: "/{{ datacenter_name }}/vm/my_folder"
    name: "{{ guest_name }}"
    state: powered-off
    scheduled_at: "09/01/2018 10:18"
    scheduled_task_name: "task_00001"
    scheduled_task_description: "Sample task to poweroff VM"
    scheduled_task_enabled: true
  register: deploy_at_scheduled_datetime

- name: Wait for the virtual machine to shutdown
  community.vmware.vmware_guest_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    datacenter: "{{ vm_datacenter }}"
    name: "{{ guest_name }}"
    state: shutdown-guest
    timeout: 200
  register: deploy

- name: Automatically answer if a question locked a virtual machine
  block:
    - name: Power on a virtual machine without the answer param
      vmware.vmware.vmware_guest_powerstate:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        datacenter: "{{ vm_datacenter }}"
        validate_certs: false
        folder: "{{ f1 }}"
        name: "{{ vm_name }}"
        state: powered-on
  rescue:
    - name: Power on a virtual machine with the answer param
      vmware.vmware.vmware_guest_powerstate:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        datacenter: "{{ vm_datacenter }}"
        validate_certs: false
        folder: "{{ f1 }}"
        name: "{{ vm_name }}"
        question_answers:
          - question: "msg.uuid.altered"
            response: "button.uuid.copiedTheVM"
        state: powered-on
'''

RETURN = r'''
result:
    description:
        - Information about the target VM 
    returned: On success
    type: dict
    sample: {
        "changed": true,
        "failed": false,
        "vm": {
            "moid": "vm-79828",
            "name": "test-d9c1-vm"
        }
    }
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

import time
from random import randint
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.vmware.plugins.module_utils import vmware
from ansible.module_utils._text import to_text, to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import format_folder_path_as_vm_fq_path
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import TaskError, RunningTaskMonitor


class VmwareGuestPowerstateModule(ModulePyvmomiBase):
    def __init__(self, module):
        super(VmwareGuestPowerstateModule, self).__init__(module)

        self.result = dict(
            changed=False,
            vm=dict(
                name=None,
                moid=None
            ),
            result={}
        )

    def standardize_folder_param(self):
        """
        Removes all "/" characters in the folder path if the folder param exists
        """
        if self.module.params['folder']:
            self.module.params['folder'] = format_folder_path_as_vm_fq_path(
                self.module.params['folder'],
                self.module.params['datacenter']
            )

    def get_vm(self):
        """
        Finds and gets VM according to the specified name/uuid/moid
        Returns:
            first vm object found or None if no matches were found 
        """
        vm_list = self.get_vm_using_params(fail_on_missing=True)
        return vm_list[0]
    
    def make_answer_response(vm, answers):
        """
        Make the response contents to answer against locked a virtual machine.
        Returns:
            Dict with answer id and number
        Raises:
            TaskError on failure
        """
        response_list = {}
        for message in vm.runtime.question.message:
            response_list[message.id] = {}
            for choice in vm.runtime.question.choice.choiceInfo:
                response_list[message.id].update({
                    choice.label: choice.key
                })

        responses = []
        try:
            for answer in answers:
                responses.append({
                    "id": vm.runtime.question.id,
                    "response_num": response_list[answer["question"]][answer["response"]]
                })
        except Exception:
            raise TaskError("not found %s or %s or both in the response list" % (answer["question"], answer["response"]))

        return responses
    
    def answer_question(vm, responses):
        """
        Answer against the question for unlocking a virtual machine.
        """
        for response in responses:
            try:
                vm.AnswerVM(response["id"], response["response_num"])
            except Exception as e:
                raise TaskError("answer failed: %s" % to_text(e))

    def wait_for_poweroff(self, vm, timeout=300):
        interval = 15
        while timeout > 0:
            if vm.runtime.powerState.lower() == 'poweredoff':
                break
            time.sleep(interval)
            timeout -= interval
        else:
            self.result['failed'] = True
            self.result['msg'] = 'Timeout while waiting for VM power off.'

    def set_vm_powerstate(self, vm, force, timeout=0, answers=None):
        """
        Set the power status for a VM determined by the current and
        requested states. force is forceful
        """
        current_state, desired_state = self.get_current_and_desired_states(vm)

        # Need Force
        if not force and current_state not in ['poweredon', 'poweredoff']:
            self.result['failed'] = True
            self.result['msg'] = "Virtual Machine is in %s power state. Force is required!" % current_state
            self.result['result'] = vm.summary

        # State is not already true
        if current_state != desired_state:
            task = None
            try:
                if desired_state == 'poweredoff':
                    task = vm.PowerOff()

                elif desired_state == 'poweredon':
                    task = vm.PowerOn()

                elif desired_state == 'restarted':
                    if current_state in ('poweredon', 'poweringon', 'resetting', 'poweredoff'):
                        task = vm.Reset()
                    else:
                        self.result['failed'] = True
                        self.result['msg'] = "Cannot restart virtual machine in the current state %s" % current_state

                elif desired_state == 'suspended':
                    if current_state in ('poweredon', 'poweringon'):
                        task = vm.Suspend()
                    else:
                        self.result['failed'] = True
                        self.result['msg'] = 'Cannot suspend virtual machine in the current state %s' % current_state

                elif desired_state in ['shutdownguest', 'rebootguest']:
                    if current_state == 'poweredon':
                        if vm.guest.toolsRunningStatus == 'guestToolsRunning':
                            if desired_state == 'shutdownguest':
                                task = vm.ShutdownGuest()
                                if timeout > 0:
                                    self.result.update(self.wait_for_poweroff(vm, timeout))
                            else:
                                task = vm.RebootGuest()
                            # Set result['changed'] immediately because
                            # shutdown and reboot return None.
                            self.result['changed'] = True
                        else:
                            self.result['failed'] = True
                            self.result['msg'] = "VMware tools should be installed for guest shutdown/reboot"
                    elif current_state == 'poweredoff':
                        self.result['changed'] = False
                    else:
                        self.result['failed'] = True
                        self.result['msg'] = "Virtual machine %s must be in poweredon state for guest reboot" % vm.name

                else:
                    self.result['failed'] = True
                    self.result['msg'] = "Unsupported expected state provided: %s" % desired_state

            except Exception as e:
                self.result['failed'] = True
                self.result['msg'] = to_text(e)

            if task:
                try:
                    _, task_result = RunningTaskMonitor(task).wait_for_completion()
                except TaskError as e:
                    self.result['failed'] = True
                    self.result['msg'] = to_text(e)
                finally:
                    if task.info.state == 'error':
                        self.result['failed'] = True
                        self.result['msg'] = task.info.error.msg
                    else:
                        self.result['changed'] = True
                        self.result['result'] = task.info

        self.result['result'] = vm.summary

    def configure_vm_powerstate(self, vm):
        """
        Configures a VMs powerstate
        """
        scheduled_at = self.module.params.get('scheduled_at', None)
        if scheduled_at:
            scheduled_task_spec = self.configure_scheduled_task_spec(scheduled_at)
            self.configure_vm_scheduled_powerstate(vm, scheduled_task_spec)
        else:
            # Check if a virtual machine is locked by a question
            if hasattr(vm, "runtime") and vm.runtime.question and self.module.params['question_answers']:
                self.configure_vm_answerable_powerstate(vm)
            else:
                self.set_vm_powerstate(vm, self.module.params['force'], self.module.params['timeout'], self.module.params['question_answers'])
        
        self.result["vm"]['moid'] = vm._GetMoId()
        self.result["vm"]['name'] = vm.name

    def configure_scheduled_task_spec(self, scheduled_at):
        """
        Reurns:
            ScheduledTaskSpec, object that contains all specifications regarding the scheduled task
        """
        if not self.is_vcenter():
            self.module.fail_json(msg="Scheduling task requires vCenter, hostname %s "
                                "is an ESXi server." % self.module.params.get('hostname'))
        powerstate = {
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
        scheduled_task_spec = vim.scheduler.ScheduledTaskSpec()
        scheduled_task_spec.name = self.module.params['scheduled_task_name'] or 'task_%s' % str(randint(10000, 99999))
        scheduled_task_spec.description = self.module.params['scheduled_task_description'] or 'Scheduled task for vm %s for ' \
                                                'operation %s at %s' % (vm.name, self.module.params['state'], scheduled_at)
        scheduled_task_spec.scheduler = vim.scheduler.OnceTaskScheduler()
        scheduled_task_spec.scheduler.runAt = scheduled_date
        scheduled_task_spec.action = vim.action.MethodAction()
        scheduled_task_spec.action.name = powerstate[self.module.params['state']]
        scheduled_task_spec.enabled = self.module.params['scheduled_task_enabled']

        return scheduled_task_spec


    def configure_vm_scheduled_powerstate(self, vm, scheduled_task_spec):
        """
        Configures a VM powerstate when scheduled task option is set
        """
        try:
            self.content.scheduledTaskManager.CreateScheduledTask(vm, scheduled_task_spec)
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
        Configures a VM powerstate when question_answers option is set
        """
        try:
            responses = vmware.make_answer_response(vm, self.module.params['question_answers'])
            vmware.answer_question(vm, responses)
        except Exception as e:
            self.module.fail_json(msg="%s" % e)

        # Wait until a virtual machine is unlocked
        while True:
            if vmware.check_answer_question_status(vm) is False:
                break

        self.result['changed'] = True
    
    def current_state_matches_desired_state(self, vm):
        """
        Checks the hosts current power state and compares it to the desired power state setting.
        Returns:
            bool, true if they match, otherwise false
        """
        current_state, desired_state = self.get_current_and_desired_states(vm)

        if current_state == desired_state:
            return True
        
        return False
    
    def get_current_and_desired_states(self, vm):
        state = self.module.params['state']
        desired_state = state.replace('_', '').replace('-', '').lower()
        current_state = vm.summary.runtime.powerState.lower()

        return current_state, desired_state


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                datacenter=dict(type='str', required=True),
                state=dict(type='str', default='powered-on',
                        choices=['powered-off', 'powered-on', 'reboot-guest', 'restarted', 'shutdown-guest', 'suspended']),
                name=dict(type='str'),
                name_match=dict(type='str', choices=['first', 'last'], default='first'),
                uuid=dict(type='str'),
                moid=dict(type='str'),
                use_instance_uuid=dict(type='bool', default=False),
                folder=dict(type='str', required=False),
                force=dict(type='bool', default=False),
                scheduled_at=dict(type='str', required=False),
                scheduled_task_name=dict(type='str', required=False),
                scheduled_task_description=dict(type='str', required=False),
                scheduled_task_enabled=dict(type='bool', default=True),
                timeout=dict(type='int', default=0),
                question_answers=dict(type='list',
                            required=False,
                            elements='dict',
                            options=dict(
                                question=dict(type='str', required=True),
                                response=dict(type='str', required=True)
                            ))
            )
        },
        supports_check_mode=True,
        mutually_exclusive=[
            ['name', 'uuid', 'moid'],
            ['scheduled_at', 'question_answers']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
    )

    result = dict(
        changed=False,
        result={}
    )

    vmware_guest_powerstate = VmwareGuestPowerstateModule(module)
    vmware_guest_powerstate.standardize_folder_param()
    vm = vmware_guest_powerstate.get_vm()
    if vmware_guest_powerstate.current_state_matches_desired_state(vm):
        module.exit_json(**result)

    if module.check_mode:
        result['changed'] = True
        module.exit_json(**result)
    
    vmware_guest_powerstate.configure_vm_powerstate(vm)
    result = vmware_guest_powerstate.result
    module.fail_json(msg="%s" % result)
    
    if hasattr(result, "failed") and result.get('failed') is True:
        module.fail_json(**result)

    module.exit_json(**result)


if __name__ == '__main__':
    main()