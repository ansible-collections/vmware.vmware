from abc import abstractmethod
from ansible_collections.vmware.vmware.plugins.module_utils.vm._abstracts import ParameterHandlerBase
from ansible_collections.vmware.vmware.plugins.module_utils.vm.devices.disks.disk import Disk


class DiskParameterHandlerBase(ParameterHandlerBase):
    def __init__(self, vm, module, controller_handlers):
        super().__init__(vm, module)

        self.disks = []
        self.controller_handlers = controller_handlers

    def validate_params_for_creation(self):
        if len(self.disks) == 0:
            self._parse_disk_params()

        if len(self.disks) == 0:
            raise ValueError(
                "At least one disk is required."
            )

    def validate_params_for_reconfiguration(self):
        if len(self.disks) == 0:
            self._parse_disk_params()

        raise NotImplementedError("Reconfiguration of disks is not implemented yet")

    def params_differ_from_actual_config(self):
        """
        Check if current VM config differs from desired config. This should not validate params
        or communicate what values are different. It should only check if the configspec needs to
        be updated and return.
        Returns:
            bool: True if the configspec needs to be updated, False otherwise.
        """
        raise NotImplementedError

    def _parse_disk_params(self):
        for disk_param in self.module.params.get("disks", []):
            disk = Disk(disk_param)
            self.disks.append(disk)

    def update_config_spec_with_params(self, configspec):
        for disk in self.disks:
            if disk._device is None:
                configspec.deviceChange.append(disk.create_disk_spec())
            else:
                configspec.deviceChange.append(disk.update_disk_spec())
