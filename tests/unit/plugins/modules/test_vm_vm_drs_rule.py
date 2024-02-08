from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import vm_vm_drs_rule

from .common.utils import (
    AnsibleExitJson, ModuleTestCase, set_module_args,
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestAffinity(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(vm_vm_drs_rule.PyVmomi, "__init__")
        init_mock.return_value = None

        get_all_vms_info = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "get_all_vms_info")
        get_all_vms_info.return_value = []

        find_cluster_by_name = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "find_cluster_by_name")
        find_cluster_by_name.return_value = {}

    def test_create(self, mocker):
        self.__prepare(mocker)
        create_mock = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "create")
        create_mock.return_value = True, None

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            cluster_name="mycluster",
            vms=["vm1", "vm2"],
            drs_rule_name="myrule",
        )

        with pytest.raises(AnsibleExitJson) as c:
            vm_vm_drs_rule.main()

        assert c.value.args[0]["changed"] == True

    def test_update(self, mocker):
        self.__prepare(mocker)
        get_rule = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "get_rule_key_by_name")
        get_rule.return_value = {'key': 0}
        normalize_rule = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "normalize_rule_spec")
        normalize_rule.return_value = {'rule_vms': [], 'rule_enabled': False, 'rule_mandatory': False, 'rule_affinity': True}
        update_rule = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "update_rule_spec")
        update_rule.return_value = True, None

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            cluster_name="mycluster",
            vms=["vm1", "vm2"],
            drs_rule_name="myrule",
        )

        with pytest.raises(AnsibleExitJson) as c:
            vm_vm_drs_rule.main()

        assert c.value.args[0]["changed"] == True    

    def test_absent(self, mocker):
        self.__prepare(mocker)
        delete_mock = mocker.patch.object(vm_vm_drs_rule.VmwareDrs, "delete")
        delete_mock.return_value = True, None

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            cluster_name="mycluster",
            vms=["vm1", "vm2"],
            drs_rule_name="myrule",
            state='absent',
        )

        with pytest.raises(AnsibleExitJson) as c:
            vm_vm_drs_rule.main()

        assert c.value.args[0]["changed"] == True
