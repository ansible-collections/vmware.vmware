from __future__ import absolute_import, division, print_function

__metaclass__ = type


import os
import functools

from ansible.module_utils.common.validation import check_type_bool
from ansible.module_utils.common.text.converters import to_native


enable_turbo_mode = check_type_bool(os.environ.get("ENABLE_TURBO_MODE", False))

if enable_turbo_mode:
    try:
        from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
            AnsibleTurboModule as BaseAnsibleModule,
        )

        BaseAnsibleModule.collection_name = "vmware.vmware"
    except ImportError:
        from ansible.module_utils.basic import AnsibleModule as BaseAnsibleModule
else:
    from ansible.module_utils.basic import AnsibleModule as BaseAnsibleModule


CACHED_FUNCTION_REGISTRY = set()

class AnsibleModule(BaseAnsibleModule):
    """
    The exit_json and __format_value_for_turbo_server should really be added to the upstream
    cloud.common repo, but until then we need it here.
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

    def clear_vmware_cache(self, funcs=None):
        cleared = set()
        no_cache = set()
        if not funcs:
            funcs = CACHED_FUNCTION_REGISTRY

        for f in funcs:
            try:
                f.cache_clear()
                cleared.add(f.__name__)
            except AttributeError:
                no_cache.add(f.__name__)

        return cleared, no_cache


def cache(func):
    @functools.wraps(func)
    @functools.lru_cache(maxsize=128)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    CACHED_FUNCTION_REGISTRY.add(wrapper)
    return wrapper
