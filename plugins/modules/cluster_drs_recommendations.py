#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: cluster_drs_recommendations
short_description: Apply Distributed Resource Scheduler (DRS) recommendations on VMware vSphere clusters
description:
    - Applies DRS recommendations on VMware vSphere clusters.
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

extends_documentation_fragment:
    - vmware.vmware.vmware.documentation
'''

EXAMPLES = r'''
- name: Apply DRS Recommendations for Cluster
  vmware.vmware.cluster_drs_recommendations:
    hostname: '{{ vcenter_hostname }}'
    username: '{{ vcenter_username }}'
    password: '{{ vcenter_password }}'
    datacenter_name: datacenter
    cluster_name: cluster
  delegate_to: localhost
'''

RETURN = r'''
applied_recommendations:
    description:
        - List of dictionaries describing the applied recommendations
        - Each entry has a description, which is a string saying where servers were moved
        - Each entry has a task_result, which is a dictionary describing the vCenter task
    returned: always
    type: list
    sample: [
        {
            "description": "server1 move from host1 to host2.",
            "task_result": {
                "completion_time": "2024-07-29T15:27:37.041577+00:00",
                "entity_name": "test-5fb1_cluster_drs_test",
                "error": null,
                "result": null,
                "state": "success"
            }
        },
        {
            "description": "server2 move from host1 to host2.",
            "task_result": {
                "completion_time": "2024-07-29T15:27:37.041577+00:00",
                "entity_name": "test-5fb1_cluster_drs_test",
                "error": null,
                "result": null,
                "state": "success"
            }
        }
    ]
'''

try:
    from pyVmomi import vmodl
except ImportError:
    pass

from itertools import zip_longest
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._vmware import (
    PyVmomi,
    vmware_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_tasks import (
    TaskError,
    RunningTaskMonitor
)
from ansible.module_utils._text import to_native


class VMwareCluster(PyVmomi):
    def __init__(self, module):
        super(VMwareCluster, self).__init__(module)
        datacenter = self.get_datacenter_by_name(self.params.get('datacenter'), fail_on_missing=True)
        self.cluster = self.get_cluster_by_name(self.params.get('cluster'), fail_on_missing=True, datacenter=datacenter)

    def get_recommendations(self):
        """
        Refreshes the clusters current DRS recommendation list and returns them.
        Returns:
            list
        """
        self.cluster.RefreshRecommendation()
        return self.cluster.recommendation

    def apply_recommendations(self):
        """
        Applies any DRS recommendations that the cluster may have pending. Waits for all tasks to finish and returns
        information about the applied recommendation and tasks.
        Returns:
          list(dict())
          Example: [{description: str, task_result: dict}]
        """
        applied_recommendation_descriptions = []
        applied_recommendation_tasks = []
        for recommendation in self.cluster.recommendation:
            applied_recommendation_descriptions.append(
                "%s move from %s to %s." % (
                    recommendation.action[0].target.name,
                    recommendation.action[0].drsMigration.source.name,
                    recommendation.action[0].drsMigration.destination.name
                )
            )

            if not self.module.check_mode:
                applied_recommendation_tasks.append(self.cluster.ApplyRecommendation(recommendation.key))

        task_results = self.__wait_for_recommendation_task_results(applied_recommendation_tasks)
        combined_results = zip_longest(applied_recommendation_descriptions, task_results, fillvalue=dict())
        return [dict(zip(['description', 'task_results'], res)) for res in combined_results]

    def __wait_for_recommendation_task_results(self, recommendation_tasks):
        """
        Waits for all tasks in a list of tasks to finish, then returns the task output
        Args:
            recommendation_tasks: list of vcenter task objects
        Returns:
          list(dict)
        """
        task_results = []
        for task in recommendation_tasks:
            try:
                _, task_result = RunningTaskMonitor(task).wait_for_completion()   # pylint: disable=disallowed-name
            except (vmodl.RuntimeFault, vmodl.MethodFault)as vmodl_fault:
                self.module.fail_json(msg=to_native(vmodl_fault.msg))
            except TaskError as task_e:
                self.module.fail_json(msg=to_native(task_e))
            except Exception as generic_exc:
                self.module.fail_json(msg="Failed to apply DRS recommendation due to exception %s" % to_native(generic_exc))
            task_results.append(task_result)

        return task_results


def main():
    module = AnsibleModule(
        argument_spec={
            **vmware_argument_spec(), **dict(
                cluster=dict(type='str', required=True, aliases=['cluster_name']),
                datacenter=dict(type='str', required=True, aliases=['datacenter_name']),
            )
        },
        supports_check_mode=True,
    )

    result = dict(
        changed=False,
        applied_recommendations=[]
    )

    cluster_drs = VMwareCluster(module)
    recommendations = cluster_drs.get_recommendations()
    if recommendations:
        result['changed'] = True
        result['applied_recommendations'] = cluster_drs.apply_recommendations()

    module.exit_json(**result)


if __name__ == '__main__':
    main()
