from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.controllers._controllers import (
    ScsiController,
    SataController,
    NvmeController,
    IdeController
)


class DiskControllerParameterHandlerBase(ParameterHandlerBase):
    """
    Disk controllers are considered to be the controllers that can be used to attach
    disks to the VM. They are configurable on the controllers page of the VM creation
    UI, next to other controllers like USB.
    Each controller has a bus number, which is used to identify the controller in the VM.
    There is a maximum number of controllers of category X that can be added to a VM. For example,
    you can only have 4 SCSI controllers on a VM.
    """
    def __init__(self, vm, module, category, max_count=4):
        super().__init__(vm, module)
        self.controllers = {} # {bus_number: controller}
        self.max_count = max_count
        self.category = category

    def validate_params_for_creation(self):
        self._parse_params_and_validate()

    def validate_params_for_reconfiguration(self):
        self._parse_params_and_validate()

    def _parse_params_and_validate(self):
        if len(self.controllers) == 0:
            self._parse_device_controller_params()
        if len(self.controllers) > self.max_count:
            raise self.module.fail_json(
                "Only a maximum of %s %s controllers are allowed, but trying to manage %s controllers." %
                (self.max_count, self.category.upper(), len(self.controllers)))

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

    def get_params_requiring_power_cycle(self):
        return set()


class ScsiControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the SCSI controllers on a VM. SCSI controllers can be used to
    attach disks and other devices to the VM.
    SCSI controllers have a sub-type that changes how they are accessed by the VM.
    The sub-type can be one of the following:
    - lsilogic: The default type. This is the most common type and is the default for most VMs.
    - buslogic: This type is used for older VMs that do not support the lsilogic type.
    - paravirtual: This type is used for VMs that are running on a paravirtualized hypervisor.
    - virtio: This type is used for VMs that are running on a virtio hypervisor.
    """
    def __init__(self, vm, module):
        super().__init__(vm, module, "scsi")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(self.params.get('scsi_controllers', [])):
            self.controllers[index] = ScsiController(
                bus_number=index,
                device_type=controller_param_def.get('controller_type'),
                bus_sharing=controller_param_def.get('bus_sharing')
            )


class SataControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the SATA controllers on a VM. SATA controllers can be used to
    attach disks and other devices to the VM.
    SATA controllers have no configurable options, so we only need to know
    the total number of controllers to manage.
    """
    def __init__(self, vm, module):
        super().__init__(vm, module, "sata")

    def _parse_device_controller_params(self):
        for index in range(self.params.get('sata_controller_count', 0)):
            self.controllers[index] = SataController(bus_number=index)


class NvmeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the NVME controllers on a VM. NVME controllers can be used to
    attach disks to the VM.
    """
    def __init__(self, vm, module):
        super().__init__(vm, module, "nvme")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(self.params.get('nvme_controllers', [])):
            self.controllers[index] = NvmeController(
                bus_number=index,
                bus_sharing=controller_param_def.get('bus_sharing')
            )


class IdeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the IDE controllers on a VM. The user cannot configure the IDE controllers,
    but the VM comes with 2 by default. The user can reference those controllers in other
    parameters so we need to create handlers for them.
    """
    def __init__(self, vm, module):
        super().__init__(vm, module, "ide", max_count=2)

    def _parse_device_controller_params(self):
        for index in range(self.max_count):
            self.controllers[index] = IdeController(bus_number=index)
