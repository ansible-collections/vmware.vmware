from abc import ABC, abstractmethod
import functools

from ansible_collections.vmware.vmware.plugins.module_utils.vm.errors import PowerCycleRequiredError


class ParameterChangeSet():
    def __init__(self, vm, params):
        self.vm = vm
        self.params = params
        if vm is None:
            raise ValueError("VM object is None, but it is required to check if a change is required.")

        self.changes_required = False
        self.power_cycle_required = False

    def check_if_change_is_required(self, parameter_name, vm_attribute, power_sensitive=False):
        self._check_if_param_differs_from_vm(parameter_name, vm_attribute)
        if power_sensitive:
            self._check_if_change_violates_power_state(parameter_name)

    def _check_if_param_differs_from_vm(self, parameter_name, vm_attribute):
        if self.params.get(parameter_name) is None or self.changes_required:
            return

        if self.params.get(parameter_name) == functools.reduce(getattr, vm_attribute.split('.'), self.vm):
            return

        self.changes_required = True

    def _check_if_change_violates_power_state(self, parameter_name):
        if self.vm.runtime.powerState != 'poweredOn' or not self.changes_required:
            return

        if self.params.get('power_cycle_allowed'):
            self.power_cycle_required = True
        else:
            raise PowerCycleRequiredError(parameter_name)

    def combine(self, change_set):
        if not isinstance(change_set, ParameterChangeSet):
            raise ValueError("change_set must be an instance of ParameterChangeSet")

        self.changes_required = self.changes_required or change_set.changes_required
        self.power_cycle_required = self.power_cycle_required or change_set.power_cycle_required


class ConfiguratorBase(ABC):
    """
    Base class for configurator classes. This class is responsible for providing a consistent interface for the VM module
    to validate and create/update VMs.
    """
    def __init__(self, vm, module):
        self.vm = vm
        self.module = module
        self.params = module.params
        self.pending_changes = None

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
    def get_parameter_change_set(self):
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
