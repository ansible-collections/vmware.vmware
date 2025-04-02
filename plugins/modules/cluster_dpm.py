#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: cluster_dpm
short_description: Manage Distributed Power Management (DPM) on VMware vSphere clusters
description:
    - Manages DPM on VMware vSphere clusters.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    cluster:
        description:
            - The name of the cluster to be managed.
        type: str
        required: true
        aliases: [ cluster_name ]
    datacenter:
        description:
            - The name of the datacenter.
        type: str
        required: true
        aliases: [ datacenter_name ]
    enable:
        description:
            - Whether to enable DPM.
        type: bool
        default: true
    automation_level:
        description:
            - Determines whether the host power state and migration recommendations generated by vSphere DPM are run
                automatically or manually.
            - If set to V(manual), then vCenter generates host power operation and related virtual machine
                migration recommendations are made, but they are not automatically run.
            - If set to V(automatic), then vCenter host power operations are automatically run if
                related virtual machine migrations can all be run automatically.
        type: str
        default: automatic
        choices: [ automatic, manual ]
    recommendation_priority_threshold:
        description:
            - Threshold for generated host power recommendations ranging from V(1) (most conservative) to V(5) (most aggressive).
            - The power state (host power on or off) recommendations generated by the vSphere DPM feature
                are assigned priorities that range from priority V(1) recommendations to priority V(5) recommendations.
            - A priority V(1) recommendation is mandatory, while a priority V(5) recommendation brings only slight improvement
        type: int
        default: 3
        choices: [ 1, 2, 3, 4, 5 ]

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Enable DPM
  vmware.vmware.cluster_dpm:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: datacenter
    cluster_name: cluster
    enable: true
  delegate_to: localhost

- name: Enable DPM and generate but don't apply all recommendations
  vmware.vmware.cluster_dpm:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: datacenter
    cluster_name: cluster
    enable: true
    automation_level: manual
    recommendation_priority_threshold: 5
  delegate_to: localhost
'''

RETURN = r'''
result:
    description:
        - Information about the DPM config update task, if something changed
        - If nothing changed, an empty dictionary is returned
    returned: On success
    type: dict
    sample: {
        "result": {
            "completion_time": "2024-07-29T15:27:37.041577+00:00",
            "entity_name": "test-5fb1_cluster_dpm_test",
            "error": null,
            "result": null,
            "state": "success"
        }
    }
'''

try:
    from pyVmomi import vim, vmodl
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError,
    RunningTaskMonitor
)
from ansible_collections.vmware.vmware.plugins.module_utils._facts import (
    ClusterFacts
)

from ansible.module_utils._text import to_native


class VMwareCluster(ModulePyvmomiBase):
    def __init__(self, module):
        super(VMwareCluster, self).__init__(module)

        datacenter = self.get_datacenter_by_name_or_moid(self.params.get('datacenter'), fail_on_missing=True)
        self.cluster = self.get_cluster_by_name_or_moid(self.params.get('cluster'), fail_on_missing=True, datacenter=datacenter)

    @property
    def automation_level(self):
        """
        The vCenter UI and docs say the automation level can be manual or automatic. When setting this option
        in the API, it expects manual or automated. So if the user chose 'automatic', we need to change it to
        automated in code.
        """
        if self.params['automation_level'] == 'automatic':
            return 'automated'

        return self.params['automation_level']

    @property
    def recommendation_priority_threshold(self):
        """
        When applying or reading this threshold from the vCenter config, the values are reversed. So
        for example, vCenter thinks 1 is the most aggressive when docs/UI say 5 is most aggressive.
        We present the scale seen in the docs/UI to the user and then adjust the value here to ensure
        vCenter behaves as intended.
        """
        return ClusterFacts.reverse_drs_or_dpm_rate(self.params['recommendation_priority_threshold'])

    def check_dpm_config_diff(self):
        """
        Check the active DPM configuration and determine if desired configuration is different.
        If the current DPM configuration is undefined for some reason, the error is caught
        and the function returns True.
        Returns:
            True if there is difference, else False
        """
        try:
            dpm_config = self.cluster.configurationEx.dpmConfigInfo

            if (dpm_config.enabled != self.params['enable'] or
                    dpm_config.defaultDpmBehavior != self.automation_level or
                    dpm_config.hostPowerActionRate != self.recommendation_priority_threshold):
                return True

        except AttributeError:
            return True

        return False

    def __create_dpm_config_spec(self):
        """
        Uses the class's attributes to create a new cluster DPM config spec
        """
        cluster_config_spec = vim.cluster.ConfigSpecEx()
        cluster_config_spec.dpmConfig = vim.cluster.DpmConfigInfo()
        cluster_config_spec.dpmConfig.enabled = self.params['enable']
        cluster_config_spec.dpmConfig.defaultDpmBehavior = self.automation_level
        cluster_config_spec.dpmConfig.hostPowerActionRate = self.recommendation_priority_threshold

        return cluster_config_spec

    def apply_dpm_configuration(self):
        """
        Apply the class's attributes as a DPM config to the cluster
        """
        cluster_config_spec = self.__create_dpm_config_spec()

        try:
            task = self.cluster.ReconfigureComputeResource_Task(cluster_config_spec, True)
            _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
        except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
            self.module.fail_json(msg=to_native(vmodl_fault.msg))
        except TaskError as task_e:
            self.module.fail_json(msg=to_native(task_e))
        except Exception as generic_exc:
            self.module.fail_json(msg="Failed to update cluster due to exception %s" % to_native(generic_exc))

        return task_result


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                cluster=dict(type='str', required=True, aliases=['cluster_name']),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
                enable=dict(type='bool', default=True),
                automation_level=dict(
                    type='str',
                    choices=['automatic', 'manual'],
                    default='automatic'
                ),
                recommendation_priority_threshold=dict(type='int', choices=[1, 2, 3, 4, 5], default=ClusterFacts.DPM_DEFAULT_RATE)
            )
        },
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        result={}
    )

    cluster_dpm = VMwareCluster(module)

    config_is_different = cluster_dpm.check_dpm_config_diff()
    if config_is_different:
        result['changed'] = True
        if not module.check_mode:
            result['result'] = cluster_dpm.apply_dpm_configuration()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
