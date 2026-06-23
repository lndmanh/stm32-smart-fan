import unittest

from connection_directory import (
    PortInfo,
    build_port_choices,
    default_friendly_name,
    is_bluetooth_port,
    port_key,
)


class FriendlyNameTests(unittest.TestCase):
    def test_strips_macos_prefix_and_bluetooth_suffix(self):
        info = PortInfo(device="/dev/cu.HC-05-DevB", description="")
        self.assertEqual(default_friendly_name(info), "HC-05")

    def test_keeps_meaningful_description(self):
        info = PortInfo(device="COM3", description="Standard Serial over Bluetooth link (COM3)")
        self.assertEqual(default_friendly_name(info), "Standard Serial over Bluetooth link (COM3)")

    def test_ignores_noise_description_and_uses_device(self):
        info = PortInfo(device="/dev/cu.usbserial-1420", description="n/a")
        self.assertEqual(default_friendly_name(info), "usbserial-1420")


class BluetoothDetectionTests(unittest.TestCase):
    def test_detects_from_device_path(self):
        self.assertTrue(is_bluetooth_port(PortInfo(device="/dev/cu.HC-05-DevB")))

    def test_detects_from_description(self):
        self.assertTrue(is_bluetooth_port(PortInfo(device="COM3", description="Serial over Bluetooth link")))

    def test_plain_usb_serial_is_not_bluetooth(self):
        info = PortInfo(device="/dev/cu.usbserial-1420", description="FT232R USB UART", manufacturer="FTDI")
        self.assertFalse(is_bluetooth_port(info))


class PortKeyTests(unittest.TestCase):
    def test_prefers_serial_number(self):
        self.assertEqual(port_key(PortInfo(device="/dev/ttyUSB0", serial_number="A12345")), "sn:A12345")

    def test_falls_back_to_vid_pid(self):
        self.assertEqual(port_key(PortInfo(device="/dev/ttyUSB0", vid=0x10C4, pid=0xEA60)), "usb:10c4:ea60")

    def test_falls_back_to_device_path(self):
        self.assertEqual(port_key(PortInfo(device="/dev/ttyUSB0")), "dev:/dev/ttyUSB0")


class BuildPortChoicesTests(unittest.TestCase):
    def setUp(self):
        self.serial = PortInfo(device="/dev/cu.usbmodem1", description="USB Modem")
        self.bluetooth = PortInfo(device="/dev/cu.HC-06", description="")
        self.remembered = PortInfo(device="/dev/cu.usbserial-9", description="Zigbee")

    def test_remembered_device_is_flagged_and_sorted_first(self):
        choices = build_port_choices(
            [self.serial, self.bluetooth, self.remembered],
            last_key=port_key(self.remembered),
        )
        self.assertEqual([choice.name for choice in choices], ["Zigbee", "HC-06", "USB Modem"])
        self.assertTrue(choices[0].is_last_used)
        self.assertTrue(choices[0].detail.endswith("Last used"))
        self.assertTrue(choices[1].is_bluetooth)

    def test_custom_name_overrides_default(self):
        choices = build_port_choices(
            [self.bluetooth],
            custom_names={port_key(self.bluetooth): "Desk Fan"},
        )
        self.assertEqual(choices[0].name, "Desk Fan")

    def test_duplicate_names_are_disambiguated(self):
        first = PortInfo(device="/dev/cu.HC-05-DevB")
        second = PortInfo(device="/dev/tty.HC-05-DevB")
        names = [choice.name for choice in build_port_choices([first, second])]
        self.assertEqual(len(set(names)), 2)
        self.assertTrue(all(name.startswith("HC-05 (") for name in names))


if __name__ == "__main__":
    unittest.main()
