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
    AnsibleExitJson, ModuleTestCase, set_module_args,
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

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datastores_to_add=ds_to_add
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert set(c.value.args[0]["added_datastores"]) == set(ds_to_add)
        assert len(c.value.args[0]["removed_datastores"]) == 0

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name=ds_to_add[0])
        ]
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datastores_to_add=ds_to_add
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert len(c.value.args[0]["added_datastores"]) == 0
        assert len(c.value.args[0]["removed_datastores"]) == 0

    def test_remove(self, mocker):
        self.__prepare(mocker)

        ds_to_remove = ['ds1']

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datastores_to_remove=ds_to_remove
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert len(c.value.args[0]["added_datastores"]) == 0
        assert len(c.value.args[0]["removed_datastores"]) == 0

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name=ds_to_remove[0])
        ]
        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            datastores_to_remove=ds_to_remove
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert len(c.value.args[0]["added_datastores"]) == 0
        assert set(c.value.args[0]["removed_datastores"]) == set(ds_to_remove)

    def test_absolute_list(self, mocker):
        self.__prepare(mocker)

        allowed_datastores = ['ds3']
        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds1'),
            create_mock_vsphere_object(name='ds2'),
            create_mock_vsphere_object(name='ds3'),
        ]

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            allowed_datastores=allowed_datastores
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert set(c.value.args[0]["added_datastores"]) == set([])
        assert set(c.value.args[0]["removed_datastores"]) == set(['ds1', 'ds2'])

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds3'),
        ]

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            allowed_datastores=allowed_datastores
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is False
        assert set(c.value.args[0]["added_datastores"]) == set([])
        assert set(c.value.args[0]["removed_datastores"]) == set([])

        self.test_cluster.configurationEx.systemVMsConfig.allowedDatastores = [
            create_mock_vsphere_object(name='ds1'),
        ]

        set_module_args(
            hostname="127.0.0.1",
            username="administrator@local",
            password="123456",
            allowed_datastores=allowed_datastores
        )

        with pytest.raises(AnsibleExitJson) as c:
            module_main()

        assert c.value.args[0]["changed"] is True
        assert set(c.value.args[0]["added_datastores"]) == set(allowed_datastores)
        assert set(c.value.args[0]["removed_datastores"]) == set(['ds1'])
