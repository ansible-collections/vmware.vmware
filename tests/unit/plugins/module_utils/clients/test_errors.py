from __future__ import absolute_import, division, print_function
__metaclass__ = type

from pyVmomi import vmodl

from ansible_collections.vmware.vmware.plugins.module_utils.clients.errors import (
    format_managed_object_not_found_message
)
from ansible_collections.vmware.vmware.tests.unit.common.vmware_object_mocks import (
    create_mock_vsphere_object
)


class TestFormatManagedObjectNotFoundMessage():

    def test_uses_name_and_moid_from_object(self):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')

        message = format_managed_object_not_found_message(vmware_object)

        assert 'test-vm' in message
        assert 'vm-123' in message

    def test_uses_supplied_object_name_over_objects_name(self):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')

        message = format_managed_object_not_found_message(vmware_object, object_name='other-name')

        assert 'other-name' in message
        assert 'test-vm' not in message
        assert 'vm-123' in message

    def test_moid_unknown_when_get_moid_raises(self):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')
        vmware_object._GetMoId.side_effect = vmodl.fault.ManagedObjectNotFound()

        message = format_managed_object_not_found_message(vmware_object)

        assert 'unknown' in message
        assert 'test-vm' in message

    def test_name_unknown_when_name_raises_and_no_object_name_given(self, mocker):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')
        type(vmware_object).name = mocker.PropertyMock(side_effect=vmodl.fault.ManagedObjectNotFound())

        message = format_managed_object_not_found_message(vmware_object)

        assert 'unknown' in message
        assert 'vm-123' in message

    def test_name_unknown_when_name_attribute_missing(self):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')
        del vmware_object.name

        message = format_managed_object_not_found_message(vmware_object)

        assert 'unknown' in message
        assert 'vm-123' in message

    def test_both_unknown_when_moid_and_name_raise(self, mocker):
        vmware_object = create_mock_vsphere_object(name='test-vm', moid='vm-123')
        vmware_object._GetMoId.side_effect = vmodl.fault.ManagedObjectNotFound()
        type(vmware_object).name = mocker.PropertyMock(side_effect=vmodl.fault.ManagedObjectNotFound())

        message = format_managed_object_not_found_message(vmware_object)

        assert 'name: unknown' in message
        assert 'moid: unknown' in message
