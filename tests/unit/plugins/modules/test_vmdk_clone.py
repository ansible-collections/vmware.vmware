from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import pytest

from pyVmomi import vim

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.vmware.vmware.plugins.modules.vmdk_clone import (
    VmdkCloneModule,
    default_format,
    find_lun,
    lun_volume,
    same_format,
    main as module_main
)
from ansible_collections.vmware.vmware.plugins.module_utils.clients.pyvmomi import (
    PyvmomiClient
)
from ansible_collections.vmware.vmware.plugins.module_utils._vmdk import (
    VmdkFiles,
    VmdkPath
)
from ansible_collections.vmware.vmware.plugins.module_utils._vsphere_tasks import (
    TaskError
)
from ...common.utils import (
    AnsibleFailJson, run_module, ModuleTestCase
)
from ...common.vmware_object_mocks import (
    create_mock_vsphere_object
)

pytestmark = pytest.mark.skipif(
    sys.version_info < (2, 7), reason="requires python2.7 or higher"
)

SOURCE = '[ds1] vm1/vm1.vmdk'
DESTINATION = '[ds1] copy/vm1.vmdk'
LUN_NAME = 'naa.624a93706c1b16ce1c034d1c0638cb69'


def make_lun(name=LUN_NAME, blocks=4096, block_size=512):
    return vim.host.ScsiDisk(
        canonicalName=name, uuid='0200' + name, deviceName='/vmfs/devices/disks/' + name,
        devicePath='/vmfs/devices/disks/' + name,
        capacity=vim.host.DiskDimensions.Lba(block=blocks, blockSize=block_size))


def make_host(mocker, luns=None, volumes=None):
    host = create_mock_vsphere_object(name='esxi1')
    host.config.storageDevice.scsiLun = luns if luns is not None else [make_lun()]
    host.config.fileSystemVolume.mountInfo = [mocker.Mock(volume=volume) for volume in volumes or []]
    return host


def vmfs_volume(name, lun_name):
    return vim.host.VmfsVolume(name=name, extent=[vim.host.ScsiDisk.Partition(diskName=lun_name, partition=1)])


@pytest.mark.parametrize('disk_format, provisioning, expected', [
    (None, 'thin', True),
    ('thin', 'thin', True),
    ('zeroedthick', 'thick', True),
    ('eagerzeroedthick', 'thick', True),
    ('eagerzeroedthick', 'eagerzeroedthick', True),
    ('eagerzeroedthick', 'thin', False),
    ('thin', 'zeroedthick', False),
    ('rdm', 'thin', False),
])
def test_same_format(disk_format, provisioning, expected):
    assert same_format(disk_format, provisioning) is expected


@pytest.mark.parametrize('provisioning, expected', [
    ('thin', 'thin'), ('thick', 'zeroedthick'), ('eagerzeroedthick', 'zeroedthick'), ('rdm', 'zeroedthick'), (None, 'zeroedthick'),
])
def test_default_format(provisioning, expected):
    assert default_format(provisioning) == expected


def test_find_lun(mocker):
    lun = make_lun()
    host = make_host(mocker, luns=[vim.host.ScsiLun(canonicalName='mpx.cdrom'), lun])
    assert find_lun(host, LUN_NAME) is lun
    assert find_lun(host, '/vmfs/devices/disks/' + LUN_NAME) is lun
    assert find_lun(host, '0200' + LUN_NAME) is lun
    assert find_lun(host, 'naa.missing') is None
    assert find_lun(host, 'mpx.cdrom') is None


def test_lun_volume(mocker):
    lun = make_lun()
    host = make_host(mocker, volumes=[vmfs_volume('other', 'naa.other'), vmfs_volume('ds9', LUN_NAME)])
    assert lun_volume(host, lun) == 'ds9'
    assert lun_volume(make_host(mocker), lun) is None


