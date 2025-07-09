from ansible_collections.vmware.vmware.plugins.module_utils.vm.parameter_handlers._abstract import DeviceLinkedParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm._change_sets import ParameterChangeSet
from ansible_collections.vmware.vmware.plugins.module_utils.vm.objects._disk import Disk


class DiskParameterChangeSet(ParameterChangeSet):
    def __init__(self, module_context):
        super().__init__(module_context)
        self.disks_to_add = []
        self.disks_to_update = []
        self.disks_in_sync = []


class DiskParameterHandler(DeviceLinkedParameterHandlerBase):
    def __init__(self, module_context, controller_handlers):
        super().__init__(module_context, change_set_class=DiskParameterChangeSet)

        self.disks = []
        self.controller_handlers = controller_handlers

    def verify_parameter_constraints(self):
        if len(self.disks) == 0:
            try:
                self._parse_disk_params()
            except ValueError as e:
                self.module_context.fail_with_parameter_error(
                    parameter_name="disks",
                    message="Error parsing disk parameters: %s" % str(e),
                    details={"error": str(e)}
                )

        if len(self.disks) == 0:
            self.module_context.fail_with_parameter_error(
                parameter_name="disks",
                message="At least one disk must be defined when creating or updating a VM."
            )

    def _parse_disk_params(self):
        for disk_param in self.module_context.params.get("disks", []):
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
            self.module_context.track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.create_disk_spec())
        for disk in change_set.disks_to_update:
            self.module_context.track_device_id_from_spec(disk)
            configspec.deviceChange.append(disk.update_disk_spec())

    def compare_live_config_with_desired_config(self):
        for disk in self.disks:
            if disk._device is None:
                self.change_set.disks_to_add.append(disk)
            elif disk.linked_device_differs_from_config():
                self.change_set.disks_to_update.append(disk)
            else:
                self.change_set.disks_in_sync.append(disk)

        if any([
            self.change_set.disks_to_add,
            self.change_set.disks_to_update,
            self.change_set.disks_in_sync
        ]):
            self.change_set.changes_required = True

        return self.change_set

    def link_vm_device(self, device):
        for disk in self.disks:
            if device.unitNumber == disk.unit_number and device.controllerKey == disk.controller.key:
                disk._device = device
                return
        else:
            raise Exception("Disk not found for device %s on controller %s" % (device.unitNumber, device.controllerKey))

