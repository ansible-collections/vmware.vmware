from abc import ABC, abstractmethod


class ConfiguratorBase(ABC):
    """
    Base class for configurator classes. This class is responsible for providing a consistent interface for the VM module
    to validate and create/update VMs.
    """
    def __init__(self, vm, module):
        self.vm = vm
        self.module = module
        self.params = module.params
        self.required_changes = None

    @abstractmethod
    def validate_params_for_creation(self):
        raise NotImplementedError

    @abstractmethod
    def configure_spec_for_creation(self, configspec, datastore):
        raise NotImplementedError

    @abstractmethod
    def configure_spec_for_reconfiguration(self, configspec):
        raise NotImplementedError

    @abstractmethod
    def check_if_power_cycle_is_required(self):
        """
        Check if the VM needs to be powered off to apply the changes.
        """
        raise NotImplementedError

    @abstractmethod
    def check_for_required_changes(self):
        return False


class ParameterHandlerBase(ABC):
    """
    Base class for handling parameter categories. The implementation of this class may look different depending
    on the parameter category and how vSphere handles the matching configuration. However, the class should
    provide a consistent interface for validating parameters, comparing parameters to live config, and updating
    config specs.
    """

    def __init__(self, vm, module):
        self.module = module
        self.params = module.params
        self.vm = vm

    @abstractmethod
    def validate_params_for_creation(self):
        """
        Validate parameters for creation.
        Returns:
            None, the module will fail with an error if the parameters are invalid.
        """
        pass

    @abstractmethod
    def validate_params_for_reconfiguration(self):
        """
        Validate parameters for reconfiguration. Reconfiguration may require that the VM is powered off,
        and this method should validate that the VM is in the correct state or the user has allowed power
        cycling.
        Returns:
            None, the module will fail with an error if the parameters are invalid.
        """
        pass

    @abstractmethod
    def update_config_spec_with_params(self, configspec):
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
    def params_differ_from_actual_config(self, vsphere_obj):
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
