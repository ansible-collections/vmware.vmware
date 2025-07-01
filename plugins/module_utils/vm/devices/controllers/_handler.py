from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.controllers._controllers import (
    ScsiController,
    SataController,
    NvmeController,
    IdeController
)


class DiskControllerParameterHandlerBase(ParameterHandlerBase):
    def __init__(self, vm, module, category, max_count=4):
        super().__init__(vm, module)
        self.controllers = {} # {bus_number: controller}
        self.max_count = max_count
        self.category = category

    def validate_params_for_creation(self):
        if len(self.controllers) == 0:
            self._parse_device_controller_params()

        if len(self.controllers) > self.max_count:
            raise ValueError(
                "Only a maximum of %s %s controllers are allowed, but trying to add %s controllers." %
                (self.max_count, self.category.upper(), len(self.controllers)))

    def validate_params_for_reconfiguration(self):
        if len(self.controllers) == 0:
            self._parse_device_controller_params()

        raise NotImplementedError("Reconfiguration of controllers is not implemented yet")

    def params_differ_from_actual_config(self):
        """
        Check if current VM config differs from desired config. This should not validate params
        or communicate what values are different. It should only check if the configspec needs to
        be updated and return.
        Returns:
            bool: True if the configspec needs to be updated, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def _parse_device_controller_params(self):
        raise NotImplementedError

    def update_config_spec_with_params(self, configspec):
        for controller in self.controllers.values():
            if controller._device is None:
                configspec.deviceChange.append(controller.create_controller_spec())
            else:
                configspec.deviceChange.append(controller.update_controller_spec())

    def get_controller_by_key(self, key):
        """
        Get a controller by the key attribute. Disks attached to VMs will have a key attribute that corresponds to their controller.
        """
        for controller in self.controllers.values():
            if controller.key == key:
                return controller
        raise ValueError("Controller with key %s not found. Available controllers: %s" % (key, list(self.controllers.keys())))




class ScsiControllerParameterHandler(DiskControllerParameterHandlerBase):
    def __init__(self, vm, module):
        super().__init__(vm, module, "scsi")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(self.params.get('scsi_controller_count', 0)):
            self.controllers[index] = ScsiController(
                bus_number=index,
                device_type=controller_param_def.get('controller_type'),
                bus_sharing=controller_param_def.get('bus_sharing')
            )

class SataControllerParameterHandler(DiskControllerParameterHandlerBase):
    def __init__(self, vm, module):
        super().__init__(vm, module, "sata")

    def _parse_device_controller_params(self):
        for index in range(self.params.get('sata_controller_count', 0)):
            self.controllers[index] = SataController(bus_number=index)

class NvmeControllerParameterHandler(DiskControllerParameterHandlerBase):
    def __init__(self, vm, module):
        super().__init__(vm, module, "nvme")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(self.params.get('nvme_controller_count', 0)):
            self.controllers[index] = NvmeController(
                bus_number=index,
                bus_sharing=controller_param_def.get('bus_sharing')
            )

class IdeControllerParameterHandler(DiskControllerParameterHandlerBase):
    def __init__(self, vm, module):
        super().__init__(vm, module, "ide", max_count=2)

    def _parse_device_controller_params(self):
        for index in range(self.max_count):
            self.controllers[index] = IdeController(bus_number=index)
