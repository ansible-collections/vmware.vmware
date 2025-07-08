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

    @abstractmethod
    def prepare_parameter_handlers(self):
        raise NotImplementedError

    @abstractmethod
    def stage_configuration_changes(self):
        raise NotImplementedError

    @abstractmethod
    def apply_staged_changes_to_config_spec(self, configspec):
        raise NotImplementedError
