from ansible.module_utils.basic import missing_required_lib

try:
    from pyVmomi import vmodl
except ImportError:
    pass


def format_managed_object_not_found_message(vmware_object, object_name=None):
    """
        Handles the situation where an object could no longer be found mid flight. This is a common situation in large
        environments where VMs are moving or being created/destroyed.
        The caller can choose if these issues are critical or not. This method just provides a common message that
        can be presented to the user.
        Args:
            vmware_object: The object that is missing. We will try to get the moid/name from the object in case it was
                            cached somewhere along the way, but that may not be possible.
    """
    try:
        moid = vmware_object._GetMoId()
    except vmodl.fault.ManagedObjectNotFound:
        moid = "unknown"

    try:
        name = object_name or vmware_object.name
    except (vmodl.fault.ManagedObjectNotFound, AttributeError):
        name = "unknown"

    message = (
        "While attempting to read a vSphere object (name: %s, moid: %s), "
        "the object was unable to be found. This can be due to the object being "
        "moved, renamed, or deleted."
    ) % (name, moid)

    return message


class ApiAccessError(Exception):
    def __init__(self, *args, **kwargs):
        super(ApiAccessError, self).__init__(*args, **kwargs)


class MissingLibError(Exception):
    def __init__(self, library, exception, url=None):
        self.exception = exception
        self.library = library
        self.url = url
        super().__init__(missing_required_lib(self.library, url=self.url))
