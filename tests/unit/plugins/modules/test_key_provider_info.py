from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.key_provider_info import (
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient,
)
from ...common.utils import run_module, ModuleTestCase

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestKeyProviderInfo(ModuleTestCase):

    def _mock_kmip_clusters(self, mocker):
        native_cluster = mocker.Mock(
            spec=[
                "clusterId",
                "managementType",
                "useAsDefault",
                "tpmRequired",
                "hasBackup",
            ]
        )
        native_cluster.clusterId.id = "native-1"
        native_cluster.managementType = "nativeProvider"
        native_cluster.useAsDefault = True
        native_cluster.tpmRequired = True
        native_cluster.hasBackup = True

        standard_server = mocker.Mock()
        standard_server.name = "kms-1"
        standard_server.address = "10.0.0.1"
        standard_server.port = 5696
        standard_server.userName = "kmsuser"
        standard_server.proxyAddress = "10.0.0.2"
        standard_server.proxyPort = 5697

        standard_cluster = mocker.Mock()
        standard_cluster.clusterId.id = "standard-1"
        standard_cluster.managementType = "vCenter"
        standard_cluster.useAsDefault = False
        standard_cluster.servers = [standard_server]

        return [native_cluster, standard_cluster]

    def __prepare(self, mocker):
        content_mock = mocker.Mock()
        content_mock.cryptoManager.kmipServers = self._mock_kmip_clusters(mocker)
        si_mock = mocker.Mock()
        si_mock.content = content_mock
        mocker.patch.object(
            PyvmomiClient, "connect_to_api", return_value=(si_mock, content_mock)
        )

    def test_gather_all(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main)

        assert result["changed"] is False
        assert result["key_providers"]["native-1"] == {
            "id": "native-1",
            "type": "native",
            "default": True,
            "tpm_required": True,
            "backed_up": True,
        }
        assert result["key_providers"]["standard-1"]["type"] == "standard"
        assert result["key_providers"]["standard-1"]["servers"] == [
            {
                "id": "kms-1",
                "address": "10.0.0.1",
                "port": 5696,
                "username": "kmsuser",
                "proxy_address": "10.0.0.2",
                "proxy_port": 5697,
            }
        ]

    def test_filter_by_name(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args={"provider_name": "standard-1"},
        )

        assert list(result["key_providers"].keys()) == ["standard-1"]

    def test_filter_by_type(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args={"type": "native"})

        assert list(result["key_providers"].keys()) == ["native-1"]
