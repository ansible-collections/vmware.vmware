from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from unittest import mock

from ansible_collections.vmware.vmware.plugins.modules.key_provider_native import (
    NativeKeyProviderModule,
    main as module_main,
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient,
)
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import (
    ModulePyvmomiBase,
)
from ...common.utils import run_module, ModuleTestCase

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestKeyProviderNative(ModuleTestCase):

    def __prepare(self, mocker):
        self.rest_client = mocker.Mock()
        mocker.patch.object(
            VmwareRestClient, "connect_to_api", return_value=self.rest_client
        )
        self.providers_service = self.rest_client.vcenter.crypto_manager.kms.Providers
        self.providers_service.CreateSpec = mock.Mock(side_effect=self._create_spec)
        self.providers_service.ConstraintsSpec = mock.Mock(side_effect=mock.Mock)
        self.providers_service.ExportSpec = mock.Mock(side_effect=mock.Mock)

        crypto_manager = mocker.Mock()
        default_id = mocker.Mock()
        default_id.id = "other-provider"
        crypto_manager.GetDefaultKmsCluster.return_value = default_id
        pyvmomi_base = mocker.patch.object(ModulePyvmomiBase, "__init__", return_value=None)
        pyvmomi_base.return_value = None
        mocker.patch.object(
            NativeKeyProviderModule,
            "pyvmomi_crypto_manager",
            new_callable=mocker.PropertyMock,
            return_value=crypto_manager,
        )
        self.crypto_manager = crypto_manager

    def _create_spec(self, provider_name, constraints=None):
        spec = mock.Mock()
        spec.provider_name = provider_name
        spec.constraints = constraints
        return spec

    def _mock_export_response(self):
        export_response = mock.Mock()
        export_response.location.url = "https://vcenter/export"
        export_response.location.download_token.token = "token-123"
        export_response.location.download_token.expiry = "2026-05-18T16:57:06"
        return export_response

    def test_create_present(self, mocker):
        self.__prepare(mocker)
        self.providers_service.get.return_value = None
        self.providers_service.create.return_value = mock.Mock()
        self.providers_service.export.return_value = self._mock_export_response()

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "new-native",
                "state": "present",
                "export_password": "backup-password",
            },
        )

        assert result["changed"] is True
        assert result["export_info"] == {
            "url": "https://vcenter/export",
            "token": "token-123",
            "expires_at": "2026-05-18T16:57:06",
        }
        self.providers_service.create.assert_called_once()
        self.providers_service.export.assert_called_once()

    def test_present_no_change(self, mocker):
        self.__prepare(mocker)
        self.providers_service.get.return_value = mock.Mock()

        result = run_module(
            module_entry=module_main,
            module_args={"provider_name": "existing-native", "state": "present"},
        )

        assert result["changed"] is False
        self.providers_service.create.assert_not_called()

    def test_set_default(self, mocker):
        self.__prepare(mocker)
        self.providers_service.get.return_value = mock.Mock()
        default_id = mock.Mock()
        default_id.id = "other-provider"
        self.crypto_manager.GetDefaultKmsCluster.return_value = default_id

        result = run_module(
            module_entry=module_main,
            module_args={
                "provider_name": "existing-native",
                "state": "present",
                "default_provider": True,
            },
        )

        assert result["changed"] is True
        self.crypto_manager.MarkDefault.assert_called_once()

    def test_absent(self, mocker):
        self.__prepare(mocker)
        self.providers_service.get.return_value = mock.Mock()

        result = run_module(
            module_entry=module_main,
            module_args={"provider_name": "existing-native", "state": "absent"},
        )

        assert result["changed"] is True
        self.providers_service.delete.assert_called_once_with("existing-native")

    def test_absent_no_change(self, mocker):
        self.__prepare(mocker)
        self.providers_service.get.return_value = None

        result = run_module(
            module_entry=module_main,
            module_args={"provider_name": "missing-native", "state": "absent"},
        )

        assert result["changed"] is False
        self.providers_service.delete.assert_not_called()
