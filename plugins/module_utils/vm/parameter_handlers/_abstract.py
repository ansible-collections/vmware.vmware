from abc import ABC, abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_set import (
    ParameterChangeSet,
)


class ParameterHandlerBase(ABC):
    """
    Base class for handling parameter categories. The implementation of this class may look different depending
    on the parameter category and how vSphere handles the matching configuration. However, the class should
    provide a consistent interface for validating parameters, comparing parameters to live config, and updating
    config specs.
    """

    def __init__(self, module_context, change_set_class=ParameterChangeSet):
        self.module_context = module_context
        self.change_set = change_set_class(module_context)

    @abstractmethod
    def verify_parameter_constraints(self):
        """
        Validate parameters for creation.
        Returns:
            None, the module will fail with an error if the parameters are invalid.
        """
        pass

    @abstractmethod
    def populate_config_spec_with_parameters(self, configspec):
        """
        Update a config spec with parameters for this handler. This should map module params to
        configspec only if they are specified by the user. For example, if the user does not specify
        the VM name, the configspec should omit that parameter or use the existing name.
        Parameters:
            configspec: The vSphere object configspec to update.
        Returns:
            None, the configspec is updated in place.
        """
        raise NotImplementedError

    @abstractmethod
    def compare_live_config_with_desired_config(self):
        """
        Check if current VM config differs from desired config. This should not validate params
        or communicate what values are different. It should only check if there are any differences; it
        does not need to return what parameters are different.
        Parameters:
            vsphere_obj: The vsphere object to compare the config to. This could be the VM, or a device on the VM for example.
                         It is up to the subclass to enforce the type of the object.
        Returns:
            bool: True if the configspec needs to be updated, False otherwise.
        """
        raise NotImplementedError


class DeviceLinkedParameterHandlerBase(ParameterHandlerBase):
    @abstractmethod
    def link_vm_device(self, device):
        """
        Link a vSphere device to the handler. If a device already exists on the VM, this method should validate
        that it matches an object managed by the handler and attach it as an attribute. If the device does not
        match any objects, it should raise an error.
        Parameters:
            device: The vSphere device to link to the handler.
        Returns:
            None, the device is linked to the handler.
        """
        raise NotImplementedError
