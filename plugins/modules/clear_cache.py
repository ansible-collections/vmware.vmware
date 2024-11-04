#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: clear_cache
short_description: Clears the internal cache used by Ansible vmware.vmware
description:
- This module clears the internal cache used by Ansible vmware.vmware modules, if caching is enabled.
author:
- Ansible Cloud Team (@ansible-collections)
requirements: []
options: {}

attributes:
  check_mode:
    description: The check_mode support.
    support: none
extends_documentation_fragment: []
'''

EXAMPLES = r'''
- name: Clear the cache
  vmware.vmware.clear_cache: {}
'''

RETURN = r'''
'''


from ansible_collections.vmware.vmware.plugins.module_utils._vmware_ansible_module import (
    AnsibleModule,
)


def main():
    module = AnsibleModule(
        argument_spec={},
        supports_check_mode=True,
    )

    cleared, no_cache = module.clear_vmware_cache()
    module.exit_json(
        changed=bool(cleared),
        cleared=list(cleared),
        no_cache=list(no_cache)
    )


if __name__ == '__main__':
    main()