class TestVmdkClone(ModuleTestCase):

    def __prepare(self, mocker, vcenter=False, source_facts=None, destination_exists=False, folder_exists=True,
                  users=None, host=None):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmdkCloneModule, 'is_vcenter', return_value=vcenter)
        datastore = create_mock_vsphere_object(name='ds1')
        paths = {
            SOURCE: VmdkPath(datastore, mocker.Mock(), SOURCE),
            DESTINATION: VmdkPath(datastore, mocker.Mock(), DESTINATION),
        }
        mocker.patch.object(VmdkFiles, 'resolve', side_effect=lambda value, option: paths[value])

        self.source_info = mocker.Mock(capacityKb=1024, controllerType=vim.vm.device.VirtualIDEController)
        self.destination_info = mocker.Mock() if destination_exists else None
        mocker.patch.object(VmdkFiles, 'file_info', side_effect=lambda path: (
            self.source_info if path.ds_path == SOURCE else self.destination_info))
        source_facts = source_facts or {'path': SOURCE, 'exists': True, 'provisioning': 'thin'}
        mocker.patch.object(VmdkFiles, 'facts', side_effect=lambda path, info: (
            source_facts if path.ds_path == SOURCE else {'path': DESTINATION, 'exists': info is not None, 'provisioning': 'thin'}))
        mocker.patch.object(VmdkFiles, 'describe', return_value={'path': DESTINATION, 'exists': True, 'provisioning': 'rdm'})
        mocker.patch.object(VmdkCloneModule, 'folder_exists', return_value=folder_exists)
        mocker.patch.object(VmdkFiles, 'users', return_value=users or [])
        self.make_folder = mocker.patch.object(VmdkCloneModule, 'make_folder')
        self.wait = mocker.patch.object(VmdkFiles, 'wait')
        mocker.patch.object(VmdkCloneModule, 'get_all_objs_by_type', return_value=[host or make_host(mocker)])

    def manager(self, mocker):
        return PyvmomiClient.connect_to_api.return_value[1].virtualDiskManager

    def test_clone_through_vcenter(self, mocker):
        self.__prepare(mocker, vcenter=True)

        result = run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert result['changed'] is True
        copy_args = self.manager(mocker).CopyVirtualDisk_Task.call_args.kwargs
        assert 'destSpec' not in copy_args
        assert copy_args['sourceName'] == SOURCE and copy_args['destName'] == DESTINATION

    def test_clone_through_vcenter_refuses_conversion(self, mocker):
        self.__prepare(mocker, vcenter=True)

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='eagerzeroedthick'))
        assert 'needs a connection to an ESXi host' in result['msg']
        self.manager(mocker).CopyVirtualDisk_Task.assert_not_called()

    def test_clone_through_vcenter_refuses_rdm(self, mocker):
        self.__prepare(mocker, vcenter=True)

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm', device=LUN_NAME))
        assert 'sees the LUN' in result['msg']

    def test_clone_on_esxi_keeps_format_and_adapter(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert result['changed'] is True
        spec = self.manager(mocker).CopyVirtualDisk_Task.call_args.kwargs['destSpec']
        assert isinstance(spec, vim.VirtualDiskManager.FileBackedVirtualDiskSpec)
        assert spec.diskType == 'thin'
        assert spec.adapterType == 'ide'

    def test_clone_on_esxi_converts(self, mocker):
        self.__prepare(mocker)

        run_module(module_entry=module_main, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='eagerzeroedthick'))
        assert self.manager(mocker).CopyVirtualDisk_Task.call_args.kwargs['destSpec'].diskType == 'eagerZeroedThick'

    @pytest.mark.parametrize('disk_format, disk_type', [('rdm', 'rdm'), ('rdmp', 'rdmp')])
    def test_clone_onto_rdm(self, mocker, disk_format, disk_type):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format=disk_format, device=LUN_NAME))
        assert result['changed'] is True
        assert result['destination']['provisioning'] == 'rdm'
        spec = self.manager(mocker).CopyVirtualDisk_Task.call_args.kwargs['destSpec']
        assert isinstance(spec, vim.VirtualDiskManager.DeviceBackedVirtualDiskSpec)
        assert spec.diskType == disk_type
        assert spec.device == '/vmfs/devices/disks/' + LUN_NAME

    def test_rdm_requires_device(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm'))
        assert 'device' in result['msg']

    def test_rdm_unknown_device(self, mocker):
        self.__prepare(mocker)

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm', device='naa.missing'))
        assert 'is not a disk visible' in result['msg']

    def test_rdm_lun_too_small(self, mocker):
        self.__prepare(mocker, host=make_host(mocker, luns=[make_lun(blocks=1024)]))

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm', device=LUN_NAME))
        assert 'less than' in result['msg']

    def test_rdm_lun_with_vmfs(self, mocker):
        self.__prepare(mocker, host=make_host(mocker, volumes=[vmfs_volume('ds9', LUN_NAME)]))

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm', device=LUN_NAME))
        assert 'ds9' in result['msg']

    def test_missing_source(self, mocker):
        self.__prepare(mocker)
        self.source_info = None

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert 'does not exist' in result['msg']

    def test_existing_destination_is_kept(self, mocker):
        self.__prepare(mocker, destination_exists=True)

        result = run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert result['changed'] is False
        self.manager(mocker).CopyVirtualDisk_Task.assert_not_called()

    def test_existing_destination_of_another_kind_warns(self, mocker):
        self.__prepare(mocker, destination_exists=True)
        warn = mocker.patch.object(AnsibleModule, 'warn')

        result = run_module(module_entry=module_main, module_args=dict(
            source=SOURCE, destination=DESTINATION, disk_format='rdm', device=LUN_NAME))
        assert result['changed'] is False
        assert 'set force to true' in warn.call_args.args[0]

    def test_force_replaces_destination(self, mocker):
        self.__prepare(mocker, destination_exists=True)

        result = run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION, force=True))
        assert result['changed'] is True
        self.manager(mocker).DeleteVirtualDisk_Task.assert_called_once()
        self.manager(mocker).CopyVirtualDisk_Task.assert_called_once()

    def test_force_refuses_used_destination(self, mocker):
        vm = create_mock_vsphere_object(name='vm9')
        self.__prepare(mocker, destination_exists=True, users=[(vm, mocker.Mock(), False)])

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(
            source=SOURCE, destination=DESTINATION, force=True))
        assert 'vm9' in result['msg']
        self.manager(mocker).DeleteVirtualDisk_Task.assert_not_called()

    def test_missing_folder(self, mocker):
        self.__prepare(mocker, folder_exists=False)

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert 'create_folders' in result['msg']

    def test_create_folders(self, mocker):
        self.__prepare(mocker, folder_exists=False)

        result = run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION, create_folders=True))
        assert result['changed'] is True
        self.make_folder.assert_called_once()

    def test_check_mode(self, mocker):
        self.__prepare(mocker, folder_exists=False)

        result = run_module(module_entry=module_main, module_args=dict(
            source=SOURCE, destination=DESTINATION, create_folders=True, _ansible_check_mode=True))
        assert result['changed'] is True
        assert result['destination']['exists'] is False
        self.make_folder.assert_not_called()
        self.manager(mocker).CopyVirtualDisk_Task.assert_not_called()

    def test_copy_failure(self, mocker):
        self.__prepare(mocker)
        self.wait.side_effect = TaskError('Insufficient disk space on datastore')

        result = run_module(module_entry=module_main, expect_success=False, module_args=dict(source=SOURCE, destination=DESTINATION))
        assert 'Insufficient disk space' in result['msg']

    def test_timeout_is_passed(self, mocker):
        self.__prepare(mocker)

        run_module(module_entry=module_main, module_args=dict(source=SOURCE, destination=DESTINATION, timeout=7200))
        assert self.wait.call_args.kwargs['timeout'] == 7200


