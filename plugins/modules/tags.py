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

    tags:
        description:
            - A list of tags to manage.
        type: list
        required: True
        elements: dict
        options:
            name:
                description:
                    - The name of the tag.
                type: str
                required: True
            category:
                description:
                    - The category of the tag.
                type: str
                required: True
            description:
                description:
                    - The description of the tag.
                type: str
                required: False

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


class VmwareTagModule(ModuleRestBase):
    def __init__(self, module):
        super().__init__(module)

    def _map_category_names_to_ids(self):
        category_map = dict()
        category_names = set(tag.get('category_name') for tag in self.params['tags'] if tag.get('category_name'))
        if not category_names:
            return category_map

        for tag_category_id in self.tag_category_service.list():
            category_data = self.tag_category_service.get(tag_category_id)
            if category_data.name in category_names:
                category_names.remove(category_data.name)
                category_map[category_data.name] = category_data.id

            if not category_names:
                break

        return category_map

    def _map_tag_params_to_dict(self, category_names_to_ids):
        tag_dict = dict()
        for tag_param in self.params['tags']:
            category_id = category_names_to_ids[tag_param['category_name']] if tag_param.get('category_name') else tag_param['category_id']
            if category_id not in tag_dict:
                tag_dict[category_id] = dict()

            tag_dict[category_id][tag_param['name']] = tag_param.get('description', None)
        return tag_dict

    def parse_tag_params_to_dict(self):
        category_names_to_ids = self._map_category_names_to_ids()
        return self._map_tag_params_to_dict(category_names_to_ids)

    def get_tags_to_remove(self):
        tags_to_remove = []
        tag_params = self.parse_tag_params_to_dict()
        for category_id in tag_params.keys():
            for existing_tag_id in self.tag_service.list_tags_for_category(category_id):
                existing_tag = self.tag_service.get(existing_tag_id)
                if existing_tag.name in tag_params[category_id]:
                    tags_to_remove.append(existing_tag)
                    del tag_params[category_id][existing_tag.name]

                if not tag_params[category_id]:
                    break

        return tags_to_remove

    def get_tags_to_create_or_update(self):
        tags_to_update = {}
        tags_to_create = {}
        tag_params = self.parse_tag_params_to_dict()
        for category_id in tag_params.keys():
            for existing_tag_id in self.tag_service.list_tags_for_category(category_id):
                self._check_if_tag_needs_updating(tag_params, category_id, existing_tag_id, tags_to_update)
                if not tag_params[category_id]:
                    break

            if tag_params[category_id]:
                tags_to_create[category_id] = [
                    {'name': tag[0], 'description': tag[1]} for tag in tag_params[category_id].items()
                ]

        return tags_to_create, tags_to_update

    def _check_if_tag_needs_updating(self, tag_params, category_id, existing_tag_id, tags_to_update):
        existing_tag = self.tag_service.get(existing_tag_id)
        if not existing_tag.name in tag_params[category_id]:
            return

        new_tag_description = tag_params[category_id][existing_tag.name]
        if new_tag_description is None or existing_tag.description == new_tag_description:
            return

        if category_id not in tags_to_update:
            tags_to_update[category_id] = []

        tags_to_update[category_id].append({
            'before': {
                'name': existing_tag.name,
                'description': existing_tag.description,
                'id': existing_tag.id,
            },
            'after': {
                'name': existing_tag.name,
                'description': new_tag_description,
                'id': existing_tag.id,
            },
        })
        del tag_params[category_id][existing_tag.name]

    def create_and_update_tags(self, tags_to_create, tags_to_update):
        for category_id, tags in tags_to_create.items():
            for tag in tags:
                new_tag_id = self._create_tag(tag['name'], tag['description'], category_id)
                tag['id'] = new_tag_id

        for category_id, tags in tags_to_update.items():
            for tag in tags:
                self.update_tag(tag['after']['id'], tag['after']['description'])

    # def get_tags_to_change(self):
    #     tags_to_create = []
    #     tags_to_update = []
    #     tags_to_delete = []

    #     all_tags = self.tag_service.list()
    #     for tag_id in all_tags:
    #         tag_model = self.tag_service.get(tag_id)
    #         if tag_model.name not in self.params['tags']:
    #             tags_to_create.append(tag_model.name)
    #             continue

    #         if self.is_tag_model_different(tag_model):
    #             tags_to_update.append(tag_model.name)
    #             continue

    #     return tags_to_create, tags_to_update, tags_to_delete

    # def is_tag_model_different(self, tag_model):
    #     if tag_model.name not in self.params['tags']:
    #         return True
    #     if tag_model.description != self.params['tags'][tag_model.name]['description']:
    #         return True
    #     return False

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

    # def create_tag_category(self, name, description, cardinality):
    #     """create a category. User who invokes this needs create category privilege."""
    #     create_spec = self.tag_category_service.CreateSpec()
    #     create_spec.name = name
    #     create_spec.description = description
    #     create_spec.cardinality = cardinality
    #     associableTypes = set()
    #     create_spec.associable_types = associableTypes
    #     return self.tag_category_service.create(create_spec)

    # def delete_tag_category(self):
    #     """Deletes an existing tag category; User who invokes this API needs
    #     delete privilege on the tag category.
    #     """
    #     return
    #     self.tag_category_service.delete(self.category_id)

    def _create_tag(self, name, description, category_id):
        """Creates a Tag"""
        create_spec = self.tag_service.CreateSpec()
        create_spec.name = name
        create_spec.description = description or ''
        create_spec.category_id = category_id
        return self.tag_service.create(create_spec)

    def update_tag(self, tag_id, description):
        update_spec = self.tag_service.UpdateSpec()
        update_spec.setDescription = description
        self.tag_service.update(tag_id, update_spec)

    def delete_tags(self, tags_to_remove):
        """Delete an existing tag.
        User who invokes this API needs delete privilege on the tag."""
        for tags in tags_to_remove.values():
            for tag in tags:
                self.tag_service.delete(tag['id'])


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            state=dict(type='str', choices=['present', 'absent'], default='present'),
            tags=dict(
                type='list', elements='dict', required=True, options=dict(
                    name=dict(type='str', required=True),
                    category_name=dict(type='str', required=False),
                    category_id=dict(type='str', required=False),
                    description=dict(type='str', required=False),
                ),
                required_one_of=[['category_name', 'category_id']]
            )
        )
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    result = dict(
        changed=False,
        updated_tags=[],
        created_tags=[],
        removed_tags=[]
    )

    vmware_tag = VmwareTagModule(module)
    if module.params['state'] == 'present':
        tags_to_create, tags_to_update = vmware_tag.get_tags_to_create_or_update()
        if tags_to_create or tags_to_update:
            result['changed'] = True
            result['created_tags'] = tags_to_create
            result['updated_tags'] = tags_to_update

        if not module.check_mode:
            vmware_tag.create_and_update_tags(tags_to_create, tags_to_update)

    elif module.params['state'] == 'absent':
        tags_to_remove = vmware_tag.get_tags_to_remove()
        if tags_to_remove:
            result['changed'] = True
            result['removed_tags'] = tags_to_remove
            if not module.check_mode:
                vmware_tag.delete_tags(tags_to_remove)

    module.exit_json(**result)

if __name__ == '__main__':
    main()
