from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import (
    DeviceLinkedParameterHandlerBase,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import (
    ParameterChangeSet,
)
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._controllers import (
    ScsiController,
    SataController,
    NvmeController,
    IdeController,
)

try:
    from pyVmomi import vim
except ImportError:
    pass


class ControllerParameterChangeSet(ParameterChangeSet):
    def __init__(self, module_context):
        super().__init__(module_context)
        self.controllers_to_add = []
        self.controllers_to_update = []
        self.controllers_in_sync = []


class DiskControllerParameterHandlerBase(DeviceLinkedParameterHandlerBase):
    """
    Disk controllers are considered to be the controllers that can be used to attach
    disks to the VM. They are configurable on the controllers page of the VM creation
    UI, next to other controllers like USB.
    Each controller has a bus number, which is used to identify the controller in the VM.
    There is a maximum number of controllers of category X that can be added to a VM. For example,
    you can only have 4 SCSI controllers on a VM.
    """

    _device_type_to_class = {}

    def __init__(self, module_context, category, max_count=4):
        if not self._device_type_to_class:
            raise NotImplementedError(
                "Controller parameter handlers must define the _device_type_to_class attribute"
            )

        super().__init__(module_context, change_set_class=ControllerParameterChangeSet)
        self.controllers = {}  # {bus_number: controller}
        self.max_count = max_count
        self.category = category

    def verify_parameter_constraints(self):
        self._parse_device_controller_params()
        if len(self.controllers) > self.max_count:
            self.module_context.fail_with_parameter_error(
                parameter_name="%s_controllers" % self.category,
                message="Only a maximum of %s %s controllers are allowed, but trying to manage %s controllers."
                % (self.max_count, self.category.upper(), len(self.controllers)),
                details={
                    "max_count": self.max_count,
                    "category": self.category,
                    "current_count": len(self.controllers),
                },
            )

    @abstractmethod
    def _parse_device_controller_params(self):
        raise NotImplementedError

    def populate_config_spec_with_parameters(self, configspec, change_set):
        for controller in change_set.controllers_to_add:
            self.module_context.track_device_id_from_spec(controller)
            configspec.deviceChange.append(
                controller.create_controller_spec(edit=False)
            )

        for controller in change_set.controllers_to_update:
            self.module_context.track_device_id_from_spec(controller)
            configspec.deviceChange.append(controller.create_controller_spec(edit=True))

    def compare_live_config_with_desired_config(self):
        for controller in self.controllers.values():
            if controller._device is None:
                self.change_set.controllers_to_add.append(controller)
            elif controller.linked_device_differs_from_config():
                self.change_set.controllers_to_update.append(controller)
            else:
                self.change_set.controllers_in_sync.append(controller)

        if any(
            [
                self.change_set.controllers_to_add,
                self.change_set.controllers_to_update,
                self.change_set.controllers_in_sync,
            ]
        ):
            self.change_set.changes_required = True

        return self.change_set

    def link_vm_device(self, device):
        for controller in self.controllers.values():
            if device.busNumber == controller.bus_number:
                controller._device = device
                return
        else:
            raise Exception(
                f"Controller {self.controllers[0].device_class.__name__} not found for device {device.busNumber}"
            )


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

    _device_type_to_class = {
        "lsilogic": vim.vm.device.VirtualLsiLogicController,
        "paravirtual": vim.vm.device.ParaVirtualSCSIController,
        "buslogic": vim.vm.device.VirtualBusLogicController,
        "lsilogicsas": vim.vm.device.VirtualLsiLogicSASController,
    }

    def __init__(self, module_context):
        super().__init__(module_context, "scsi")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(
            self.module_context.params.get("scsi_controllers", [])
        ):
            self.controllers[index] = ScsiController(
                bus_number=index,
                device_type=controller_param_def.get("controller_type"),
                bus_sharing=controller_param_def.get("bus_sharing"),
            )


class SataControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the SATA controllers on a VM. SATA controllers can be used to
    attach disks and other devices to the VM.
    SATA controllers have no configurable options, so we only need to know
    the total number of controllers to manage.
    """

    _device_type_to_class = {
        "sata": vim.vm.device.VirtualAHCIController,
    }

    def __init__(self, module_context):
        super().__init__(module_context, "sata")

    def _parse_device_controller_params(self):
        for index in range(self.module_context.params.get("sata_controller_count", 0)):
            self.controllers[index] = SataController(bus_number=index)


class NvmeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the NVME controllers on a VM. NVME controllers can be used to
    attach disks to the VM.
    """

    _device_type_to_class = {"nvme": vim.vm.device.VirtualNVMEController}

    def __init__(self, module_context):
        super().__init__(module_context, "nvme")

    def _parse_device_controller_params(self):
        for index, controller_param_def in enumerate(
            self.module_context.params.get("nvme_controllers", [])
        ):
            self.controllers[index] = NvmeController(
                bus_number=index, bus_sharing=controller_param_def.get("bus_sharing")
            )


class IdeControllerParameterHandler(DiskControllerParameterHandlerBase):
    """
    Represents the IDE controllers on a VM. The user cannot configure the IDE controllers,
    but the VM comes with 2 by default. The user can reference those controllers in other
    parameters so we need to create handlers for them.
    """

    _device_type_to_class = {"ide": vim.vm.device.VirtualIDEController}

    def __init__(self, module_context):
        super().__init__(module_context, "ide", max_count=2)

    def _parse_device_controller_params(self):
        for index in range(self.max_count):
            self.controllers[index] = IdeController(bus_number=index)
