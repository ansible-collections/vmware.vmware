# -*- coding: utf-8 -*-

# Copyright: (c) 2016, Charles Paul <cpaul@ansible.com>
# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2019, Abhijeet Kasurde <akasurde@redhat.com>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


class ModuleDocFragment(object):
    # This document fragment serves as a base for all vmware modules. If you are using the REST API SDK in your module,
    # you should use the REST_COMPATIBLE_DOCUMENTATION fragment. Otherwise, you can use this BASE_DOCUMENTATION.
    # BASE_DOCUMENTATION covers the arg spec provided by the base_argument_spec() function, while
    # REST_COMPATIBLE_DOCUMENTATION covers the arg spec provided by the rest_compatible_argument_spec() function
    BASE_DOCUMENTATION = r'''
notes:
  - All modules require API write access and hence is not supported on a free ESXi license.
  - All variables and VMware object names are case sensitive.
  - >-
      Modules may rely on the 'requests' python library, which does not use the system certificate store by default. You can
      specify the certificate store by setting the REQUESTS_CA_BUNDLE environment variable.
      Example: 'export REQUESTS_CA_BUNDLE=/path/to/your/ca_bundle.pem'
options:
  hostname:
    description:
      - The hostname or IP address of the vSphere vCenter server.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_HOST) will be used instead.
    type: str
  username:
    description:
      - The username of the vSphere vCenter server.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_USER) will be used instead.
    type: str
    aliases: [ admin, user ]
  password:
    description:
      - The password of the vSphere vCenter server.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_PASSWORD) will be used instead.
    type: str
    aliases: [ pass, pwd ]
  validate_certs:
    description:
      - Allows connection when SSL certificates are not valid. Set to V(false) when certificates are not trusted.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_VALIDATE_CERTS) will be used instead.
    type: bool
    default: true
  port:
    description:
      - The port number of the vSphere vCenter server.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_PORT) will be used instead.
    type: int
    default: 443
  proxy_host:
    description:
      - Address of a proxy that will receive all HTTPS requests and relay them.
      - The format is a hostname or a IP.
      - If the value is not specified in the task, the value of environment variable E(VMWARE_PROXY_HOST) will be used instead.
    type: str
    required: false
  proxy_port:
    description:
    - Port of the HTTP proxy that will receive all HTTPS requests and relay them.
    - If the value is not specified in the task, the value of environment variable E(VMWARE_PROXY_PORT) will be used instead.
    type: int
    required: false
'''
    # Use this document fragment a base for any vmware modules that use the REST API SDK. If your module uses
    # both the REST SDK and pyvmomi, you should still use this doc fragment
    REST_COMPATIBLE_DOCUMENTATION = BASE_DOCUMENTATION + r'''
  proxy_protocol:
    description:
      - The proxy connection protocol to use.
      - This is option is used if the correct proxy protocol cannot be automatically determined.
    type: str
    choices: [ http, https ]
    default: https
    aliases: [protocol]
'''
