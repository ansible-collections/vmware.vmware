# -*- coding: utf-8 -*-

# Copyright: (c) 2016, Charles Paul <cpaul@ansible.com>
# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2019, Abhijeet Kasurde <akasurde@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    # This document fragment serves as a partial base for all vmware plugins. It should be used in addition to the base fragment, vmware.vmware.base_options
    # since that contains the actual argument descriptions and defaults. This just defines the environment variables since plugins have something
    # like the module spec where that is usually done.
    DOCUMENTATION = r'''
options:
  hostname:
    env:
      - name: VMWARE_HOST
  username:
    env:
      - name: VMWARE_USER
  password:
    env:
      - name: VMWARE_PASSWORD
  validate_certs:
    env:
      - name: VMWARE_VALIDATE_CERTS
  port:
    env:
      - name: VMWARE_PORT
  proxy_host:
    env:
      - name: VMWARE_PROXY_HOST
  proxy_port:
    env:
      - name: VMWARE_PROXY_PORT
'''
