#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: esxi_powerstate
version_added: '2.10.0'
short_description: Manages power states of ESXi hosts in vCenter
description:
    - Manages power states of ESXi hosts, e.g., Shutdown / Reboot / Standby.
    - Unlike a virtual machine, an ESXi host cannot be powered on from a fully
      powered off state through the vSphere API. The V(powered-on) state can only
      bring a host out of a standby state, and requires the host to support a wake
      method such as DPM, IPMI, or Wake-on-LAN.
author:
    - Mike Morency (@mikemorency)

options:
    esxi_host_name:
        description:
            - Name of the ESXi host as defined in vCenter.
        required: true
        type: str
        aliases: ['name']
    state:
        description:
            - Set the power state of the ESXi host.
            - V(powered-off) shuts the host down.
            - V(restarted) reboots the host.
            - V(standby) puts the host into a standby (low power) state. Standby mode requires that the host
              supports power-management or wake methods, and is never supported on nested or virtual hosts.
            - V(powered-on) brings the host out of a standby state. It cannot power on a host
              that is fully powered off, and requires a supported wake method (DPM, IPMI, or Wake-on-LAN).
        choices: [ powered-off, powered-on, restarted, standby ]
        default: powered-on
        type: str
    force:
        description:
            - Ignore warnings and complete the actions.
            - When V(false), the V(powered-off) and V(restarted) operations are only
              performed if the host is already in maintenance mode.
            - When V(true), the operation is performed regardless of the host's maintenance mode.
        default: false
        type: bool
    evacuate_powered_off_vms:
        description:
            - If set to V(true), powered off virtual machines are evacuated from the host
              before entering the standby state.
            - Only used when O(state) is V(standby).
        default: false
        type: bool
    timeout:
        description:
            - The timeout, in seconds, to wait for the power state change to complete.
            - Also used as the time to wait for the host to enter or leave the standby state
              when O(state) is V(standby) or V(powered-on).
            - When O(state) is V(restarted), the module waits up to this long for the host to
              finish rebooting and reconnect to vCenter. When O(state) is V(powered-off), it
              waits up to this long for the host to report a powered off state.
        default: 600
        type: int
    scheduled_at:
        description:
            - Date and time in string format at which specified task needs to be performed.
            - "The required format for date and time - 'dd/mm/yyyy hh:mm'."
            - Scheduling a task requires vCenter server. A standalone ESXi server does not support this option.
        type: str
        required: false
    scheduled_task_name:
        description:
            - Name of scheduled task.
            - Valid only if O(scheduled_at) is specified.
            - If provided, the module reconciles against an existing scheduled task with this name on
              the host, so repeated runs are idempotent. A matching task is left unchanged, and a task
              that has drifted from the requested schedule or action is reconfigured.
            - If not provided, a random task name is generated on every run. Idempotency cannot be
              achieved in this case because there is no stable name to look the task up by, so a new
              scheduled task is created each time the module runs.
        type: str
        required: false
    scheduled_task_description:
        description:
            - Description of scheduled task.
            - Valid only if O(scheduled_at) is specified.
            - If not specified, newly created tasks are given an empty description.
        type: str
        required: false
    scheduled_task_enabled:
        description:
            - Flag to indicate whether the scheduled task is enabled or disabled.
            - Newly created scheduled tasks are enabled by default.
        type: bool
        required: false


extends_documentation_fragment:
    - vmware.vmware.base_options
"""

EXAMPLES = r"""
- name: Reboot an ESXi host
  vmware.vmware.esxi_powerstate:
    hostname: "{{ vcenter_hostname }}"
    username: "{{ vcenter_username }}"
    password: "{{ vcenter_password }}"
    name: "{{ esxi_host_name }}"
    state: restarted
    force: true

- name: Shutdown an ESXi host that is in maintenance mode
  vmware.vmware.esxi_powerstate:
    name: "{{ esxi_host_name }}"
    state: powered-off

- name: Put an ESXi host into standby and evacuate powered off VMs
  vmware.vmware.esxi_powerstate:
    name: "{{ esxi_host_name }}"
    state: standby
    evacuate_powered_off_vms: true

- name: Bring an ESXi host out of standby
  vmware.vmware.esxi_powerstate:
    name: "{{ esxi_host_name }}"
    state: powered-on

- name: Reboot an ESXi host at a given scheduled time
  vmware.vmware.esxi_powerstate:
    name: "{{ esxi_host_name }}"
    state: restarted
    force: true
    scheduled_at: "09/01/2026 10:18"
    scheduled_task_name: "task_00001"
    scheduled_task_description: "Sample task to reboot ESXi host"
    scheduled_task_enabled: true
"""

RETURN = r"""
host:
    description:
        - Identifying information about the ESXi host.
    returned: always
    type: dict
    sample: {
        "host": {
            "moid": "host-111111",
            "name": "10.10.10.10"
        },
    }
