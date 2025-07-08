from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import ParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import DiskParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import Disk
from ansible_collections.vmware.vmware.plugins.module_utils.vm._utils import parse_device_node, track_device_id_from_spec

try:
    from pyVmomi import vim
except ImportError:
    pass


class DiskParameterHandler(ParameterHandlerBase):
    def __init__(self, vm, module, controller_handlers):
        super().__init__(vm, module)

        self.disks = []
        self.controller_handlers = controller_handlers

    def verify_parameter_constraints(self):
        if len(self.disks) == 0:
            self._parse_disk_params()

        if len(self.disks) == 0:
            raise ValueError(
                "At least one disk is required."
            )

    def _parse_disk_params(self):
        for disk_param in self.module.params.get("disks", []):
            controller_type, controller_bus_number, unit_number = parse_device_node(disk_param['device_node'])
            for controller_handler in self.controller_handlers:
                if controller_type == controller_handler.category:
                    controller = controller_handler.controllers.get(controller_bus_number)
                    break

            if controller is None:
                self.module.fail_json(
                    msg="No controller has been configured for device %s." % disk_param['device_node'],
                    device_node=disk_param['device_node'],
                    available_disks=[c.name_as_str for c in controller_handler.disks.values()]
                )

            disk = Disk(
                size=disk_param.get("size"),
                backing=disk_param.get("backing"),
                mode=disk_param.get("mode"),
                controller=controller,
                unit_number=unit_number
            )
            self.disks.append(disk)

    def populate_config_spec_with_parameters(self, configspec, change_set):
        for disk in change_set.disks_to_add:
            track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.create_disk_spec())
        for disk in change_set.disks_to_update:
            track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.update_disk_spec())

    def get_parameter_change_set(self):
        change_set = DiskParameterChangeSet(self.vm, self.params)
        for disk in self.disks:
            if disk._device is None:
                change_set.disks_to_add.append(disk)
            elif disk.linked_device_differs_from_config():
                change_set.disks_to_update.append(disk)
            else:
                change_set.disks_in_sync.append(disk)

        return change_set

    def link_disk_to_vm_device(self, device):
        for disk in self.disks:
            if device.unitNumber == disk.unit_number and device.controllerKey == disk.controller.key:
                disk._device = device
                return
        else:
            raise Exception("Disk not found for device %s on controller %s" % (device.unitNumber, device.controllerKey))

