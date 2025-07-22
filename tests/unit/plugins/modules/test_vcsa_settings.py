from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from types import SimpleNamespace

from ansible_collections.vmware.vmware.plugins.modules import vcsa_settings
from ansible_collections.vmware.vmware.plugins.module_utils.clients.rest import (
    VmwareRestClient
)

from ...common.utils import (
    run_module, ModuleTestCase
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestVcsaSettings(ModuleTestCase):

    def __prepare(self, mocker):
        self.api_client_mock = mocker.Mock()
        mocker.patch.object(VmwareRestClient, 'connect_to_api', return_value=self.api_client_mock)

    def mock_proxy_list(self, default_args, changed_args):
        # using a mock object here causes issues with json and attribute comparison
        proxy_mock = SimpleNamespace(**default_args)
        for key, value in changed_args.items():
            setattr(proxy_mock, key, value)

        proxy_mock.server = proxy_mock.url
        del proxy_mock.url

        self.api_client_mock.appliance.networking.Proxy.list.return_value = {
            'http': proxy_mock
        }
        return proxy_mock

    def test_basic_module_execution(self, mocker):
        """Test basic module execution without any parameters"""
        self.__prepare(mocker)

        result = run_module(
            module_entry=vcsa_settings.main,
            module_args={}
        )

        assert result["changed"] is False
        assert "vcsa_settings" in result
        assert "vcsa" in result

    def test_proxy_no_change_needed(self, mocker):
        self.__prepare(mocker)

        module_args = {
            "proxy": [
                {
                    "enabled": True,
                    "url": "http://localhost",
                    "port": 8080,
                    "protocol": "http"
                }
            ]
        }
        # Mock the current proxy state to match desired state
        self.mock_proxy_list(module_args["proxy"][0], {})

        result = run_module(
            module_entry=vcsa_settings.main,
            module_args=module_args
        )

        assert result["changed"] is False
        assert "proxy" in result["vcsa_settings"]

    def test_proxy_change_needed_enable(self, mocker):
        self.__prepare(mocker)

        module_args = {
            "proxy": [
                {
                    "enabled": True,
                    "url": "http://localhost",
                    "port": 8080,
                    "protocol": "http"
                }
            ]
        }

        self.mock_proxy_list(module_args["proxy"][0], {'enabled': False})
        result = run_module(
            module_entry=vcsa_settings.main,
            module_args=module_args
        )

        assert result["changed"] is True
        assert "proxy" in result["vcsa_settings"]
        assert self.api_client_mock.appliance.networking.Proxy.set.call_count == 1

        self.api_client_mock.appliance.networking.Proxy.set.reset_mock()
        self.mock_proxy_list(module_args["proxy"][0], {'url': 'http://foo', 'enabled': True})
        result = run_module(
            module_entry=vcsa_settings.main,
            module_args=module_args
        )

        assert result["changed"] is True
        assert "proxy" in result["vcsa_settings"]
        assert self.api_client_mock.appliance.networking.Proxy.set.call_count == 1

    def test_proxy_change_needed_disable(self, mocker):
        self.__prepare(mocker)

        module_args = {
            "proxy": [
                {
                    "enabled": False,
                    "url": "http://localhost",
                    "port": 8080,
                    "protocol": "http"
                }
            ]
        }

        self.mock_proxy_list(module_args["proxy"][0], {'enabled': True})
        result = run_module(
            module_entry=vcsa_settings.main,
            module_args=module_args
        )

        assert result["changed"] is True
        assert "proxy" in result["vcsa_settings"]
        assert self.api_client_mock.appliance.networking.Proxy.set.call_count == 1

    def test_proxy_no_proxy_config(self, mocker):
        self.__prepare(mocker)

        module_args = {}  # No proxy config

        result = run_module(
            module_entry=vcsa_settings.main,
            module_args=module_args
        )

        assert result["changed"] is False
        assert "vcsa_settings" in result
        # Should not call proxy list or set methods
        assert not hasattr(self.api_client_mock.appliance.networking.Proxy, 'list') or \
               self.api_client_mock.appliance.networking.Proxy.list.call_count == 0
