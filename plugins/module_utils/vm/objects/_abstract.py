"""
Abstract base class for VMware vSphere object representations.

This module defines the AbstractVsphereObject class, which serves as the foundation
for all VMware vSphere object representations in the VM configuration management
system. It provides a consistent interface for handling VMware objects, change
detection, and specification generation.

The main use case is to represent parameter version of a vSphere object and the
live version of the same object. If both versions implement the same interface,
it is easier to compare and link parameters and what's actually in vSphere.

Classes:
    AbstractVsphereObject: Abstract base class for all vSphere object representations
"""

from abc import ABC, abstractmethod


class AbstractVsphereObject(ABC):
    """
    Abstract base class for VMware vSphere object representations.

    The class supports two main representation modes:
    1. Input parameters: An object that represents the desired state of a vSphere object.
    2. Live object: An object that represents the current state of a vSphere object.

    Key Features:
    - Change detection through linked device comparison
    - VMware specification generation for both new and update operations
    - Module output formatting for Ansible integration

    Attributes:
        _raw_object: Original VMware object from pyVmomi (optional, only makes sense for live objects)
        _live_object: Corresponding live device for change detection (optional, only makes sense for input parameters)
    """

    def __init__(self, raw_object=None):
        """
        Initialize the vSphere object representation.

        Args:
            raw_object: Original VMware object from pyVmomi (optional)
                       Used when creating object from existing VMware device
        """
        self._raw_object = raw_object
        self._live_object = None

    @classmethod
    @abstractmethod
    def from_live_device_spec(cls, live_device_spec):
        """
        Create object instance from VMware device specification.

        This factory method creates an appropriate object instance based on
        the provided VMware device spec from vSphere.

        Args:
            device_spec: VMware device specification object from vSphere (pyvmomi most likely)

        Returns:
            AbstractVsphereObject: Appropriate subclass instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("from_live_device_spec must be implemented by subclasses")

    @abstractmethod
    def to_new_spec(self):
        """
        Generate VMware specification for new object creation.

        Creates a VMware device specification that can be used to create
        a new object in vSphere. The specification should include all
        necessary properties for the object type.

        Returns:
            VMware device specification object

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("to_new_spec must be implemented by subclasses")

    @abstractmethod
    def to_update_spec(self):
        """
        Generate VMware specification for object modification.

        Creates a VMware device specification that can be used to update
        an existing object in vSphere. The specification should include
        only the properties that need to be changed.

        Returns:
            VMware device specification object

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("to_update_spec must be implemented by subclasses")

    @abstractmethod
    def differs_from_live_object(self):
        """
        Determine if this object differs from its linked live device.

        Compares the current object configuration with the linked live device
        to detect changes. This is used for change detection in VM configuration
        management.

        Returns:
            bool: True if the object differs from the linked device, False otherwise

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError(
            "differs_from_live_object must be implemented by subclasses"
        )

    def _compare_attributes_for_changes(self, param_value, device_value):
        """
        Helper method to compare two attribute values to determine if a change is required.

        This method provides comparison logic for different values with Ansible idempotency in mind.
        If a parameter value is not specified (None), it is not considered a change.
        If a device value is not specified (None), it is considered a change.
        If a parameter value is an AbstractVsphereObject, it is compared using the differs_from_live_object method.
        Otherwise, the direct equality comparison is used.

        Args:
            param_value: Value from module parameters (desired state)
            device_value: Value from existing device (current state)

        Returns:
            bool: True if the values represent a change, False otherwise

        """
        if param_value is None:
            return False

        if device_value is None:
            return True

        if isinstance(param_value, AbstractVsphereObject):
            return param_value.differs_from_live_object()
        return param_value != device_value

    @abstractmethod
    def _to_module_output(self):
        """
        Convert object to module output format.

        Generates a dictionary representation of the object suitable for
        Ansible module output. This format is used for reporting object
        state and changes to the user.

        Returns:
            dict: Module output representation of the object

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("_to_module_output must be implemented by subclasses")

    def to_change_set_output(self):
        """
        Generate change set output for configuration tracking.

        Creates a dictionary containing both the new and old values of the
        object, suitable for change tracking and reporting. None values
        are filtered out to keep the output clean.

        Returns:
            dict: Change set output with 'new_value' and 'old_value' keys
                - new_value: Current object state
                - old_value: Previous object state (empty dict if no linked device)

        Example:
            {
                "new_value": {"name": "new_name", "size": 1024},
                "old_value": {"name": "old_name", "size": 512}
            }
        """
        new_value = self._to_module_output()
        old_value = {}
        if self._live_object is not None:
            old_value = self._live_object._to_module_output()

        # Remove None values from both new and old values
        for key, value in new_value.copy().items():
            if value is None:
                del new_value[key]
                if key in old_value:
                    del old_value[key]

        return {
            "new_value": new_value,
            "old_value": old_value,
        }

    def link_corresponding_live_object(self, abstract_vsphere_object: "AbstractVsphereObject"):
        """
        Link this object to its corresponding live device for change detection.

        Establishes a link between the current object (representing desired state)
        and the corresponding live device (representing current state). This link
        is used for change detection and comparison operations.

        Args:
            abstract_vsphere_object: The corresponding live device object to link

        Raises:
            Exception: If a device is already linked (prevents multiple links)

        Note:
            This method should be called when setting up change detection
            between desired and current object states.
        """
        if self._live_object is not None:
            raise Exception("Linked device already set, cannot link another one.")

        self._live_object = abstract_vsphere_object
