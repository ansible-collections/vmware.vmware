#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: tag
short_description: Manage one or more VMware tags.
description:
    - This module allows you to create, update, and delete VMware tags.
    - You can also specify a vSphere object, and manage the tags assigned to it.
    - If no object is specified, the module will manage the tags at a global level.

author:
    - Ansible Cloud Team (@ansible-collections)

options:
    state:
        description:
            - Whether to create, update, or delete the tag(s).
        type: str
        required: True
        choices: [present, absent, set]
    object_moid:
        description:
            - The MOID of the vSphere object to manage.
        type: str
        required: False

    tags:
        description:
            - A list of tags to manage.
        type: list
        required: True
        elements: str

extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
'''

EXAMPLES = r'''
- name: Gather VM Resource Info
  vmware.vmware.vm_resource_info:
    moid: "{{ vm_id }}"

- name: Gather VM Resource Info By Name
  vmware.vmware.vm_resource_info:
    name: "{{ vm_name }}"
    name_match: first

- name: Gather Just Resource Config Info
  vmware.vmware.vm_resource_info:
    moid: "{{ vm_id }}"
    gather_cpu_stats: false
    gather_memory_stats: false

- name: Gather Just The Host and Resource Pool IDs For All VMs
  vmware.vmware.vm_resource_info:
    moid: "{{ vm_id }}"
    gather_cpu_config: false
    gather_memory_config: false
    gather_cpu_stats: false
    gather_memory_stats: false
# Note: although all gather parameters are set to false in the previous example, the output keys will still be present in the results. For example:
# "vms": [
#     {
#         "cpu": {},
#         "esxi_host": {
#             "moid": "host-64",
#             "name": "10.10.10.129"
#         },
#         "memory": {},
#         "moid": "vm-75373",
#         "name": "ma1",
#         "resource_pool": {
#             "moid": "resgroup-35",
#             "name": "Resources"
#         },
#         "stats": {
#             "cpu": {},
#             "memory": {}
#         }
#     }
# ]
'''

RETURN = r'''
vms:
    description:
        - Information about CPU and memory for the selected VMs.
    returned: Always
    type: list
    sample: [
        {
            "cpu": {
                "cores_per_socket": 1,
                "hot_add_enabled": false,
                "hot_remove_enabled": false,
                "processor_count": 1
            },
            "esxi_host": {
                "moid": "host-64",
                "name": "10.10.10.129"
            },
            "memory": {
                "hot_add_enabled": false,
                "hot_add_increment": 0,
                "hot_add_max_limit": 4096,
                "size_mb": 4096
            },
            "moid": "vm-75373",
            "name": "ma1",
            "resource_pool": {
                "moid": "resgroup-35",
                "name": "Resources"
            },
            "stats": {
                "cpu": {
                    "demand_mhz": 68,
                    "distributed_entitlement_mhz": 68,
                    "readiness_mhz": 0,
                    "static_entitlement_mhz": 1989,
                    "usage_mhz": 68
                },
                "memory": {
                    "active_mb": 81,
                    "ballooned_mb": 0,
                    "consumed_overhead_mb": 38,
                    "distributed_entitlement_mb": 857,
                    "guest_usage_mb": 81,
                    "host_usage_mb": 1890,
                    "static_entitlement_mb": 4406,
                    "swapped_mb": 0
                }
            }
        }
    ]
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    rest_compatible_argument_spec
)



class VmwareTag(ModuleRestBase):
    def __init__(self, module):
        super().__init__(module)
        # self.dynamic_managed_object = DynamicID(type=self.object_type, id=managed_object_id)

    def _main(self):
        all_categories = self.tag_category_service.list()
        for category_id in all_categories:
            category_model = self.tag_category_service.get(category_id)
            print("Category ID '{}', name '{}', description '{}'".format(
                category_model.id, category_model.name, category_model.description
            ))

    def get_tags_to_change(self):
        tags_to_create = []
        tags_to_update = []
        tags_to_delete = []

        all_tags = self.tag_service.list()
        for tag_id in all_tags:
            tag_model = self.tag_service.get(tag_id)
            if tag_model.name not in self.params['tags']:
                tags_to_create.append(tag_model.name)
                continue

            if self.is_tag_model_different(tag_model):
                tags_to_update.append(tag_model.name)
                continue

        return tags_to_create, tags_to_update, tags_to_delete

    def is_tag_model_different(self, tag_model):
        if tag_model.name not in self.params['tags']:
            return True
        if tag_model.description != self.params['tags'][tag_model.name]['description']:
            return True
        return False

    # def tag_object(self, object_moid):
    #     print('Tagging the cluster {0}...'.format(self.cluster_name))
    #     self.dynamic_id = DynamicID(
    #         type='ClusterComputeResource', id=self.cluster_moid)
    #     self.client.tagging.TagAssociation.attach(
    #         tag_id=self.tag_id, object_id=self.dynamic_id)
    #     for tag_id in self.client.tagging.TagAssociation.list_attached_tags(
    #             self.dynamic_id):
    #         if tag_id == self.tag_id:
    #             self.tag_attached = True
    #             break
    #     assert self.tag_attached
    #     print('Tagged cluster: {0}'.format(self.cluster_moid))

    def create_tag_category(self, name, description, cardinality):
        """create a category. User who invokes this needs create category privilege."""
        create_spec = self.tag_category_service.CreateSpec()
        create_spec.name = name
        create_spec.description = description
        create_spec.cardinality = cardinality
        associableTypes = set()
        create_spec.associable_types = associableTypes
        return self.tag_category_service.create(create_spec)

    def delete_tag_category(self, category_id):
        """Deletes an existing tag category; User who invokes this API needs
        delete privilege on the tag category.
        """
        self.tag_category_service.delete(category_id)

    def create_tag(self, name, description, category_id):
        """Creates a Tag"""
        create_spec = self.tag_service.CreateSpec()
        create_spec.name = name
        create_spec.description = description
        create_spec.category_id = category_id
        return self.tag_service.create(create_spec)

    def update_tag(self, tag_id, description):
        update_spec = self.tag_service.UpdateSpec()
        update_spec.setDescription = description
        self.tag_service.update(tag_id, update_spec)

    def delete_tag(self, tag_id):
        """Delete an existing tag.
        User who invokes this API needs delete privilege on the tag."""
        self.tag_service.delete(tag_id)

def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type='str', choices=['present', 'absent', 'set'], required=True),
            object_moid=dict(type='str', required=False),
            tags=dict(type='list', elements='str', required=True),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[['name', 'uuid', 'moid']]
    )

    result = dict(
        changed=False,
        created_tags=[],
        updated_tags=[],
        deleted_tags=[]
    )

    vmware_tag = VmwareTag(module)
    tags_to_create, tags_to_update, tags_to_delete = vmware_tag.get_tags_to_change()

    if any([tags_to_create, tags_to_update, tags_to_delete]):
        result['changed'] = True
        result['created_tags'] = tags_to_create
        result['updated_tags'] = tags_to_update
        result['deleted_tags'] = tags_to_delete

    for tag_id in tags_to_create:
        vmware_tag.create_tag(tag_id)
    for tag_id in tags_to_update:
        vmware_tag.update_tag(tag_id)
    for tag_id in tags_to_delete:
        vmware_tag.delete_tag(tag_id)

    module.exit_json(**result)

if __name__ == '__main__':
    main()