class TestVmdkCloneFolders():

    def __module(self, mocker):
        mocker.patch.object(PyvmomiClient, 'connect_to_api', return_value=(mocker.Mock(), mocker.Mock()))
        mocker.patch.object(VmdkFiles, 'resolve')
        module = mocker.Mock(params={'source': SOURCE, 'destination': DESTINATION, 'hostname': 'h', 'username': 'u', 'password': 'p'})
        module.fail_json.side_effect = AnsibleFailJson
        self.path = VmdkPath(create_mock_vsphere_object(name='ds1'), vim.Datacenter('datacenter-1'), DESTINATION)
        return VmdkCloneModule(module)

    def test_folder_exists(self, mocker):
        clone = self.__module(mocker)
        wait = mocker.patch.object(VmdkFiles, 'wait')
        assert clone.folder_exists(self.path)
        assert self.path.datastore.browser.SearchDatastore_Task.call_args.kwargs['datastorePath'] == '[ds1] copy'
        wait.side_effect = TaskError('not found', parent_error=vim.fault.FileNotFound())
        assert not clone.folder_exists(self.path)

    def test_folder_exists_error(self, mocker):
        clone = self.__module(mocker)
        mocker.patch.object(VmdkFiles, 'wait', side_effect=TaskError('denied', parent_error=vim.fault.NoPermission()))
        with pytest.raises(AnsibleFailJson):
            clone.folder_exists(self.path)

    def test_make_folder(self, mocker):
        clone = self.__module(mocker)
        clone.make_folder(self.path)
        clone.content.fileManager.MakeDirectory.assert_called_once_with(
            name='[ds1] copy', datacenter=self.path.datacenter, createParentDirectories=True)

    def test_make_folder_exists(self, mocker):
        clone = self.__module(mocker)
        clone.content.fileManager.MakeDirectory.side_effect = vim.fault.FileAlreadyExists()
        clone.make_folder(self.path)

    def test_make_folder_error(self, mocker):
        clone = self.__module(mocker)
        clone.content.fileManager.MakeDirectory.side_effect = vim.fault.NoPermission(msg='denied')
        with pytest.raises(AnsibleFailJson):
            clone.make_folder(self.path)
