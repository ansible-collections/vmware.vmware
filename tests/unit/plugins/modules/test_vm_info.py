from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from pyVmomi import vmodl

from ansible_collections.vmware.vmware.plugins.modules import vm_info

from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVmInfo(ModuleTestCase):

    def __prepare(self, mocker):
        init_mock = mocker.patch.object(vm_info.VmwareVmInfo, "__init__")
        init_mock.return_value = None

        gather_info_for_vms = mocker.patch.object(vm_info.VmwareVmInfo, "gather_info_for_vms")
        gather_info_for_vms.return_value = []

    def test_gather(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=vm_info.main, module_args={})
        assert result["changed"] is False


class TestGatherInfoForVms:
    """
    Covers the churn handling added when a VM disappears mid-flight. A VM that
    raises ManagedObjectNotFound should be skipped with a warning rather than
    failing the whole module run.
    """

    def _build_info_instance(self, mocker):
        mocker.patch.object(vm_info.VmwareVmInfo, "__init__", return_value=None)
        info = vm_info.VmwareVmInfo(mocker.Mock())
        info.module = mocker.Mock()
        return info

    def test_skips_missing_vm_and_warns(self, mocker):
        info = self._build_info_instance(mocker)
        present_vm = create_mock_vsphere_object(name="present", moid="vm-1")
        missing_vm = create_mock_vsphere_object(name="missing", moid="vm-2")
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[missing_vm, present_vm]
        )

        def fake_gather(vm):
            if vm is missing_vm:
                raise vmodl.fault.ManagedObjectNotFound()
            return {"name": vm.name}

        mocker.patch.object(
            vm_info.VmwareVmInfo, "_gather_info_about_one_vm", side_effect=fake_gather
        )

        result = info.gather_info_for_vms()

        assert result == [{"name": "present"}]
        info.module.warn.assert_called_once()
        warning_message = info.module.warn.call_args[0][0]
        assert "missing" in warning_message

    def test_includes_all_vms_when_no_errors(self, mocker):
        info = self._build_info_instance(mocker)
        vm1 = create_mock_vsphere_object(name="vm1", moid="vm-1")
        vm2 = create_mock_vsphere_object(name="vm2", moid="vm-2")
        mocker.patch.object(vm_info.VmwareVmInfo, "get_vms", return_value=[vm1, vm2])
        mocker.patch.object(
            vm_info.VmwareVmInfo,
            "_gather_info_about_one_vm",
            side_effect=lambda vm: {"name": vm.name},
        )

        result = info.gather_info_for_vms()

        assert result == [{"name": "vm1"}, {"name": "vm2"}]
        info.module.warn.assert_not_called()

    def test_returns_empty_when_no_vms(self, mocker):
        info = self._build_info_instance(mocker)
        mocker.patch.object(vm_info.VmwareVmInfo, "get_vms", return_value=[])
        gather_one = mocker.patch.object(
            vm_info.VmwareVmInfo, "_gather_info_about_one_vm"
        )

        result = info.gather_info_for_vms()

        assert result == []
        gather_one.assert_not_called()
        info.module.warn.assert_not_called()

    def test_warning_still_skips_when_last_vm_is_missing(self, mocker):
        info = self._build_info_instance(mocker)
        present_vm = create_mock_vsphere_object(name="present", moid="vm-1")
        missing_vm = create_mock_vsphere_object(name="missing", moid="vm-2")
        mocker.patch.object(
            vm_info.VmwareVmInfo, "get_vms", return_value=[present_vm, missing_vm]
        )

        def fake_gather(vm):
            if vm is missing_vm:
                raise vmodl.fault.ManagedObjectNotFound()
            return {"name": vm.name}

        mocker.patch.object(
            vm_info.VmwareVmInfo, "_gather_info_about_one_vm", side_effect=fake_gather
        )

        result = info.gather_info_for_vms()

        assert result == [{"name": "present"}]
        info.module.warn.assert_called_once()


class TestGatherInfoAboutOneVm:
    """
    Covers the _gather_info_about_one_vm helper extracted during the churn fix.
    Both schema branches must attach identity (plus its legacy flattening),
    tags, and env to the returned facts.
    """

    def _build_info_instance(self, mocker):
        mocker.patch.object(vm_info.VmwareVmInfo, "__init__", return_value=None)
        info = vm_info.VmwareVmInfo(mocker.Mock())
        info.module = mocker.Mock()
        info.pyvmomi = mocker.Mock()
        return info

    def test_summary_schema_builds_facts(self, mocker):
        info = self._build_info_instance(mocker)
        info.params = {"schema": "summary"}
        vm = create_mock_vsphere_object(name="vm1", moid="vm-1")

        vm_facts = mocker.patch.object(vm_info, "VmFacts")
        vm_facts.return_value.all_facts.return_value = {"base": "facts"}
        mocker.patch.object(
            vm_info.VmwareVmInfo, "_get_identity", return_value={"guest_os": "linux"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_tags", return_value=["tag1"])
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_env", return_value={"PATH": "/bin"})

        result = info._gather_info_about_one_vm(vm)

        vm_facts.assert_called_once_with(vm)
        assert result["base"] == "facts"
        assert result["identity"] == {"guest_os": "linux"}
        # legacy output flattens identity keys onto the top level
        assert result["guest_os"] == "linux"
        assert result["tags"] == ["tag1"]
        assert result["env"] == {"PATH": "/bin"}

    def test_non_summary_schema_uses_obj_to_json(self, mocker):
        info = self._build_info_instance(mocker)
        info.params = {"schema": "vsphere", "properties": ["name", "config"]}
        vm = create_mock_vsphere_object(name="vm1", moid="vm-1")

        obj_to_json = mocker.patch.object(
            vm_info, "vmware_obj_to_json", return_value={"name": "vm1"}
        )
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_identity", return_value={})
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_tags", return_value=[])
        mocker.patch.object(vm_info.VmwareVmInfo, "_get_env", return_value={})

        result = info._gather_info_about_one_vm(vm)

        obj_to_json.assert_called_once_with(vm, ["name", "config"])
        assert result["name"] == "vm1"
        assert result["identity"] == {}
        assert result["tags"] == []
        assert result["env"] == {}

    def test_managed_object_not_found_propagates(self, mocker):
        """
        _gather_info_about_one_vm must let ManagedObjectNotFound bubble up so
        gather_info_for_vms can catch it and warn.
        """
        info = self._build_info_instance(mocker)
        info.params = {"schema": "summary"}
        vm = create_mock_vsphere_object(name="vm1", moid="vm-1")

        vm_facts = mocker.patch.object(vm_info, "VmFacts")
        vm_facts.return_value.all_facts.side_effect = vmodl.fault.ManagedObjectNotFound()

        with pytest.raises(vmodl.fault.ManagedObjectNotFound):
            info._gather_info_about_one_vm(vm)
