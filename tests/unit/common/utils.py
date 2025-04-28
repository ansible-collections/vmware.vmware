from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import contextlib
import mock
import pytest

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes


def run_module(module_entry, module_args=None, expect_success=True):
    """
        Run the (mock) module and expect Ansible to exit without an error
    """
    raises = AnsibleExitJson if expect_success else AnsibleFailJson

    if module_args is None:
        module_args = {}

    with pytest.raises(raises) as c, set_module_args(module_args):
        module_entry()

    return c.value.args[0]


@contextlib.contextmanager
def set_module_args(args=None):
    """
    Context manager that sets module arguments for AnsibleModule
    """
    if args is None:
        args = {}

    if '_ansible_remote_tmp' not in args:
        args['_ansible_remote_tmp'] = '/tmp'
    if '_ansible_keep_remote_files' not in args:
        args['_ansible_keep_remote_files'] = False

    if 'hostname' not in args:
        args["hostname"] = "127.0.0.1"
    if 'username' not in args:
        args["username"] = "test"
    if 'password' not in args:
        args["password"] = "test"

    try:
        from ansible.module_utils.testing import patch_module_args
    except ImportError:
        # Before data tagging support was merged (2.19), this was the way to go:
        from ansible.module_utils import basic
        serialized_args = to_bytes(json.dumps({'ANSIBLE_MODULE_ARGS': args}))
        with mock.patch.object(basic, '_ANSIBLE_ARGS', serialized_args):
            yield
    else:
        # With data tagging support, we have a new helper for this:
        with patch_module_args(args):
            yield


class DummyDatacenter:
    pass


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case """
    pass


class AnsibleFailJson(Exception):
    pass


class AnsibleDummyException(Exception):
    pass


def exit_json(*args, **kwargs):
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


class ModuleTestCase:
    def setup_method(self):
        self.mock_module = mock.patch.multiple(
            basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json
        )
        self.mock_module.start()

    def teardown_method(self):
        self.mock_module.stop()
