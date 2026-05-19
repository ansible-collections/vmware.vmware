from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from ansible_collections.vmware.vmware.plugins.modules.key_provider_standard import (
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient,
)
from ...common.utils import run_module, ModuleTestCase

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestKeyProviderStandard(ModuleTestCase):

    def _mock_kms_server(self, mocker, server_id="kms-1"):
        server = mocker.Mock()
        server.name = server_id
        server.address = "10.0.0.1"
        server.port = 5696
        server.proxyAddress = "10.0.0.2"
        server.proxyPort = 5697
        server.userName = "kmsuser"
        return server

    def _mock_cluster(self, mocker, servers=None, use_as_default=False):
        cluster = mocker.Mock()
        cluster.clusterId.id = "standard-1"
        cluster.useAsDefault = use_as_default
        cluster.servers = servers or [self._mock_kms_server(mocker)]
        return cluster

    def __prepare(self, mocker, clusters=None):
        content_mock = mocker.Mock()
        content_mock.cryptoManager = mocker.Mock()
        content_mock.cryptoManager.kmipServers = clusters or []
        si_mock = mocker.Mock()
        si_mock.content = content_mock
        mocker.patch.object(
            PyvmomiClient, "connect_to_api", return_value=(si_mock, content_mock)
        )
        self.crypto_manager = content_mock.cryptoManager

    def _kms_server_args(self, server_id="kms-1", address="10.0.0.1"):
        return {
            "id": server_id,
            "address": address,
            "port": 5696,
            "proxy_address": "10.0.0.2",
            "proxy_port": 5697,
            "username": "kmsuser",
            "password": "kms-password",
        }

    def test_create_cluster(self, mocker):
        self.__prepare(mocker)

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "kms_servers": [self._kms_server_args()],
            },
        )

        assert result["changed"] is True
        assert result["modified_kms_servers"] == ["kms-1"]
        self.crypto_manager.RegisterKmipServer.assert_called_once()

    def test_present_no_change(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "always_update_password": False,
                "kms_servers": [self._kms_server_args()],
            },
        )

        assert result["changed"] is False
        assert result["modified_kms_servers"] == []

    def test_update_server(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "always_update_password": False,
                "kms_servers": [self._kms_server_args(address="10.0.0.99")],
            },
        )

        assert result["changed"] is True
        assert result["modified_kms_servers"] == ["kms-1"]
        self.crypto_manager.UpdateKmipServer.assert_called_once()

    def test_add_server(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "always_update_password": False,
                "kms_servers": [
                    self._kms_server_args(),
                    self._kms_server_args(server_id="kms-2", address="10.0.0.3"),
                ],
            },
        )

        assert result["changed"] is True
        assert result["modified_kms_servers"] == ["kms-2"]
        self.crypto_manager.RegisterKmipServer.assert_called_once()

    def test_remove_server(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "kms_servers_state": "absent",
                "kms_servers": [{"id": "kms-1"}],
            },
        )

        assert result["changed"] is True
        assert result["modified_kms_servers"] == ["kms-1"]
        self.crypto_manager.RemoveKmipServer.assert_called_once()

    def test_set_default(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "standard-1",
                "state": "present",
                "default_provider": True,
                "kms_servers": [self._kms_server_args()],
            },
        )

        assert result["changed"] is True
        self.crypto_manager.MarkDefault.assert_called_once()

    def test_absent(self, mocker):
        self.__prepare(mocker, clusters=[self._mock_cluster(mocker)])

        result = run_module(
            module_entry=module_main,
            module_args={"provider_name": "standard-1", "state": "absent"},
        )

        assert result["changed"] is True
        self.crypto_manager.UnregisterKmsCluster.assert_called_once()
