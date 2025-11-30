from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch

from ansible_collections.vmware.vmware.plugins.modules.vm_apply_customization import (
    Identity,
    CloudInitIdentity,
    WinSysprepIdentity,
    UnixPrepIdentity,
    VMCustomizationModule,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ...common.utils import (
    run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object,
    MockVsphereTask
)


class TestCloudInitIdentity():
    def test_static_create_from_params(self):
        params = dict(windows_sysprep=True)
        identity = Identity.create_from_params(params)
        assert isinstance(identity, WinSysprepIdentity)

        params = dict(cloud_init=True)
        identity = Identity.create_from_params(params)
        assert isinstance(identity, CloudInitIdentity)

        params = dict(unix_prep=True)
        identity = Identity.create_from_params(params)
        assert isinstance(identity, UnixPrepIdentity)

    def test_create_identity_spec(self):
        params = dict(instance_data_string='{"foo": "bar"}')
        identity = CloudInitIdentity(params)
        spec = identity.create_identity_spec()
        assert spec is not None
        assert spec.metadata == '{"foo": "bar"}'
        assert not spec.userdata

    def test_create_identity_spec_with_options(self):
        params = dict(
            instance_data={'foo': 'bar'},
            user_data_string="userdata",
        )
        identity = CloudInitIdentity(params)
        spec = identity.create_identity_spec()
        assert spec is not None
        assert spec.metadata == '{"foo": "bar"}'
        assert spec.userdata == "userdata"


class TestWinSysprepIdentity():
    def test_create_identity_spec(self):
        params = dict(
            gui_run_once_commands=['command1', 'command2'],
            auto_logon=True,
            auto_logon_count=2,
            password='password',
            timezone=0,
            domain=dict(
                join_user_name='domainAdmin',
                join_user_password='password',
            ),
            users_full_name='John Doe',
            hostname='foo'
        )
        identity = WinSysprepIdentity(params)
        spec = identity.create_identity_spec()
        assert spec is not None
        assert spec.guiRunOnce.commandList == ['command1', 'command2']
        assert spec.guiUnattended.autoLogon is True
        assert spec.guiUnattended.autoLogonCount == 2
        assert spec.guiUnattended.password is not None
        assert spec.guiUnattended.timeZone == 0
        assert spec.identification.domainAdminPassword.plainText is True
        assert spec.identification.domainAdminPassword.value == 'password'

    def test_create_identity_spec_minimal(self):
        params = dict(auto_logon=True, auto_logon_count=1)
        identity = WinSysprepIdentity(params)
        spec = identity.create_identity_spec()
        assert spec is not None
        assert spec.guiUnattended is not None
        assert spec.identification is not None
        assert spec.userData is not None


class TestUnixPrepIdentity():
    def test_create_identity_spec(self):
        params = dict(
            domain='unixprep.local',
            hostname='foo',
            hardware_clock_utc=True,
            timezone='America/New_York',
            script_string='#!/bin/sh\necho "Hello, World!"'
        )
        identity = UnixPrepIdentity(params)
        spec = identity.create_identity_spec()
        assert spec.hostName.name == 'foo'
        assert spec.hwClockUTC is True
        assert spec.timeZone == 'America/New_York'
        assert spec.scriptText == '#!/bin/sh\necho "Hello, World!"'

    def test_create_identity_spec_minimal(self):
        params = dict(domain='unixprep.local', hostname='foo')
        identity = UnixPrepIdentity(params)
        spec = identity.create_identity_spec()
        assert spec is not None
        assert spec.domain == 'unixprep.local'
        assert spec.hostName.name == 'foo'
        assert spec.hwClockUTC is None
        assert spec.timeZone is None
        assert spec.scriptText is None


class TestVmApplyCustomization(ModuleTestCase):

    def __prepare(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        self.vm_mock = create_mock_vsphere_object()
        mocker.patch.object(VMCustomizationModule, 'get_vms_using_params', return_value=([self.vm_mock]))
        self.vm_mock.CustomizeVM_Task.return_value = MockVsphereTask()

        self.identity_mock = mocker.Mock()
        self.identity_mock.create_identity_spec.return_value = mocker.Mock()
        mocker.patch.object(Identity, 'create_from_params', return_value=self.identity_mock)

    @patch('ansible_collections.vmware.vmware.plugins.modules.vm_apply_customization.vim.vm.customization.Specification')
    def test_customize_minimal(self, specification_mock, mocker):
        self.__prepare(mocker)
        specification_mock.return_value = mocker.Mock()
        mock_nic = mocker.Mock()
        mock_nic.macAddress = '00:00:00:00:00:00'
        self.vm_mock.config.hardware.device = [mock_nic]
        module_args = dict(
            name="vm1",
            global_dns=dict(servers=['1.1.1.1', '1.0.0.1'], resolution_suffixes=['example.com']),
            windows_sysprep=dict(auto_logon=True, auto_logon_count=1, password='password', timezone=0),
            use_dhcpv4_for_all_nics=True,
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.vm_mock.CustomizeVM_Task.assert_called_once()
        self.identity_mock.create_identity_spec.assert_called_once()

    @patch('ansible_collections.vmware.vmware.plugins.modules.vm_apply_customization.vim.vm.customization.Specification')
    def test_customize_with_custom_nic_settings(self, specification_mock, mocker):
        self.__prepare(mocker)
        specification_mock.return_value = mocker.Mock()
        mock_nic = mocker.Mock()
        mock_nic.macAddress = '00:00:00:00:00:00'
        self.vm_mock.config.hardware.device = [mock_nic]
        module_args = dict(
            name="vm1",
            global_dns=dict(servers=['1.1.1.1', '1.0.0.1'], resolution_suffixes=['example.com']),
            windows_sysprep=dict(auto_logon=True, auto_logon_count=1, password='password', timezone=0),
            use_dhcpv4_for_all_nics=False,
            nic_specific_settings=[
                dict(
                    mac_address='00:00:00:00:00:00',
                    ipv4=dict(),
                    netbios_mode='disableNetBIOS',
                    primary_wins_server='192.168.1.1',
                    secondary_wins_server='192.168.1.2',
                    ipv6=dict(),
                ),
                dict(
                    mac_address='00:00:00:00:00:01',
                    ipv4=dict(
                        address='192.168.1.101',
                        subnet_mask='255.255.255.0',
                        gateways=['192.168.1.1'],
                    ),
                    dns_servers=['1.1.1.1', '1.0.0.1'],
                    resolution_suffix='example.com',
                    ipv6=dict(
                        address='2001:db8::1',
                        subnet_mask=128,
                        gateways=['2001:db8::1'],
                    ),
                ),
            ],
        )

        result = run_module(module_entry=module_main, module_args=module_args)

        assert result["changed"] is True
        self.vm_mock.CustomizeVM_Task.assert_called_once()
        self.identity_mock.create_identity_spec.assert_called_once()
