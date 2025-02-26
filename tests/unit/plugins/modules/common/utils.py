from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes

import mock


def set_module_args(add_cluster=True, **args):
    if '_ansible_remote_tmp' not in args:
        args['_ansible_remote_tmp'] = '/tmp'
    if '_ansible_keep_remote_files' not in args:
        args['_ansible_keep_remote_files'] = False
    if add_cluster and 'cluster_name' not in args:
        args["cluster_name"] = "mycluster"
    if 'hostname' not in args:
        args["hostname"] = "127.0.0.1"
    if 'username' not in args:
        args["username"] = "test"
    if 'password' not in args:
        args["password"] = "test"

    args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
    basic._ANSIBLE_ARGS = to_bytes(args)


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
