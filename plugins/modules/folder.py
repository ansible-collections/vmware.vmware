#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: folder
short_description: Manage VMware vSphere folders
description:
    - Adds or removes VMware vSphere folders. This module does not manage folders inside of datastores.
author:
    - Ansible Cloud Team (@ansible-collections)

options:
    datacenter:
        description:
            - The name of the datacenter where the folder should be created.
            - Only used if the O(relative_path) option is used.
        type: str
        required: false
        aliases: [datacenter_name]
    folder_type:
        description:
            - The type of folder that should be created.
            - The folder type controls what resources can be held in the folder, as well as the path where the folder is created.
            - For example, a folder at path /DC-01/vm/my/folder has folder type 'vm'.
            - Only used if the O(relative_path) option is used.
        type: str
        required: false
        choices: [vm, host, storage, network]
    relative_path:
        description:
            - The relative path of the folder to create. The relative path should not include the datacenter or the folder type.
            - For example the relative path for the folder /DC-01/vm/my/folder is my/folder
            - One of O(relative_path) or O(absolute_path) must be specified.
        type: str
    absolute_path:
        description:
            - The absolute path of the folder to create. The absolute path should include the datacenter or the folder type.
            - The leading slash is not required. For example the absolute path could be /DC-01/vm/my/folder or DC-01/vm/my/folder
            - One of O(relative_path) or O(absolute_path) must be specified.
        type: str
    state:
        description:
            - Create V(present) or remove V(absent) a vSphere folder.
            - When state is V(present), all folders in the specified path will be created if they are missing.
            - When state is V(absent), all content inside the folder will be deleted. See O(remove_vm_data)
        choices: [ absent, present ]
        default: present
        type: str
    remove_vm_data:
        description:
            - Only used if state is V(absent)
            - If true, any VMs in the folder tree will be completely removed. This includes any disks or data associated with the VM.
            - >-
              If false, any VMs in the folder tree are deregistered. This means they are removed from the vSphere inventory but
              their data is not deleted.
        default: false
        type: bool

extends_documentation_fragment:
    - vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Create Folder Using A Relative Path (/DC01/storage/my/test/folder)
  vmware.vmware.folder:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false
    datacenter: DC01
    relative_path: my/test/folder
    folder_type: storage

# This is the same as the example above, but shows how to do it using different params.
- name: Create A Folder Using An Absolute Path
  vmware.vmware.folder:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false
    absolute_path: /DC01/storage/my/test/folder


- name: Delete The Folder and All Of Its Contents
  vmware.vmware.folder:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false
    absolute_path: /DC01/storage/my
    state: absent


- name: Delete A VM Folder But Keep The VM Data Disks
  vmware.vmware.folder:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false
    absolute_path: /DC01/vm/sql
    state: absent
    remove_vm_data: False
'''

RETURN = r'''
folder:
    description:
        - Identifying information about the folder
    returned: When state is present
    type: dict
    sample: {
        "folder": {
            "moid": "group-c111111",
            "name": "example-folder"
        },
    }
