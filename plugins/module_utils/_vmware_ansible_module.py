from __future__ import absolute_import, division, print_function

__metaclass__ = type


import os

from ansible.module_utils.common.validation import check_type_bool
from ansible.module_utils.common.text.converters import to_native


enable_turbo_mode = check_type_bool(os.environ.get("ENABLE_TURBO_MODE", False))

if enable_turbo_mode:
    try:
        from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (  # noqa: F401
            AnsibleTurboModule as BaseAnsibleModule,
        )

        BaseAnsibleModule.collection_name = "vmware.vmware"
    except ImportError:
        from ansible.module_utils.basic import BaseAnsibleModule  # noqa: F401
else:
    from ansible.module_utils.basic import BaseAnsibleModule  # noqa: F401


class AnsibleModule(BaseAnsibleModule):
    """
    This should really be added to the upstream cloud.common repo, but until then we need it here.
    The outputs from a module need to be passed through the turbo server using pickle. If the output
    contains something that pickle cannot encode/decode, we need to convert it first.
    For most APIs that return content as JSON, this isn't an issue. But for the SDKs VMware uses,
    it can be a problem.
    """
    def exit_json(self, **kwargs):
        if enable_turbo_mode:
            kwargs = self.__format_value_for_turbo_server(kwargs)
        super().exit_json(**kwargs)

    def __format_value_for_turbo_server(self, value):
        if isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, set):
            return self.__format_value_for_turbo_server(list(value))
        if isinstance(value, list):
            return [self.__format_value_for_turbo_server(v) for v in value]
        if isinstance(value, dict):
            for k, v in value.items():
                value[k] = self.__format_value_for_turbo_server(v)
            return value

        return to_native(value)
