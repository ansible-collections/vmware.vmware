from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils import basic
from ansible.module_utils._text import to_bytes
from ansible_collections.vmware.vmware.plugins.module_utils import _vmware

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


def mock_pyvmomi(mocker):
    connect_to_api = mocker.patch.object(_vmware, "connect_to_api")
    _content = type('', (), {})()
    _content.customFieldsManager = False
    connect_to_api.return_value = None, _content


class DummyDatacenter:
    pass


class AnsibleExitJson(Exception):
    """Exception class to be raised by module.exit_json and caught by the test case """
    pass


class AnsibleFailJson(Exception):
    pass


class AnsibleDummyException(Exception):
    pass


def raise_dummy_exception(*args, **kwargs):
    raise AnsibleDummyException()


def exit_json(*args, **kwargs):
    if 'changed' not in kwargs:
        kwargs['changed'] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*args, **kwargs):
    """function to patch over fail_json; package return data into an exception """
    kwargs['failed'] = True
    raise AnsibleFailJson(kwargs)


def resource_task_success(*args, **kwargs):
    task_mock = mock.Mock()
    task_mock.info = mock.Mock()
    task_mock.info.state = "success"
    return task_mock


def resource_task_fail(*args, **kwargs):
    task_mock = mock.Mock()
    task_mock.info = mock.Mock()
    task_mock.info.state = "error"
    return task_mock


class ModuleTestCase:
    def setup_method(self):
        self.mock_module = mock.patch.multiple(
            basic.AnsibleModule, exit_json=exit_json, fail_json=fail_json,
        )
        self.mock_module.start()

    def teardown_method(self):
        self.mock_module.stop()


def generate_name(test_case):
    return test_case['name']
