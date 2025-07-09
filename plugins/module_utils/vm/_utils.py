import re


def parse_device_node(device_node):
    """
    Parse a device node and return the controller type, bus number, and unit number.
    Example:
        SCSI(0:0) -> ('scsi', 0, 0)
        SATA(0:0) -> ('sata', 0, 0)
        IDE(0:0) -> ('ide', 0, 0)
        NVME(0:0) -> ('nvme', 0, 0)
    Parameters:
        device_node (str): The device node to parse.
    Returns:
        tuple: A tuple containing the controller type, bus number, and unit number.
    Raises:
        ValueError: If the device node is not in the expected format.
    """
    try:
        controller_category = device_node.split("(")[0].lower()
        _device_numbers = device_node.split("(")[1].strip(")")
        controller_bus_number, controller_unit_number = _device_numbers.split(":")
        return controller_category, int(controller_bus_number), int(controller_unit_number)
    except (ValueError, IndexError, AttributeError):
        raise ValueError(
            "Unable to parse device node: %s. "
            "Expected format is <controller_type>(<bus_number>:<unit_number>)" %
            device_node
        )


def format_size_str_as_kb(size_str):
    """
    Convert size string like '100gb' to kilobytes
    Example:
        '100gb' -> 104857600
        '1tb' -> 1073741824
        '1mb' -> 1024
        '1kb' -> 1
    Parameters:
        size_str (str): The size string to convert.
    Returns:
        int: The size in kilobytes.
    Raises:
        ValueError: If the size string is empty or invalid.
    """
    unit_converters = {'tb': 3, 'gb': 2, 'mb': 1, 'kb': 0}
    if not size_str:
        raise ValueError("Size string cannot be empty")

    match = re.search(r'^(\d+)([a-zA-Z]+)$', size_str)
    if not match:
        raise ValueError("Invalid disk size format: '%s'. Format should be like '100gb'." % size_str)

    disk_size_str, disk_units = match.groups()
    disk_units = disk_units.lower()

    if disk_units not in unit_converters:
        raise ValueError("Unsupported size unit: '%s'. Supported units: %s" % (disk_units, list(unit_converters.keys())))

    try:
        disk_size = float(disk_size_str)
    except ValueError:
        raise ValueError("Invalid disk size number: '%s'" % disk_size_str)

    return int(disk_size * (1024 ** unit_converters[disk_units]))
