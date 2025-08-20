from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.vmware.vmware.plugins.module_utils.vm._utils import (
    parse_device_node,
    format_size_str_as_kb,
)


class TestParseDeviceNode:
    """Test cases for parse_device_node function."""

    @pytest.mark.parametrize(
        "device_node,expected",
        [
            ("SCSI(0:0)", ("scsi", 0, 0)),
            ("SATA(1:2)", ("sata", 1, 2)),
            ("IDE(0:1)", ("ide", 0, 1)),
            ("NVME(0:0)", ("nvme", 0, 0)),
            ("ScSi(0:0)", ("scsi", 0, 0)),  # Case insensitive
            ("SCSI(255:127)", ("scsi", 255, 127)),  # Large numbers
            ("SCSI( 1 : 2 )", ("scsi", 1, 2)),  # Whitespace
        ],
    )
    def test_valid_device_nodes(self, device_node, expected):
        """Test parsing valid device nodes."""
        result = parse_device_node(device_node)
        assert result == expected

    @pytest.mark.parametrize(
        "invalid_device_node",
        [
            "SCSI0:0",  # Missing parentheses
            "SCSI(0,0)",  # Missing colon
            "SCSI(0:0:extra)",  # Extra characters
            "SCSI(a:b)",  # Non-numeric values
            "",  # Empty string
            None,  # None input
        ],
    )
    def test_invalid_device_nodes(self, invalid_device_node):
        """Test error handling for invalid device nodes."""
        with pytest.raises(ValueError, match="Unable to parse device node"):
            parse_device_node(invalid_device_node)


class TestFormatSizeStrAsKb:
    """Test cases for format_size_str_as_kb function."""

    @pytest.mark.parametrize(
        "size_str,expected",
        [
            ("1024kb", 1024),
            ("1mb", 1024),
            ("1gb", 1048576),
            ("1tb", 1073741824),
            ("1GB", 1048576),  # Case insensitive
            ("100gb", 104857600),  # Large value
            ("0kb", 0),  # Zero value
            ("1.5gb", 1572864),  # Decimal value
            ("999999999kb", 999999999),  # Very large number
            ("0.5mb", 512),  # Fractional MB
            ("1Gb", 1048576),  # Mixed case
        ],
    )
    def test_valid_size_conversions(self, size_str, expected):
        """Test conversion of valid size strings."""
        result = format_size_str_as_kb(size_str)
        assert result == expected

    @pytest.mark.parametrize(
        "invalid_size_str",
        [
            "",  # Empty string
            None,  # None input
        ],
    )
    def test_empty_size_strings(self, invalid_size_str):
        """Test error handling for empty or None size strings."""
        with pytest.raises(ValueError, match="Size string cannot be empty"):
            format_size_str_as_kb(invalid_size_str)

    @pytest.mark.parametrize(
        "invalid_size_str",
        [
            "1024",  # No unit
            "gb",  # No number
            "1 gb",  # Spaces
            "abcgb",  # Invalid number format
            "-1gb",  # Negative number
            " 1gb ",  # Whitespace around value
            "1@gb",  # Special characters
        ],
    )
    def test_invalid_size_format(self, invalid_size_str):
        """Test error handling for invalid size format."""
        with pytest.raises(ValueError, match="Invalid disk size format"):
            format_size_str_as_kb(invalid_size_str)

    def test_unsupported_size_units(self):
        """Test error handling for unsupported size units."""
        with pytest.raises(ValueError, match="Unsupported size unit"):
            format_size_str_as_kb("1pb")
