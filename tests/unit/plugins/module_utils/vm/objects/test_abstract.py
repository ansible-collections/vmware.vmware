from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest
from unittest.mock import Mock

from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._abstract import (
    AbstractVsphereObject,
)


class ConcreteObject(AbstractVsphereObject):
    """Concrete implementation for testing AbstractVsphereObject."""

    @classmethod
    def from_live_device_spec(cls, live_device_spec):
        """Test implementation of abstract method."""
        return cls(live_device_spec)

    def to_new_spec(self):
        return Mock()

    def to_update_spec(self):
        """Test implementation of abstract method."""
        return self.to_new_spec()

    def differs_from_live_object(self):
        return True

    def _to_module_output(self):
        """Test implementation of abstract method."""
        return {"one": 1, "two": 2}


class TestAbstractVsphereObject:
    """Test cases for AbstractVsphereObject base class."""

    def test_successful_initialization(self):
        """Test successful initialization with valid parameters."""
        raw_object = Mock()

        obj = ConcreteObject(raw_object)

        assert obj._raw_object is raw_object

    def test_compare_attributes_for_changes(self):
        """Test compare_attributes_for_changes method."""
        obj = ConcreteObject()
        assert obj._compare_attributes_for_changes(None, None) is False
        assert obj._compare_attributes_for_changes("value", None) is True
        assert obj._compare_attributes_for_changes("value", "1") is True
        assert obj._compare_attributes_for_changes("value", "value") is False

        other_obj = ConcreteObject()
        other_obj.differs_from_live_object = Mock()
        other_obj.differs_from_live_object.return_value = 1
        assert obj._compare_attributes_for_changes(other_obj, "value") == 1

    def test_to_change_set_output(self):
        """Test to_change_set_output method."""
        obj = ConcreteObject()
        assert obj.to_change_set_output() == {
            "new_value": {"one": 1, "two": 2},
            "old_value": {},
        }

        obj._live_object = ConcreteObject()
        assert obj.to_change_set_output() == {
            "new_value": {"one": 1, "two": 2},
            "old_value": {"one": 1, "two": 2},
        }

        obj._to_module_output = Mock()
        obj._to_module_output.return_value = {"one": None, "two": 2, "three": None}
        assert obj.to_change_set_output() == {
            "new_value": {"two": 2},
            "old_value": {"two": 2},
        }

    def test_link_corresponding_live_object(self):
        """Test link_corresponding_live_object method."""
        obj = ConcreteObject()
        assert obj._live_object is None

        obj.link_corresponding_live_object(ConcreteObject())
        assert obj._live_object is not None

        with pytest.raises(Exception):
            obj.link_corresponding_live_object(ConcreteObject())