'''

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.text.converters import to_native

from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_argument_spec import (
    base_argument_spec
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_folder_paths import (
    prepend_datacenter_and_folder_type
)


class VmwareFolder(ModulePyvmomiBase):
    def __init__(self, module):
        super().__init__(module)
        if self.params['absolute_path']:
            self.absolute_folder_path = self.params['absolute_path']
        else:
            self.absolute_folder_path = prepend_datacenter_and_folder_type(
                folder_path=self.params['relative_path'],
                datacenter_name=self.params['datacenter'],
                folder_type=self.params['folder_type'],
            )
        self.absolute_folder_path = self.absolute_folder_path.strip('/')
        self.folder_object = self.lookup_folder_object(self.absolute_folder_path)

    def lookup_folder_object(self, path, fail_on_missing=False):
        try:
            return self.get_folder_by_absolute_path(
                folder_path=path,
                fail_on_missing=fail_on_missing
            )
        except Exception as generic_exc:
            self.module.fail_json(msg=(
                "Unexpected error while looking up folder %s due to exception %s"
                % (self.absolute_folder_path, to_native(generic_exc))
            ))

    def delete_folder(self):
        try:
            if "vim.Virtualmachine" in self.folder_object.childType and not self.params['remove_vm_data']:
                self.folder_object.UnregisterAndDestroy()
            else:
                self.folder_object.Destroy()
        except vim.fault.ConcurrentAccess as e:
            self.module.fail_json(msg=(
                "Failed to remove folder as another client modified folder during this operation : %s"
                % to_native(e.msg)
            ))
        except vim.fault.InvalidState as e:
            self.module.fail_json(msg=(
                "Failed to remove folder because it is in an invalid state : %s" % to_native(e.msg)
            ))
        except Exception as e:
            self.module.fail_json(msg=(
                "Failed to remove folder due to unexpected error %s " % to_native(e)
            ))

    def create_folder(self):
        """
        Create the folder requested by the user. To save time, we split the folder path in half and check
        if the folder at that point exists. If it does, we start the search there. If it doesn't, we start
        the search at the /datacenter/type point of the path.
        Returns:
            The final folder object created
        """
        split_path = self.absolute_folder_path.split('/')
        middle_index = (len(split_path)//2) + 1

        starting_index = middle_index
        starting_folder = self.lookup_folder_object('/'.join(split_path[:middle_index]))
        if not starting_folder:
            # whatever folder is in the middle of the path doesn't exist, so we may as well
            # start from the beginning, or /datacenter/type, and check the whole path
            starting_index = 2
            starting_folder = self.lookup_folder_object('/'.join(split_path[:2]), fail_on_missing=True)

        return self.__create_folders_on_path(
            starting_folder=starting_folder,
            starting_index=starting_index,
            path_parts=split_path,
        )

    def __create_folders_on_path(self, starting_index, starting_folder, path_parts):
        """
        Creates each folder that should be on a path.
        Arguments:
            starting_index:
                int, The index of the path_parts list where we should start
            starting_folder:
                Folder object, The folder that exists at the starting index point of the path
            path_parts:
                A list of strings that make up the final folder path
        Returns:
            The final folder object created
        """
        last_known_path = '/'.join(path_parts[:starting_index])
        last_known_folder = starting_folder
        for path_part in path_parts[starting_index:]:
            last_known_path = last_known_path + '/' + path_part
            _folder = self.lookup_folder_object(last_known_path)
            if _folder:
                last_known_folder = _folder
                continue

            last_known_folder = last_known_folder.CreateFolder(path_part)
        return last_known_folder


def main():
    module = AnsibleModule(
        argument_spec={
            **base_argument_spec(), **dict(
                datacenter=dict(type='str', required=False, aliases=['datacenter_name']),
                folder_type=dict(type='str', choices=['vm', 'host', 'network', 'storage'], required=False),
                relative_path=dict(type='str', required=False),
                absolute_path=dict(type='str', required=False),
                state=dict(type='str', default='present', choices=['absent', 'present']),
                remove_vm_data=dict(type='bool', default=False),
            )
        },
        supports_check_mode=True,
        required_one_of=[
            ('relative_path', 'absolute_path')
        ],
        mutually_exclusive=[
            ('absolute_path', 'relative_path')
        ],
        required_by={
            'relative_path': ('datacenter', 'folder_type')
        }
    )

    vmware_folder = VmwareFolder(module)

    if module.params['state'] == 'present':
        if vmware_folder.folder_object:
            module.exit_json(changed=False, folder={
                'moid': vmware_folder.folder_object._GetMoId(),
                'name': vmware_folder.folder_object.name
            })

        new_folder = vmware_folder.create_folder()
        module.exit_json(changed=True, folder={
                'moid': new_folder._GetMoId(),
                'name': new_folder.name
            })

    if module.params['state'] == 'absent':
        if not vmware_folder.folder_object:
            module.exit_json(changed=False)

        vmware_folder.delete_folder()
        module.exit_json(changed=True)


if __name__ == '__main__':
    main()
