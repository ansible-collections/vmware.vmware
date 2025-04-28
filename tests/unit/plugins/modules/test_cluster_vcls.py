from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest
from pyVmomi import vim

from ansible_collections.vmware.vmware.plugins.modules.cluster_vcls import (
    VMwareClusterVcls,
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

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)


class TestClusterVcls(ModuleTestCase):
    def __prepare(self, mocker):
        self.test_cluster = create_mock_vsphere_object()
        self.test_task = MockVsphereTask()
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VMwareClusterVcls, 'get_datacenter_by_name_or_moid')
        mocker.patch.object(VMwareClusterVcls, 'get_datastore_by_name_or_moid', return_value=mocker.Mock(spec=vim.Datastore))
        mocker.patch.object(VMwareClusterVcls, 'get_cluster_by_name_or_moid', return_value=self.test_cluster)

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = []
        self.test_cluster.ReconfigureComputeResource_Task.return_value = self.test_task

    def test_add(self, mocker):
        self.__prepare(mocker)

        ds_to_add = ['ds1']

        module_args = dict(
            cluster='foo',
            datastores_to_add=ds_to_add
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert set(result["added_datastores"]) == set(ds_to_add)
        assert len(result["removed_datastores"]) == 0

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name=ds_to_add[0])
        ]
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert len(result["added_datastores"]) == 0
        assert len(result["removed_datastores"]) == 0

    def test_remove(self, mocker):
        self.__prepare(mocker)

        ds_to_remove = ['ds1']
        module_args = dict(
            cluster='foo',
            datastores_to_remove=ds_to_remove
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert len(result["added_datastores"]) == 0
        assert len(result["removed_datastores"]) == 0

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name=ds_to_remove[0])
        ]
        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert len(result["added_datastores"]) == 0
        assert set(result["removed_datastores"]) == set(ds_to_remove)

    def test_absolute_list(self, mocker):
        self.__prepare(mocker)

        allowed_datastores = ['ds3']
        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds1'),
            create_mock_vsphere_object(name='ds2'),
            create_mock_vsphere_object(name='ds3'),
        ]

        module_args = dict(
            cluster='foo',
            allowed_datastores=allowed_datastores
        )

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert set(result["added_datastores"]) == set([])
        assert set(result["removed_datastores"]) == set(['ds1', 'ds2'])

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds3'),
        ]

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is False
        assert set(result["added_datastores"]) == set([])
        assert set(result["removed_datastores"]) == set([])

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds1'),
        ]

        result = run_module(module_entry=module_main, module_args=module_args)
        assert result["changed"] is True
        assert set(result["added_datastores"]) == set(allowed_datastores)
        assert set(result["removed_datastores"]) == set(['ds1'])
