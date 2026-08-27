from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules import esxi_info
from ansible_collections.vmware.vmware.plugins.modules.esxi_info import (
    EsxiInfo,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)

from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import MockEsxiHost

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestEsxiInfo(ModuleTestCase):

    def __prepare(self, mocker, all_facts=None):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        esxi_facts_cls = mocker.patch.object(esxi_info, 'EsxiFacts')
        esxi_facts_cls.return_value.all_facts.return_value = (
            all_facts if all_facts is not None else {"name": "test", "moid": "host-1"}
        )

    def test_gather_by_name(self, mocker):
        self.__prepare(mocker)
        host = MockEsxiHost(name="esxi01", moid="host-1")
        mocker.patch.object(EsxiInfo, 'get_esxi_host_by_name_or_moid', return_value=host)

        result = run_module(module_entry=module_main, module_args=dict(esxi_host_name="esxi01"))

        assert result["changed"] is False
        assert len(result["hosts"]) == 1
        assert result["hosts"][0]["name"] == "test"
        assert result["hosts"][0]["tags"] == []

    def test_gather_by_moid(self, mocker):
        self.__prepare(mocker)
        host = MockEsxiHost(name="esxi01", moid="host-1")
        get_host = mocker.patch.object(EsxiInfo, 'get_esxi_host_by_name_or_moid', return_value=host)

        result = run_module(module_entry=module_main, module_args=dict(moid="host-1"))

        get_host.assert_called_once()
        assert len(result["hosts"]) == 1

    def test_gather_by_cluster(self, mocker):
        self.__prepare(mocker)
        cluster = mocker.Mock()
        cluster.host = [MockEsxiHost(moid="host-1"), MockEsxiHost(moid="host-2")]
        mocker.patch.object(EsxiInfo, 'get_cluster_by_name_or_moid', return_value=cluster)

        result = run_module(module_entry=module_main, module_args=dict(cluster="my_cluster"))

        assert len(result["hosts"]) == 2

    def test_gather_by_datacenter(self, mocker):
        self.__prepare(mocker)
        datacenter = mocker.Mock()
        datacenter.hostFolder = "FOLDER"
        mocker.patch.object(EsxiInfo, 'get_datacenter_by_name_or_moid', return_value=datacenter)
        get_all = mocker.patch.object(
            EsxiInfo, 'get_all_objs_by_type', return_value=[MockEsxiHost(moid="host-1")]
        )

        result = run_module(module_entry=module_main, module_args=dict(datacenter="my_dc"))

        assert len(result["hosts"]) == 1
        assert get_all.call_args.kwargs["folder"] == "FOLDER"

    def test_gather_all(self, mocker):
        self.__prepare(mocker)
        get_all = mocker.patch.object(
            EsxiInfo, 'get_all_objs_by_type',
            return_value=[MockEsxiHost(moid="host-1"), MockEsxiHost(moid="host-2")]
        )

        result = run_module(module_entry=module_main, module_args={})

        assert len(result["hosts"]) == 2
        assert get_all.call_args.kwargs["folder"] is None

    def test_schema_vsphere(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        host = MockEsxiHost(moid="host-1")
        mocker.patch.object(EsxiInfo, 'get_esxi_host_by_name_or_moid', return_value=host)
        mocker.patch.object(
            esxi_info, 'vmware_obj_to_json', return_value={"overallStatus": "green"}
        )

        result = run_module(module_entry=module_main, module_args=dict(
            esxi_host_name="esxi01",
            schema="vsphere",
            properties=["overallStatus"],
        ))

        assert result["hosts"] == [{"overallStatus": "green"}]
        # tags are not gathered/added in the vsphere schema path
        assert "tags" not in result["hosts"][0]

    def test_schema_vsphere_attribute_error(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        host = MockEsxiHost(moid="host-1")
        mocker.patch.object(EsxiInfo, 'get_esxi_host_by_name_or_moid', return_value=host)
        mocker.patch.object(
            esxi_info, 'vmware_obj_to_json', side_effect=AttributeError("bad property")
        )

        result = run_module(module_entry=module_main, module_args=dict(
            esxi_host_name="esxi01",
            schema="vsphere",
            properties=["bad property"],
        ), expect_success=False)

        assert result["failed"] is True
        assert "bad property" in result["msg"]

    def test_properties_without_vsphere_schema_fails(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))

        result = run_module(module_entry=module_main, module_args=dict(
            esxi_host_name="esxi01",
            properties=["hardware.memorySize"],
        ), expect_success=False)

        assert result["failed"] is True
        assert "properties" in result["msg"]

    def test_gather_tags(self, mocker):
        self.__prepare(mocker)
        host = MockEsxiHost(moid="host-1")
        mocker.patch.object(EsxiInfo, 'get_esxi_host_by_name_or_moid', return_value=host)

        rest_instance = mocker.Mock()
        rest_instance.get_tags_by_host_moid.return_value = ["tag-obj"]
        rest_instance.format_tag_identity_as_dict.return_value = {"name": "my_tag"}
        mocker.patch.object(esxi_info, 'ModuleRestBase', return_value=rest_instance)

        result = run_module(module_entry=module_main, module_args=dict(
            esxi_host_name="esxi01",
            gather_tags=True,
        ))

        assert result["hosts"][0]["tags"] == [{"name": "my_tag"}]
        rest_instance.get_tags_by_host_moid.assert_called_once_with("host-1")
