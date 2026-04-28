#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Cloud Team (@ansible-collections)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
module: license_info
short_description: Fetch VMware vCenter license keys
description:
- Fetch vCenter, ESXi server license keys.
author:
- Ansible Cloud Team (@ansible-collections)
requirements:
- Python SDK for the VMware vSphere Management API
options:
    include_properties:
        description:
        - Include normalized license properties in output.
        - When true, returns all normalized property items.
        type: bool
        default: false
attributes:
  check_mode:
    description: The check_mode support.
    support: full
extends_documentation_fragment:
- vmware.vmware.base_options
'''

EXAMPLES = r'''
- name: Fetch vCenter license details
    vmware.vmware.license_info:
        hostname: '{{ vcenter_hostname }}'
        username: '{{ vcenter_username }}'
        password: '{{ vcenter_password }}'

- name: Fetch vCenter license details with properties
    vmware.vmware.license_info:
        hostname: '{{ vcenter_hostname }}'
        username: '{{ vcenter_username }}'
        password: '{{ vcenter_password }}'
        include_properties: true
'''

RETURN = r'''
licenses:
    description: List of license keys.
    returned: always
    type: list
    elements: dict
    contains:
        name:
            description: Display name of the license.
            type: str
            returned: always
        license_key:
            description: License key string.
            type: str
            returned: always
        edition_key:
            description: Edition identifier for the license.
            type: str
            returned: always
        cost_unit:
            description: Unit used for license consumption.
            type: str
            returned: always
        total:
            description: Total available license capacity.
            type: int
            returned: always
        used:
            description: Consumed license capacity.
            type: int
            returned: always
        expiration_date:
            description: License expiration date when available.
            type: str
            returned: when available
        labels:
            description: Key/value label metadata from vCenter.
            type: dict
            returned: always
        properties:
            description: Normalized vCenter license properties.
            type: dict
            returned: when include_properties=true
    sample:
        - name: VMware vCenter Server 8 Standard
            license_key: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
            edition_key: vc.standard.instance
            cost_unit: server
            total: 1
            used: 1
            expiration_date: '2026-07-31T00:00:00-05:00'
            labels:
                ProductName: VMware vCenter Server
            properties:
                ProductName: VMware VirtualCenter Server
                ProductVersion: '8.0'
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import (
    base_argument_spec,
)


class VcenterLicenseMgr(ModulePyvmomiBase):
    def __init__(self, module):
        super(VcenterLicenseMgr, self).__init__(module)
        self.include_properties = module.params.get("include_properties")

    @staticmethod
    def _to_primitive(value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except TypeError:
                return str(value)
        return None

    def _normalize_value(self, value):
        primitive = self._to_primitive(value)
        if primitive is not None or value is None:
            return primitive

        if isinstance(value, (list, tuple, set)):
            normalized = [self._normalize_value(item) for item in value]
            return [item for item in normalized if item not in (None, "", [], {})]

        if isinstance(value, dict):
            normalized = {
                str(k): self._normalize_value(v)
                for k, v in value.items()
            }
            return {k: v for k, v in normalized.items() if v not in (None, "", [], {})}

        # Many pyVmomi objects expose key/value and can be serialized cleanly this way.
        if hasattr(value, "key") and hasattr(value, "value"):
            key = self._normalize_value(getattr(value, "key", None))
            nested_value = self._normalize_value(getattr(value, "value", None))
            if key in (None, "") and nested_value in (None, "", [], {}):
                return None
            return {"key": key, "value": nested_value}

        # Skip opaque VMOMI object dumps that explode output size.
        return None

    @staticmethod
    def _append_property(data, key, value):
        if key not in data:
            data[key] = value
            return

        existing = data[key]
        if isinstance(existing, list):
            existing.append(value)
            return

        data[key] = [existing, value]

    def _property_pairs_to_dict(self, property_list):
        ignore_keys = {
            "LicenseInfo",
            "SuiteLicenseInfo",
            "Localized",
            "Properties",
        }
        data = {}
        for item in property_list or []:
            key = self._normalize_value(getattr(item, "key", None))
            if not key:
                continue
            if key in ignore_keys:
                continue

            value = self._normalize_value(getattr(item, "value", None))
            if value in (None, "", [], {}):
                continue

            self._append_property(data, key, value)
        return data

    def _labels_to_dict(self, labels):
        data = {}
        for label in labels or []:
            key = self._normalize_value(getattr(label, "key", None))
            if not key:
                continue
            value = self._normalize_value(getattr(label, "value", None))
            if value in (None, "", [], {}):
                continue
            data[key] = value
        return data

    def _guess_expiration(self, properties):
        preferred_keys = [
            "expirationDate",
            "expiration_date",
            "expiryDate",
            "expiry_date",
        ]
        for key in preferred_keys:
            if key in properties and properties[key] not in (None, ""):
                return properties[key]
        return None

    def list_details(self, licenses):
        details = []
        for item in licenses:
            properties = self._property_pairs_to_dict(getattr(item, "properties", None))
            labels = self._labels_to_dict(getattr(item, "labels", None))
            entry = {
                "name": self._normalize_value(getattr(item, "name", None)),
                "license_key": self._normalize_value(getattr(item, "licenseKey", None)),
                "edition_key": self._normalize_value(getattr(item, "editionKey", None)),
                "cost_unit": self._normalize_value(getattr(item, "costUnit", None)),
                "total": self._normalize_value(getattr(item, "total", None)),
                "used": self._normalize_value(getattr(item, "used", None)),
                "expiration_date": self._guess_expiration(properties),
                "labels": labels,
            }

            if self.include_properties:
                entry["properties"] = properties

            details.append(entry)
        return details


def main():
    argument_spec = base_argument_spec()
    argument_spec.update(
        include_properties=dict(type="bool", default=False),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    result = {"changed": False}

    pyv = VcenterLicenseMgr(module)
    if not pyv.is_vcenter():
        module.fail_json(
            msg=(
                "vcenter_license is meant for vCenter, hostname %s "
                "is not vCenter server." % module.params.get('hostname')
            )
        )

    lm = pyv.content.licenseManager
    details = pyv.list_details(lm.licenses)

    result["licenses"] = details

    module.exit_json(**result)


if __name__ == '__main__':
    main()