"""

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

import time
from random import randint
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_text, to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError,
    RunningTaskMonitor,
)

# Maps a desired power state to the WSDL method name vCenter stores/returns for a
# scheduled task's action. Used to compare an existing scheduled task's action against
# the desired action.
STATE_TO_SCHEDULED_METHOD_NAME = {
    "powered-off": "ShutdownHost_Task",
    "powered-on": "PowerUpHostFromStandBy_Task",
    "restarted": "RebootHost_Task",
    "standby": "PowerDownHostToStandBy_Task",
}

SCHEDULED_AT_TIME_FORMAT = "%d/%m/%Y %H:%M"


class EsxiPowerstateModule(ModulePyvmomiBase):
    def __init__(self, module):
        super(EsxiPowerstateModule, self).__init__(module)

        self.result = dict(changed=False, host=dict(name=None, moid=None))

        self.host = self.get_esxi_host_by_name_or_moid(
            identifier=self.params["esxi_host_name"], fail_on_missing=True
        )
        self.desired_state = (
            self.params["state"].replace("_", "").replace("-", "").lower()
        )
        self.current_state = self.host.runtime.powerState.lower()
        self.result["host"]["moid"] = self.host._GetMoId()
        self.result["host"]["name"] = self.host.name
        # Boot time captured before a reboot so we can confirm the host actually
        # rebooted (bootTime advances) rather than just that the task was accepted.
        self._boot_time_before_reboot = None

    def run_host_task(self, task):
        """
        Waits for a host power state task to complete and marks the result as changed.
        """
        if not task:
            return
        try:
            RunningTaskMonitor(task).wait_for_completion(timeout=self.params["timeout"])
        except TaskError as e:
            self.module.fail_json(msg=to_text(e))
        finally:
            self.result["changed"] = True

    def shutdown_host(self):
        return self.host.ShutdownHost_Task(self.params["force"])

    def reboot_host(self):
        # Record the current boot time so wait_for_reboot can confirm the host actually
        # went through a reboot cycle rather than just accepting the task.
        self._boot_time_before_reboot = getattr(self.host.runtime, "bootTime", None)
        return self.host.RebootHost_Task(self.params["force"])

    def _get_host_runtime(self):
        """
        Returns the host's live runtime info, or None if it cannot be read (for example
        while the host is briefly unreachable during a reboot).
        """
        try:
            return self.host.runtime
        except Exception:
            return None

    def wait_for_reboot(self):
        """
        Waits for the host to finish rebooting and reconnect to vCenter. Comparing
        bootTime avoids the race where the host still reports connected and powered on
        immediately after the reboot task is initiated.
        """
        deadline = time.time() + self.params["timeout"]
        while time.time() < deadline:
            runtime = self._get_host_runtime()
            if runtime is not None:
                current_boot = getattr(runtime, "bootTime", None)
                if (
                    str(runtime.connectionState) == "connected"
                    and str(runtime.powerState).lower() == "poweredon"
                    and current_boot is not None
                    and current_boot != self._boot_time_before_reboot
                ):
                    return
            time.sleep(5)

        self.module.fail_json(
            msg="Timed out after %d seconds waiting for host %s to finish rebooting "
            "and reconnect" % (self.params["timeout"], self.host.name)
        )

    def wait_for_powered_off(self):
        """
        Waits for the host to report a powered off state after a shutdown.
        """
        deadline = time.time() + self.params["timeout"]
        while time.time() < deadline:
            runtime = self._get_host_runtime()
            if runtime is not None and str(runtime.powerState).lower() in ("poweredoff", "unknown"):
                return
            time.sleep(5)

        self.module.fail_json(
            msg="Timed out after %d seconds waiting for host %s to power off"
            % (self.params["timeout"], self.host.name)
        )

    def standby_host(self):
        return self.host.PowerDownHostToStandBy_Task(
            self.params["timeout"], self.params["evacuate_powered_off_vms"]
        )

    def power_up_host(self):
        if self.current_state == "poweredoff":
            self.module.fail_json(
                msg="Cannot power on ESXi host %s because it is fully powered off. The API can only "
                "power a host up from a standby state." % self.host.name
            )
        return self.host.PowerUpHostFromStandBy_Task(self.params["timeout"])

    def set_host_powerstate(self):
        """
        Set the power state for the ESXi host determined by the requested state.
        """
        desired_powerstate = {
            "poweredoff": self.shutdown_host,
            "poweredon": self.power_up_host,
            "restarted": self.reboot_host,
            "standby": self.standby_host,
        }
        try:
            if self.desired_state in desired_powerstate:
                task = desired_powerstate[self.desired_state]()
            else:
                self.module.fail_json(
                    msg="Unsupported expected state provided: %s" % self.desired_state
                )
        except Exception as e:
            self.module.fail_json(msg=to_text(e))

        self.run_host_task(task)

        # The task only reports that the operation was initiated. Wait for the host to
        # actually reach the requested state so callers can rely on it afterwards.
        if self.desired_state == "restarted":
            self.wait_for_reboot()
        elif self.desired_state == "poweredoff":
            self.wait_for_powered_off()

    def configure_host_scheduled_powerstate(self, scheduled_at):
        """
        Configures an ESXi host power state when the scheduled task option is set.
        When the user supplied an explicit task name, an existing task with that name is
        reconciled so repeated runs are idempotent. A matching task is left unchanged and a
        drifted task is reconfigured. Without an explicit name the task name is randomly
        generated and a new task is always created.
        This path computes the diff using read-only calls, so it honors check mode itself:
        the change is detected but no scheduled task is created or reconfigured.
        """
        if not self.is_vcenter():
            self.module.fail_json(
                msg="Scheduling task requires vCenter, hostname %s "
                "is an ESXi server." % self.params.get("hostname")
            )
        scheduled_date = self._parse_scheduled_date(scheduled_at)

        existing_task = None
        if self.params.get("scheduled_task_name"):
            existing_task = self.get_existing_scheduled_task(
                self.params["scheduled_task_name"]
            )

        if existing_task is not None and self.scheduled_task_matches(
            existing_task, scheduled_date
        ):
            self.result["changed"] = False
            return

        # A create or reconfigure is required.
        self.result["changed"] = True
        if self.module.check_mode:
            return

        if existing_task is not None:
            spec = self.build_scheduled_task_spec(
                scheduled_date, existing_task=existing_task
            )
            self.reconfigure_scheduled_task(existing_task, spec)
        else:
            spec = self.build_scheduled_task_spec(scheduled_date, existing_task=None)
            self.create_scheduled_task(spec)

    def _parse_scheduled_date(self, scheduled_at):
        try:
            return datetime.strptime(scheduled_at, SCHEDULED_AT_TIME_FORMAT)
        except ValueError as e:
            self.module.fail_json(
                msg="Failed to convert given date and time string to Python datetime object,"
                "please specify string in 'dd/mm/yyyy hh:mm' format: %s" % to_native(e)
            )

    def build_scheduled_task_spec(self, scheduled_date, existing_task=None):
        """
        Builds the ScheduledTaskSpec for a create or reconfigure.
        The API requires C(description) and C(enabled). When the user did not specify them,
        an existing task's values are carried forward on reconfigure, otherwise create
        defaults are used (empty description, enabled).
        Returns:
            ScheduledTaskSpec
        """
        powerstate = {
            "powered-off": vim.HostSystem.ShutdownHost_Task,
            "powered-on": vim.HostSystem.PowerUpHostFromStandBy_Task,
            "restarted": vim.HostSystem.RebootHost_Task,
            "standby": vim.HostSystem.PowerDownHostToStandBy_Task,
        }
        spec = vim.scheduler.ScheduledTaskSpec()
        spec.name = self.params["scheduled_task_name"] or "task_%s" % str(
            randint(10000, 99999)  # NOSONAR - task name uniqueness only, not a security context
        )
        spec.scheduler = vim.scheduler.OnceTaskScheduler()
        spec.scheduler.runAt = scheduled_date
        spec.action = vim.action.MethodAction()
        spec.action.name = powerstate[self.params["state"]]

        # description and enabled are required by the API. Prefer the user's value, then the
        # existing task's value (reconfigure), then a create default.
        if self.params["scheduled_task_description"] is not None:
            spec.description = self.params["scheduled_task_description"]
        elif existing_task is not None:
            spec.description = existing_task.info.description or ""
        else:
            spec.description = ""

        if self.params["scheduled_task_enabled"] is not None:
            spec.enabled = self.params["scheduled_task_enabled"]
        elif existing_task is not None:
            spec.enabled = existing_task.info.enabled
        else:
            spec.enabled = True

        return spec

    def get_existing_scheduled_task(self, name):
        """
        Returns the scheduled task attached to the host with the given name, or None if
        no such task exists.
        """
        try:
            existing_tasks = (
                self.content.scheduledTaskManager.RetrieveEntityScheduledTask(self.host)
            )
        except (vmodl.RuntimeFault, vmodl.MethodFault) as e:
            self.module.fail_json(
                msg="Failed to retrieve scheduled tasks for host %s: %s"
                % (self.host.name, to_native(getattr(e, "msg", e)))
            )
        for task in existing_tasks or []:
            if task.info.name == name:
                return task
        return None

    @staticmethod
    def _method_short_name(method_action):
        """
        Normalizes a MethodAction returned by vCenter into its short method name for
        comparison. vCenter returns the action as a (possibly namespaced) string, e.g.
        C(ShutdownHost_Task).
        """
        value = getattr(method_action, "name", method_action)
        return str(value).rsplit('.', maxsplit=1)[-1]

    def scheduled_task_matches(self, existing_task, scheduled_date):
        """
        Compares an existing scheduled task against the requested schedule on the fields the
        module manages (action and run time, plus enabled and description when the user
        specified them). Fields the user did not specify are not compared.
        Returns:
            bool, True if the existing task already matches what was requested.
        """
        info = existing_task.info
        # enabled has no default, so only compare it when the user specified it.
        if self.params["scheduled_task_enabled"] is not None:
            if bool(info.enabled) != bool(self.params["scheduled_task_enabled"]):
                return False
        # description has no default, so only compare it when the user specified one.
        if self.params["scheduled_task_description"] is not None:
            if (info.description or None) != self.params["scheduled_task_description"]:
                return False
        if (
            self._method_short_name(info.action)
            != STATE_TO_SCHEDULED_METHOD_NAME[self.params["state"]]
        ):
            return False
        existing_runat = getattr(info.scheduler, "runAt", None)
        if existing_runat is None:
            return False
        if existing_runat.tzinfo is not None:
            existing_runat = existing_runat.replace(tzinfo=None)
        return existing_runat.strftime(SCHEDULED_AT_TIME_FORMAT) == scheduled_date.strftime(
            SCHEDULED_AT_TIME_FORMAT
        )

    def reconfigure_scheduled_task(self, existing_task, scheduled_task_spec):
        """
        Updates an existing scheduled task so it matches the desired spec.
        """
        try:
            existing_task.ReconfigureScheduledTask(scheduled_task_spec)
            self.result["changed"] = True
        except (
            vim.fault.InvalidName,
            vim.fault.DuplicateName,
            vmodl.fault.InvalidArgument,
        ) as e:
            self.module.fail_json(
                msg="Failed to reconfigure scheduled task %s for %s: %s"
                % (
                    self.params.get("state"),
                    self.host.name,
                    to_native(getattr(e, "msg", e)),
                )
            )

    def create_scheduled_task(self, scheduled_task_spec):
        """
        Creates a new scheduled task for the host power state operation.
        """
        try:
            self.content.scheduledTaskManager.CreateScheduledTask(
                self.host, scheduled_task_spec
            )
            # As this is an async task, we create the scheduled task and mark state as changed.
            self.result["changed"] = True
        except vim.fault.InvalidName as e:
            self.module.fail_json(
                msg="Failed to create scheduled task %s for %s : %s"
                % (self.params.get("state"), self.host.name, to_native(e.msg))
            )
        except vim.fault.DuplicateName as e:
            self.module.fail_json(
                msg="Failed to create scheduled task %s as specified task "
                "name is invalid: %s" % (self.params.get("state"), to_native(e.msg))
            )
        except vmodl.fault.InvalidArgument as e:
            err_msg = (
                "Failed to create scheduled task %s as specifications given are invalid: "
                % self.params.get("state")
            )
            if scheduled_task_spec.scheduler.runAt < datetime.now():
                err_msg += "the specified time has already passed"
            else:
                err_msg += to_native(e.msg)
            self.module.fail_json(msg=err_msg)


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(),
            **dict(
                esxi_host_name=dict(type="str", required=True, aliases=["name"]),
                state=dict(
                    type="str",
                    default="powered-on",
                    choices=["powered-off", "powered-on", "restarted", "standby"],
                ),
                force=dict(type="bool", default=False),
                evacuate_powered_off_vms=dict(type="bool", default=False),
                timeout=dict(type="int", default=600),
                scheduled_at=dict(type="str", required=False),
                scheduled_task_name=dict(type="str", required=False),
                scheduled_task_description=dict(type="str", required=False),
                scheduled_task_enabled=dict(type="bool", required=False),
            ),
        },
        supports_check_mode=True,
    )

    esxi_powerstate = EsxiPowerstateModule(module)

    if esxi_powerstate.params.get("scheduled_at"):
        # The scheduled task path diffs against any existing task and honors check mode itself.
        esxi_powerstate.configure_host_scheduled_powerstate(
            esxi_powerstate.params["scheduled_at"]
        )
        module.exit_json(**esxi_powerstate.result)

    # Immediate power action. If the host is already in the desired state, nothing to do.
    if esxi_powerstate.current_state == esxi_powerstate.desired_state:
        module.exit_json(**esxi_powerstate.result)

    if module.check_mode:
        esxi_powerstate.result["changed"] = True
        module.exit_json(**esxi_powerstate.result)

    esxi_powerstate.set_host_powerstate()

    module.exit_json(**esxi_powerstate.result)


if __name__ == "__main__":
    main()
