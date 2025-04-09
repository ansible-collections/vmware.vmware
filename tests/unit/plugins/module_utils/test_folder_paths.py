from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.errors import RequiredIfError
import ansible_collections.vmware.vmware.plugins.module_utils._folder_paths as folder_paths
import pytest


class TestFolderPaths():

    def __prepare(self, mocker):
        pass

    def test_prepend_datacenter_and_folder_type(self, mocker):
        self.__prepare(mocker)

        # test defaults
        with pytest.raises(RequiredIfError):
            folder_paths.prepend_datacenter_and_folder_type()

        # test no datacenter
        assert folder_paths.prepend_datacenter_and_folder_type('foo/vm/bar') == 'foo/vm/bar'

        # test abs paths
        assert folder_paths.prepend_datacenter_and_folder_type('foo/vm/bar', 'foo') == 'foo/vm/bar'

        # test relative paths
        assert folder_paths.prepend_datacenter_and_folder_type('bar', 'foo', 'vm') == 'foo/vm/bar'

        # test bad folder type
        with pytest.raises(ValueError):
            folder_paths.prepend_datacenter_and_folder_type('bar', 'foo', 'bizz')

    def test_format_folder_path_as_vm_fq_path(self, mocker):
        self.__prepare(mocker)
        assert folder_paths.format_folder_path_as_vm_fq_path('foo', 'bar') == 'bar/vm/foo'

    def test_format_folder_path_as_host_fq_path(self, mocker):
        self.__prepare(mocker)
        assert folder_paths.format_folder_path_as_host_fq_path('foo', 'bar') == 'bar/host/foo'

    def test_format_folder_path_as_network_fq_path(self, mocker):
        self.__prepare(mocker)
        assert folder_paths.format_folder_path_as_network_fq_path('foo', 'bar') == 'bar/network/foo'

    def test_format_folder_path_as_datastore_fq_path(self, mocker):
        self.__prepare(mocker)
        assert folder_paths.format_folder_path_as_datastore_fq_path('foo', 'bar') == 'bar/datastore/foo'

    def test_get_folder_path_of_vsphere_object(self, mocker):
        self.__prepare(mocker)
        _root = mocker.Mock()
        _dc = mocker.Mock()
        _parent = mocker.Mock()
        _child = mocker.Mock()

        _root.name = "Datacenters"
        _dc.name = "dc"
        _parent.name = "parent"
        _child.name = "child"

        _root.parent = None
        _root.parentVApp = None
        _root.parentFolder = None
        _dc.parent = _root
        _dc.parentVApp = _root
        _dc.parentFolder = _root
        _parent.parent = _dc
        _parent.parentVApp = _dc
        _parent.parentFolder = _dc
        _child.parent = _parent
        _child.parentVApp = _parent
        _child.parentFolder = _parent

        assert folder_paths.get_folder_path_of_vsphere_object(_dc) == '/'
        assert folder_paths.get_folder_path_of_vsphere_object(_parent) == '/dc'
        assert folder_paths.get_folder_path_of_vsphere_object(_child) == '/dc/parent'
