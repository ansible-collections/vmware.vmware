#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2023, Ansible Eco Content Team (github.com/eco-ansible-content)
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: vm_info
short_description: Gather VM information
description:
    - This module gathers information about one or more VMs.
    - Gathering all properties or only a targeted subset has a similar runtime, so playbooks
      can use any information associated with a VM without a significant performance cost.

requirements:
    - vSphere Automation SDK
options:
    datacenter:
        description:
            - The datacenter with the VM you would like to query.
            - This is only used if the O(folder) parameter is supplied as a relative path.
        aliases: [datacenter_name]
        type: str
        required: false
    guest_username:
        description:
            - The username to be used to connect to guest vm and fetch environment info.
            - Setting this option means that one additional REST API call will be done per VM.
            - This must be supplied with O(guest_password).
        type: str
    guest_password:
        description:
            - The password of the user to be used to connect to guest vm and fetch environment info.
            - Setting this option means that one additional REST API call will be done per VM.
            - This must be supplied with O(guest_username).
        type: str
    name:
        description:
            - The name of the vm to gather info for
            - Only one of name, moid, uuid is allowed
        type: str
        required: False
        aliases: [guest_name]
    uuid:
        description:
            - The UUID of the vm to gather info for
            - Only one of name, moid, uuid is allowed
        type: str
        required: False
    moid:
        description:
            - The MOID of the vm to gather info for
            - Only one of name, moid, uuid is allowed
        type: str
        required: False
    use_instance_uuid:
        description:
            - If true, search by instance UUID instead of BIOS UUID.
            - BIOS UUID may not be unique and may cause errors.
        type: bool
        required: False
        default: True
    name_match:
        description:
            - If using name and multiple VMs have the same name, specify which VM should be selected
        type: str
        required: False
        choices: ['first', 'last']
    folder:
        description:
          - Absolute or relative folder path to search for the virtual machine(s).
          - For example 'datacenter name/vm/path/to/folder' or 'path/to/folder'
          - This parameter can be used on its own to specify a folder to search recursively for VMs.
        type: str
    folder_paths_are_absolute:
        description:
            - If true, any folder path parameters are treated as absolute paths.
            - If false, modules will try to intelligently determine if the path is absolute
              or relative.
            - This option is useful when your environment has a complex folder structure. By default,
              modules will try to intelligently determine if the path is absolute or relative.
              They may mistakenly prepend the datacenter name or other folder names, and this option
              can be used to avoid this.
        type: bool
        required: false
        default: false
    gather_tags:
        description:
            - If true, gather any tags attached to the VM(s).
            - Setting this option means that one additional REST API call will be done per VM.
        type: bool
        default: false
        required: false

    gather_identity:
        description:
            - If true, gather the identity information from the REST API.
            - This populates the C(identity) value in the return output.
            - This adds an additional API call per VM. All of the information obtained
              with these calls can be gathered more efficiently using the O(properties)
              option.
        type: bool
        default: true

    gather_location_objects:
        description:
            - If true, information about the VM's folder and datacenter will be included in the output.
            - This gives more detailed information about these objects than what VM properties alone
              can provide.
        type: bool
        default: false

    gather_compute_objects:
        description:
            - If true, information about the VM's ESXi host, cluster, and resource pool will be included
              in the output.
            - This gives more detailed information about these objects than what VM properties alone
              can provide.
        type: bool
        default: false

    schema:
        description:
            - The type of info to gather from the VMs.
            - The default value of C(summary) is for backwards compatibility. Users should prefer
              the C(vsphere) schema with a list of O(properties).
            - The C(summary) option provides a curated list of VM parameters with custom names.
              It's performance is noticeably worse than the equivalent search using C(vsphere) and
              O(properties).
        choices: [summary, vsphere]
        default: summary
        type: str
    properties:
        description:
            - The list of VM properties to gather. This is only used when O(schema=vsphere).
            - The C(gather_*) options may add properties to this list.
            - If omitted, or if the keyword 'all' is supplied in the list, all properties
              are gathered, which can produce a large amount of output.
            - If set to an empty list, only properties required by the relevnat C(gather_*)
              options are returned. Use this to get a minimal output or if you are unsure
              what about the property names.
            - Adding properties does not significantly increase runtime.
        type: list
        elements: str

attributes:
    check_mode:
        description: The check_mode support.
        support: full
extends_documentation_fragment:
    - vmware.vmware.base_options
    - vmware.vmware.additional_rest_options
'''

EXAMPLES = r'''
- name: Gather guest vm info
  vmware.vmware.vm_info:
    hostname: "https://vcenter"
    username: "username"
    password: "password"
    validate_certs: false
    guest_name: "my_vm"

# The examples below use the vsphere schema with targeted properties. This is the most
# efficient way to gather information. Properties use the vSphere property path syntax
# and the results are nested to match, for example guest.net is returned under vms[*].guest.net.

- name: Gather basic info about every VM in a folder
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - runtime.powerState
      - config.guestFullName
      - config.hardware.numCPU
      - config.hardware.memoryMB
  register: vm_basics

- name: Gather power state and host placement for all VMs in the vCenter
  vmware.vmware.vm_info:
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - runtime.powerState
      - runtime.host
      - resourcePool
  register: vm_placement

- name: Gather disk and storage info for a single VM
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    name: my_vm
    gather_identity: false
    schema: vsphere
    properties:
      - name
      # virtual disks, and other devices, attached to the VM
      - config.hardware.device
      # datastore usage in bytes
      - storage.perDatastoreUsage
      # the datastores the VM files live on
      - datastore
  register: vm_storage

- name: Gather guest OS disk usage for all VMs in a folder
  # This requires VMware tools to be running in the guest
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - guest.disk
  register: vm_guest_disks

- name: Report guest filesystems that are over 90% full
  ansible.builtin.debug:
    msg: "{{ item.0.name }} {{ item.1.diskPath }} is nearly full"
  loop: "{{ vm_guest_disks.vms | subelements('guest.disk', skip_missing=true) }}"
  when: (1 - (item.1.freeSpace / item.1.capacity)) > 0.9

- name: Gather network info for all VMs in a folder
  # This requires VMware tools to be running in the guest
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    gather_identity: false
    schema: vsphere
    properties:
      - name
      # the guest's primary IP address
      - guest.ipAddress
      # per-NIC IP addresses, MAC addresses, and the connected network
      - guest.net
      # the port groups the VM is attached to
      - network
  register: vm_networks

- name: Gather the IP address of a single VM
  vmware.vmware.vm_info:
    name: my_vm
    gather_identity: false
    schema: vsphere
    properties:
      - guest.ipAddress
  register: vm_ip

- name: Gather resource usage for all VMs in a folder
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - summary.quickStats
      - config.hardware.numCPU
      - config.hardware.memoryMB
  register: vm_usage

- name: Gather VMware tools and hardware version info for all VMs in a folder
  vmware.vmware.vm_info:
    folder: "/my-datacenter/vm/production"
    gather_identity: false
    schema: vsphere
    properties:
      - name
      - guest.toolsStatus
      - guest.toolsRunningStatus
      - guest.toolsVersion
      - config.version
'''

RETURN = r'''
vms:
    description:
        - Information about the VMs.
        - The return structure depends on the schema value you used.
        - The first item in the sample list shows the C(summary) schema
        - The second item shows the C(vsphere) schema with all properties. Note that this
          sample is already shortened to remove similar list items. It is a lot of data.
        - O(gather_compute_objects) adds the C(resource_pool), C(esxi_host), and C(cluster)
          keys.
        - O(gather_location_objects) adds the C(datacenter) and C(folder) keys.
    returned: On success
    type: list
    sample: [
        {
            "advanced_settings": {
                "govcsim": "TRUE"
            },
            "annotation": null,
            "current_snapshot": null,
            "customvalues": {},
            "env": {},
            "guest_consolidation_needed": false,
            "guest_question": null,
            "guest_tools_status": "guestToolsNotRunning",
            "guest_tools_version": "0",
            "hw_cluster": null,
            "hw_cores_per_socket": 1,
            "hw_datastores": [
                "LocalDS_0"
            ],
            "hw_esxi_host": "DC0_H0",
            "hw_eth0": {
                "addresstype": "generated",
                "ipaddresses": [],
                "label": "ethernet-0",
                "macaddress": "00:0c:29:36:63:62",
                "macaddress_dash": "00-0c-29-36-63-62",
                "portgroup_key": "dvportgroup-13",
                "portgroup_portkey": null,
                "summary": "DVSwitch: fea97929-4b2d-5972-b146-930c6d0b4014"
            },
            "hw_files": [
                "[LocalDS_0] DC0_H0_VM0/DC0_H0_VM0.vmx",
                "[LocalDS_0] DC0_H0_VM0/DC0_H0_VM0.nvram",
                "[LocalDS_0] DC0_H0_VM0/vmware.log",
                "[LocalDS_0] DC0_H0_VM0/disk1.vmdk"
            ],
            "hw_folder": "DC0/vm",
            "hw_guest_full_name": null,
            "hw_guest_ha_state": null,
            "hw_guest_id": "otherGuest",
            "hw_interfaces": [
                "eth0"
            ],
            "hw_is_template": false,
            "hw_memtotal_mb": 32,
            "hw_name": "DC0_H0_VM0",
            "hw_power_status": "poweredOn",
            "hw_processor_count": 1,
            "hw_product_uuid": "265104de-1472-547c-b873-6dc7883fb6cb",
            "hw_version": "vmx-13",
            "identity": {},
            "instance_uuid": "b4689bed-97f0-5bcd-8a4c-07477cc8f06f",
            "ipv4": null,
            "ipv6": null,
            "module_hw": true,
            "moid": "vm-63",
            "snapshots": [],
            "tags": [],
            "tpm_info": {
                "provider_id": null,
                "tpm_present": null
            },
            "vimref": "vim.VirtualMachine:vm-63",
            "vnc": {}
        },
        {
            "alarmActionsEnabled": true,
            "availableField": [
                {
                    "_vimtype": "vim.CustomFieldsManager.FieldDef",
                    "fieldDefPrivileges": null,
                    "fieldInstancePrivileges": null,
                    "key": 601,
                    "managedObjectType": "vim.VirtualMachine",
                    "name": "MyAttribute",
                    "type": "str"
                }
            ],
            "capability": {
                "_vimtype": "vim.vm.Capability",
                "bootOptionsSupported": true,
                "bootRetryOptionsSupported": true,
                "changeModeDisksSupported": true,
                "changeTrackingSupported": true,
                "consolePreferencesSupported": false,
                "cpuFeatureMaskSupported": true,
                "disableSnapshotsSupported": false,
                "diskOnlySnapshotOnSuspendedVMSupported": true,
                "diskSharesSupported": true,
                "ehvSecureBootSupported": null,
                "featureRequirementSupported": true,
                "guestAutoLockSupported": true,
                "hostBasedReplicationSupported": true,
                "lockSnapshotsSupported": true,
                "memoryReservationLockSupported": true,
                "memorySnapshotsSupported": true,
                "multipleCoresPerSocketSupported": true,
                "multipleSnapshotsSupported": true,
                "nestedHVSupported": true,
                "npivWwnOnNonRdmVmSupported": true,
                "perVmEvcSupported": true,
                "pmemFailoverSupported": false,
                "poweredOffSnapshotsSupported": true,
                "poweredOnMonitorTypeChangeSupported": true,
                "quiescedSnapshotsSupported": true,
                "recordReplaySupported": false,
                "requireSgxAttestationSupported": false,
                "revertToSnapshotSupported": true,
                "s1AcpiManagementSupported": true,
                "seSparseDiskSupported": true,
                "secureBootSupported": true,
                "settingDisplayTopologySupported": true,
                "settingScreenResolutionSupported": true,
                "settingVideoRamSizeSupported": true,
                "sevSnpSupported": null,
                "sevSupported": false,
                "snapshotConfigSupported": true,
                "snapshotOperationsSupported": true,
                "suspendToMemorySupported": true,
                "swapPlacementSupported": true,
                "tdxSupported": null,
                "toolsAutoUpdateSupported": false,
                "toolsSyncTimeAllowSupported": true,
                "toolsSyncTimeSupported": true,
                "vPMCSupported": true,
                "vendorDeviceGroupSupported": false,
                "virtualExecUsageIgnored": true,
                "virtualMmuUsageIgnored": true,
                "virtualMmuUsageSupported": false,
                "vmNpivWwnDisableSupported": true,
                "vmNpivWwnSupported": true,
                "vmNpivWwnUpdateSupported": true
            },
            "config": {
                "_vimtype": "vim.vm.ConfigInfo",
                "alternateGuestName": "",
                "annotation": "Please don't touch used by cloud-user/atomic",
                "bootOptions": {
                    "_vimtype": "vim.vm.BootOptions",
                    "bootDelay": 0,
                    "bootOrder": [],
                    "bootRetryDelay": 10000,
                    "bootRetryEnabled": false,
                    "efiSecureBootEnabled": false,
                    "enterBIOSSetup": false,
                    "networkBootProtocol": "ipv4"
                },
                "changeTrackingEnabled": false,
                "changeVersion": "2026-08-27T05:18:49.888935Z",
                "consolePreferences": null,
                "contentLibItemInfo": null,
                "cpuAffinity": null,
                "cpuAllocation": {
                    "_vimtype": "vim.ResourceAllocationInfo",
                    "expandableReservation": false,
                    "limit": -1,
                    "overheadLimit": null,
                    "reservation": 0,
                    "shares": {
                        "_vimtype": "vim.SharesInfo",
                        "level": "normal",
                        "shares": 2000
                    }
                },
                "cpuFeatureMask": [],
                "cpuHotAddEnabled": false,
                "cpuHotRemoveEnabled": false,
                "createDate": "2025-11-11T12:48:28.079765Z",
                "datastoreUrl": [
                    {
                        "_vimtype": "vim.vm.ConfigInfo.DatastoreUrlPair",
                        "name": "mock-datastore",
                        "url": "/vmfs/volumes/00000000-00000000-0000-000000000000"
                    }
                ],
                "defaultPowerOps": {
                    "_vimtype": "vim.vm.DefaultPowerOpInfo",
                    "defaultPowerOffType": "soft",
                    "defaultResetType": "soft",
                    "defaultSuspendType": "hard",
                    "powerOffType": "soft",
                    "resetType": "soft",
                    "standbyAction": "checkpoint",
                    "suspendType": "hard"
                },
                "deviceGroups": {
                    "_vimtype": "vim.vm.VirtualDeviceGroups",
                    "deviceGroup": []
                },
                "deviceSwap": {
                    "_vimtype": "vim.vm.VirtualDeviceSwap",
                    "lsiToPvscsi": {
                        "_vimtype": "vim.vm.VirtualDeviceSwap.DeviceSwapInfo",
                        "applicable": false,
                        "enabled": true,
                        "status": "none"
                    }
                },
                "extraConfig": [
                    {
                        "_vimtype": "vim.option.OptionValue",
                        "key": "sched.cpu.latencySensitivity",
                        "value": "normal"
                    }
                ],
                "files": {
                    "_vimtype": "vim.vm.FileInfo",
                    "ftMetadataDirectory": null,
                    "logDirectory": "[mock-datastore] mock-vm/",
                    "snapshotDirectory": "[mock-datastore] mock-vm/",
                    "suspendDirectory": "[mock-datastore] mock-vm/",
                    "vmPathName": "[mock-datastore] mock-vm/mock-vm.vmx"
                },
                "firmware": "efi",
                "fixedPassthruHotPlugEnabled": false,
                "flags": {
                    "_vimtype": "vim.vm.FlagInfo",
                    "cbrcCacheEnabled": false,
                    "disableAcceleration": null,
                    "diskUuidEnabled": false,
                    "enableLogging": true,
                    "faultToleranceType": "unset",
                    "htSharing": "any",
                    "monitorType": "release",
                    "recordReplayEnabled": false,
                    "runWithDebugInfo": false,
                    "snapshotDisabled": false,
                    "snapshotLocked": false,
                    "snapshotPowerOffBehavior": "powerOff",
                    "useToe": false,
                    "vbsEnabled": false,
                    "virtualExecUsage": null,
                    "virtualMmuUsage": null,
                    "vvtdEnabled": false
                },
                "forkConfigInfo": null,
                "ftEncryptionMode": "ftEncryptionOpportunistic",
                "ftInfo": null,
                "guestArchitecture": null,
                "guestAutoLockEnabled": true,
                "guestFullName": "Other 2.6.x Linux (64-bit)",
                "guestId": "other26xLinux64Guest",
                "guestIntegrityInfo": {
                    "_vimtype": "vim.vm.GuestIntegrityInfo",
                    "enabled": false
                },
                "guestMonitoringModeInfo": {
                    "_vimtype": "vim.vm.GuestMonitoringModeInfo",
                    "gmmAppliance": null,
                    "gmmFile": null
                },
                "hardware": {
                    "_vimtype": "vim.vm.VirtualHardware",
                    "autoCoresPerSocket": false,
                    "device": [
                        {
                            "_vimtype": "vim.vm.device.VirtualDisk",
                            "backing": {
                                "_vimtype": "vim.vm.device.VirtualDisk.FlatVer2BackingInfo",
                                "backingObjectId": "",
                                "changeId": null,
                                "contentId": "00000000000000000000000000000001",
                                "datastore": "vim.Datastore:datastore-1000",
                                "deltaDiskFormat": null,
                                "deltaDiskFormatVariant": null,
                                "deltaGrainSize": null,
                                "digestEnabled": false,
                                "diskMode": "persistent",
                                "eagerlyScrub": false,
                                "fileName": "[mock-datastore] mock-vm/mock-vm.vmdk",
                                "keyId": null,
                                "parent": null,
                                "sharing": "sharingNone",
                                "split": false,
                                "thinProvisioned": true,
                                "uuid": "6000C290-0000-0000-0000-000000000004",
                                "writeThrough": false
                            },
                            "capacityInBytes": 4507828224,
                            "capacityInKB": 4402176,
                            "connectable": null,
                            "controllerKey": 1000,
                            "deviceGroupInfo": null,
                            "deviceInfo": {
                                "_vimtype": "vim.Description",
                                "label": "Hard disk 1",
                                "summary": "4,402,176 KB"
                            },
                            "diskChainBrokenIssue": null,
                            "diskObjectId": "5993-2000",
                            "guestReadOnly": false,
                            "independentFilters": [],
                            "iofilter": [],
                            "key": 2000,
                            "nativeUnmanagedLinkedClone": false,
                            "numaNode": null,
                            "shares": {
                                "_vimtype": "vim.SharesInfo",
                                "level": "normal",
                                "shares": 1000
                            },
                            "slotInfo": null,
                            "storageIOAllocation": {
                                "_vimtype": "vim.StorageResourceManager.IOAllocationInfo",
                                "limit": -1,
                                "reservation": 0,
                                "shares": {
                                    "_vimtype": "vim.SharesInfo",
                                    "level": "normal",
                                    "shares": 1000
                                }
                            },
                            "unitNumber": 0,
                            "vDiskId": null,
                            "vDiskVersion": 1,
                            "vFlashCacheConfigInfo": null,
                            "virtualDiskFormat": null
                        },
                        {
                            "_vimtype": "vim.vm.device.VirtualVmxnet3",
                            "addressType": "assigned",
                            "backing": {
                                "_vimtype": "vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo",
                                "port": {
                                    "_vimtype": "vim.dvs.PortConnection",
                                    "connectionCookie": 1671356471,
                                    "portKey": "946",
                                    "portgroupKey": "dvportgroup-5000",
                                    "switchUuid": "50 00 00 00 00 00 00 01-00 00 00 00 00 00 00 02"
                                }
                            },
                            "connectable": {
                                "_vimtype": "vim.vm.device.VirtualDevice.ConnectInfo",
                                "allowGuestControl": false,
                                "connected": true,
                                "migrateConnect": "unset",
                                "startConnected": true,
                                "status": "ok"
                            },
                            "controllerKey": 100,
                            "deviceGroupInfo": null,
                            "deviceInfo": {
                                "_vimtype": "vim.Description",
                                "label": "Network adapter 1",
                                "summary": "DVSwitch: 50 00 00 00 00 00 00 01-00 00 00 00 00 00 00 02"
                            },
                            "externalId": null,
                            "key": 4000,
                            "macAddress": "00:50:56:00:00:01",
                            "numaNode": null,
                            "resourceAllocation": {
                                "_vimtype": "vim.vm.device.VirtualEthernetCard.ResourceAllocation",
                                "limit": -1,
                                "reservation": 0,
                                "share": {
                                    "_vimtype": "vim.SharesInfo",
                                    "level": "normal",
                                    "shares": 50
                                }
                            },
                            "slotInfo": {
                                "_vimtype": "vim.vm.device.VirtualDevice.PciBusSlotInfo",
                                "pciSlotNumber": 192
                            },
                            "strictLatencyConfig": null,
                            "subnetId": null,
                            "unitNumber": 7,
                            "uptCompatibilityEnabled": true,
                            "uptv2Enabled": false,
                            "wakeOnLanEnabled": true
                        }
                    ],
                    "memoryMB": 4096,
                    "motherboardLayout": "i440bxHostBridge",
                    "numCPU": 2,
                    "numCoresPerSocket": 1,
                    "simultaneousThreads": 1,
                    "virtualICH7MPresent": false,
                    "virtualSMCPresent": false
                },
                "hotPlugMemoryIncrementSize": 0,
                "hotPlugMemoryLimit": 4096,
                "initialOverhead": {
                    "_vimtype": "vim.vm.ConfigInfo.OverheadInfo",
                    "initialMemoryReservation": 79839232,
                    "initialSwapReservation": 639033344
                },
                "instanceUuid": "50000000-0000-0000-0000-000000000002",
                "keyId": null,
                "latencySensitivity": {
                    "_vimtype": "vim.LatencySensitivity",
                    "level": "normal",
                    "sensitivity": null
                },
                "locationId": "56000000-0000-0000-0000-000000000003",
                "managedBy": null,
                "maxMksConnections": 40,
                "memoryAffinity": null,
                "memoryAllocation": {
                    "_vimtype": "vim.ResourceAllocationInfo",
                    "expandableReservation": false,
                    "limit": -1,
                    "overheadLimit": 84,
                    "reservation": 0,
                    "shares": {
                        "_vimtype": "vim.SharesInfo",
                        "level": "normal",
                        "shares": 40960
                    }
                },
                "memoryHotAddEnabled": false,
                "memoryReservationLockedToMax": false,
                "messageBusTunnelEnabled": false,
                "metroFtEnabled": false,
                "metroFtHostGroup": "",
                "migrateEncryption": "opportunistic",
                "modified": "1970-01-01T00:00:00Z",
                "name": "mock-vm",
                "nestedHVEnabled": false,
                "networkShaper": null,
                "npivDesiredNodeWwns": null,
                "npivDesiredPortWwns": null,
                "npivNodeWorldWideName": [],
                "npivOnNonRdmDisks": null,
                "npivPortWorldWideName": [],
                "npivTemporaryDisabled": true,
                "npivWorldWideNameType": null,
                "numaInfo": {
                    "_vimtype": "vim.vm.VirtualNumaInfo",
                    "autoCoresPerNumaNode": true,
                    "coresPerNumaNode": 2,
                    "vnumaOnCpuHotaddExposed": false
                },
                "pmem": null,
                "pmemFailoverEnabled": false,
                "rebootPowerOff": false,
                "repConfig": null,
                "scheduledHardwareUpgradeInfo": {
                    "_vimtype": "vim.vm.ScheduledHardwareUpgradeInfo",
                    "fault": null,
                    "scheduledHardwareUpgradeStatus": "none",
                    "upgradePolicy": "never",
                    "versionKey": null
                },
                "sevEnabled": false,
                "sevSnpEnabled": null,
                "sgxInfo": {
                    "_vimtype": "vim.vm.SgxInfo",
                    "epcSize": 0,
                    "flcMode": "unlocked",
                    "lePubKeyHash": null,
                    "requireAttestation": false
                },
                "swapPlacement": "inherit",
                "swapStorageObjectId": null,
                "tdxEnabled": null,
                "template": false,
                "tools": {
                    "_vimtype": "vim.vm.ToolsConfigInfo",
                    "afterPowerOn": true,
                    "afterResume": true,
                    "beforeGuestReboot": null,
                    "beforeGuestShutdown": true,
                    "beforeGuestStandby": true,
                    "customizationKeyId": null,
                    "lastInstallInfo": {
                        "_vimtype": "vim.vm.ToolsConfigInfo.ToolsLastInstallInfo",
                        "counter": 0,
                        "fault": null
                    },
                    "pendingCustomization": null,
                    "syncTimeWithHost": false,
                    "syncTimeWithHostAllowed": true,
                    "toolsInstallType": "guestToolsTypeOpenVMTools",
                    "toolsUpgradePolicy": "manual",
                    "toolsVersion": 12389
                },
                "uuid": "42000000-0000-0000-0000-000000000001",
                "vAppConfig": {
                    "_vimtype": "vim.vApp.VmConfigInfo",
                    "eula": [],
                    "installBootRequired": false,
                    "installBootStopDelay": 0,
                    "ipAssignment": {
                        "_vimtype": "vim.vApp.IPAssignmentInfo",
                        "ipAllocationPolicy": "fixedPolicy",
                        "ipProtocol": "IPv4",
                        "supportedAllocationScheme": [],
                        "supportedIpProtocol": [
                            "IPv4"
                        ]
                    },
                    "ovfEnvironmentTransport": [
                        "com.vmware.guestInfo"
                    ],
                    "ovfSection": [],
                    "product": [
                        {
                            "_vimtype": "vim.vApp.ProductInfo",
                            "appUrl": "",
                            "classId": "",
                            "fullVersion": "",
                            "instanceId": "",
                            "key": 0,
                            "name": "",
                            "productUrl": "",
                            "vendor": "",
                            "vendorUrl": "",
                            "version": ""
                        }
                    ],
                    "property": []
                },
                "vAssertsEnabled": false,
                "vFlashCacheReservation": null,
                "vPMCEnabled": false,
                "vcpuConfig": [],
                "version": "vmx-15",
                "vmOpNotificationTimeout": -1,
                "vmOpNotificationToAppEnabled": false,
                "vmStorageObjectId": null,
                "vmxConfigChecksum": "MockBase64Value0000000000000000000000000=",
                "vmxRuntimeConfig": [],
                "vmxStatsCollectionEnabled": true
            },
            "configIssue": [],
            "configStatus": "green",
            "customValue": [],
            "datastore": [
                "'vim.Datastore:datastore-1000'"
            ],
            "declaredAlarmState": [
                {
                    "_vimtype": "vim.alarm.AlarmState",
                    "acknowledged": false,
                    "acknowledgedByUser": null,
                    "acknowledgedTime": null,
                    "alarm": "vim.alarm.Alarm:alarm-6",
                    "disabled": null,
                    "entity": "vim.VirtualMachine:vm-2000",
                    "eventKey": null,
                    "key": "6.2000",
                    "overallStatus": "green",
                    "time": "2026-08-27T05:20:15.153157Z"
                }
            ],
            "disabledMethod": [
                "Destroy_Task",
                "UnregisterVM",
                "UnmountToolsInstaller",
                "AnswerVM",
                "UpgradeVM_Task",
                "UpgradeTools_Task",
                "UpgradeToolsFromImage_Task",
                "ApplyEvcModeVM_Task",
                "StartRecording_Task",
                "StopRecording_Task",
                "StartReplaying_Task",
                "StopReplaying_Task",
                "TurnOffFaultToleranceForVM_Task",
                "MakePrimaryVM_Task",
                "TerminateFaultTolerantVM_Task",
                "DisableSecondaryVM_Task",
                "EnableSecondaryVM_Task",
                "CreateSecondaryVM_Task",
                "CreateSecondaryVMEx_Task",
                "StopRecording_Task",
                "StopReplaying_Task",
                "CustomizeVM_Task",
                "MarkAsTemplate",
                "ResetGuestInformation",
                "ExportVm",
                "PowerOnVM_Task",
                "MarkAsVirtualMachine"
            ],
            "effectiveRole": [
                -1
            ],
            "environmentBrowser": "'vim.EnvironmentBrowser:envbrowser-2000'",
            "guest": {
                "_vimtype": "vim.vm.GuestInfo",
                "appHeartbeatStatus": "appStatusGray",
                "appState": "none",
                "customizationInfo": {
                    "_vimtype": "vim.vm.GuestInfo.CustomizationInfo",
                    "customizationStatus": "TOOLSDEPLOYPKG_IDLE",
                    "endTime": null,
                    "errorMsg": null,
                    "startTime": null
                },
                "disk": [
                    {
                        "_vimtype": "vim.vm.GuestInfo.DiskInfo",
                        "capacity": 3155144704,
                        "diskPath": "/",
                        "filesystemType": "xfs",
                        "freeSpace": 1147379712,
                        "mappings": [
                            {
                                "_vimtype": "vim.vm.GuestInfo.VirtualDiskMapping",
                                "key": 2000
                            }
                        ]
                    }
                ],
                "generationInfo": [],
                "guestDetailedData": "architecture='X86' bitness='64'",
                "guestFamily": "linuxGuest",
                "guestFullName": "Red Hat Enterprise Linux 9 (64-bit)",
                "guestId": "rhel9_64Guest",
                "guestKernelCrashed": false,
                "guestOperationsReady": true,
                "guestRebootStatus": null,
                "guestState": "running",
                "guestStateChangeSupported": true,
                "hostName": "nlb",
                "hwVersion": "vmx-15",
                "interactiveGuestOperationsReady": false,
                "ipAddress": "192.0.2.17",
                "ipStack": [
                    {
                        "_vimtype": "vim.vm.GuestInfo.StackInfo",
                        "dhcpConfig": null,
                        "dnsConfig": {
                            "_vimtype": "vim.net.DnsConfigInfo",
                            "dhcp": false,
                            "domainName": "lab.example.com",
                            "hostName": "nlb",
                            "ipAddress": [
                                "192.0.2.10",
                                "192.0.2.15"
                            ],
                            "searchDomain": [
                                "lab.example.com",
                                "mgmt.lab.example.com",
                                "lab.example.com",
                                "example.com"
                            ]
                        },
                        "ipRouteConfig": {
                            "_vimtype": "vim.net.IpRouteConfigInfo",
                            "ipRoute": [
                                {
                                    "_vimtype": "vim.net.IpRouteConfigInfo.IpRoute",
                                    "gateway": {
                                        "_vimtype": "vim.net.IpRouteConfigInfo.Gateway",
                                        "device": "0",
                                        "ipAddress": "192.0.2.254"
                                    },
                                    "network": "0.0.0.0",
                                    "prefixLength": 0
                                }
                            ]
                        },
                        "ipStackConfig": []
                    }
                ],
                "net": [
                    {
                        "_vimtype": "vim.vm.GuestInfo.NicInfo",
                        "connected": true,
                        "deviceConfigId": 4000,
                        "dnsConfig": null,
                        "ipAddress": [
                            "192.0.2.17",
                            "2001:db8::1"
                        ],
                        "ipConfig": {
                            "_vimtype": "vim.net.IpConfigInfo",
                            "autoConfigurationEnabled": null,
                            "dhcp": null,
                            "ipAddress": [
                                {
                                    "_vimtype": "vim.net.IpConfigInfo.IpAddress",
                                    "ipAddress": "192.0.2.17",
                                    "lifetime": null,
                                    "origin": null,
                                    "prefixLength": 24,
                                    "state": "preferred"
                                },
                                {
                                    "_vimtype": "vim.net.IpConfigInfo.IpAddress",
                                    "ipAddress": "2001:db8::1",
                                    "lifetime": null,
                                    "origin": null,
                                    "prefixLength": 64,
                                    "state": "unknown"
                                }
                            ]
                        },
                        "macAddress": "00:50:56:00:00:01",
                        "netBIOSConfig": null,
                        "network": "vm_traffic"
                    }
                ],
                "screen": {
                    "_vimtype": "vim.vm.GuestInfo.ScreenInfo",
                    "height": 800,
                    "width": 1280
                },
                "toolsInstallType": "guestToolsTypeOpenVMTools",
                "toolsRunningStatus": "guestToolsRunning",
                "toolsStatus": "toolsOk",
                "toolsVersion": "12389",
                "toolsVersionStatus": "guestToolsUnmanaged",
                "toolsVersionStatus2": "guestToolsUnmanaged"
            },
            "guestHeartbeatStatus": "green",
            "layout": {
                "_vimtype": "vim.vm.FileLayout",
                "configFile": [
                    "mock-vm.nvram",
                    "mock-vm.vmsd"
                ],
                "disk": [
                    {
                        "_vimtype": "vim.vm.FileLayout.DiskLayout",
                        "diskFile": [
                            "[mock-datastore] mock-vm/mock-vm.vmdk"
                        ],
                        "key": 2000
                    }
                ],
                "logFile": [
                    "vmware-198.log",
                    "vmware-199.log",
                    "vmware-192.log",
                    "vmware-193.log",
                    "vmware-196.log",
                    "vmware-197.log",
                    "vmware-194.log",
                    "vmware-195.log",
                    "vmware-201.log",
                    "vmware-200.log",
                    "vmware.log"
                ],
                "snapshot": [],
                "swapFile": "[mock-datastore] mock-vm/mock-vm-a1b2c3d4.vswp"
            },
            "layoutEx": {
                "_vimtype": "vim.vm.FileLayoutEx",
                "disk": [
                    {
                        "_vimtype": "vim.vm.FileLayoutEx.DiskLayout",
                        "chain": [
                            {
                                "_vimtype": "vim.vm.FileLayoutEx.DiskUnit",
                                "fileKey": [
                                    3,
                                    4
                                ]
                            }
                        ],
                        "key": 2000,
                        "virtualDiskFormat": null
                    }
                ],
                "file": [
                    {
                        "_vimtype": "vim.vm.FileLayoutEx.FileInfo",
                        "accessible": true,
                        "backingObjectId": null,
                        "key": 0,
                        "name": "[mock-datastore] mock-vm/mock-vm.vmx",
                        "size": 4582,
                        "type": "config",
                        "uniqueSize": 4582
                    }
                ],
                "snapshot": [],
                "timestamp": "2026-10-15T13:09:18.418562Z"
            },
            "name": "mock-vm",
            "network": [
                "'vim.dvs.DistributedVirtualPortgroup:dvportgroup-5000'"
            ],
            "overallStatus": "green",
            "parent": "'vim.Folder:group-v3000'",
            "permission": [],
            "recentTask": [],
            "resourceConfig": {
                "_vimtype": "vim.ResourceConfigSpec",
                "changeVersion": null,
                "cpuAllocation": {
                    "_vimtype": "vim.ResourceAllocationInfo",
                    "expandableReservation": false,
                    "limit": -1,
                    "overheadLimit": null,
                    "reservation": 0,
                    "shares": {
                        "_vimtype": "vim.SharesInfo",
                        "level": "normal",
                        "shares": 2000
                    }
                },
                "entity": "vim.VirtualMachine:vm-2000",
                "lastModified": null,
                "memoryAllocation": {
                    "_vimtype": "vim.ResourceAllocationInfo",
                    "expandableReservation": false,
                    "limit": -1,
                    "overheadLimit": 84,
                    "reservation": 0,
                    "shares": {
                        "_vimtype": "vim.SharesInfo",
                        "level": "normal",
                        "shares": 40960
                    }
                },
                "scaleDescendantsShares": null
            },
            "resourcePool": "'vim.ResourcePool:resgroup-4000'",
            "rootSnapshot": [],
            "runtime": {
                "_vimtype": "vim.vm.RuntimeInfo",
                "bootTime": "2026-01-12T13:55:08Z",
                "cleanPowerOff": null,
                "connectionState": "connected",
                "consolidateWorkDone": null,
                "consolidateWorkTotal": null,
                "consolidationNeeded": false,
                "cryptoState": null,
                "dasVmProtection": null,
                "device": [
                    {
                        "_vimtype": "vim.vm.DeviceRuntimeInfo",
                        "key": 4000,
                        "runtimeState": {
                            "_vimtype": "vim.vm.DeviceRuntimeInfo.VirtualEthernetCardRuntimeState",
                            "attachmentStatus": "green",
                            "featureRequirement": [],
                            "reservationStatus": null,
                            "uptv2Active": null,
                            "uptv2InactiveReasonOther": [],
                            "uptv2InactiveReasonVm": [],
                            "vmDirectPathGen2Active": false,
                            "vmDirectPathGen2InactiveReasonExtended": null,
                            "vmDirectPathGen2InactiveReasonOther": [
                                "vmNptIncompatibleNetwork"
                            ],
                            "vmDirectPathGen2InactiveReasonVm": []
                        }
                    }
                ],
                "diskChainBroken": null,
                "faultToleranceState": "notConfigured",
                "featureMask": [],
                "featureRequirement": [
                    {
                        "_vimtype": "vim.vm.FeatureRequirement",
                        "featureName": "cpuid.3dnprefetch",
                        "key": "cpuid.3dnprefetch",
                        "value": "Bool:Min:1"
                    }
                ],
                "host": "vim.HostSystem:host-6000",
                "instantCloneFrozen": false,
                "iommuActive": null,
                "maxCpuUsage": 4590,
                "maxMemoryUsage": 4096,
                "memoryOverhead": null,
                "minRequiredEVCModeKey": "intel-cascadelake",
                "needSecondaryReason": null,
                "numMksConnections": 0,
                "offlineFeatureRequirement": [
                    {
                        "_vimtype": "vim.vm.FeatureRequirement",
                        "featureName": "cpuid.lm",
                        "key": "cpuid.lm",
                        "value": "Num:Min:1"
                    }
                ],
                "onlineStandby": false,
                "opNotificationTimeout": null,
                "paused": false,
                "powerState": "poweredOn",
                "question": null,
                "quiescedForkParent": null,
                "recordReplayState": "inactive",
                "snapshotInBackground": false,
                "suspendInterval": 0,
                "suspendTime": null,
                "suspendedToMemory": null,
                "toolsInstallerMounted": false,
                "vFlashCacheAllocation": null,
                "vmFailoverInProgress": null
            },
            "storage": {
                "_vimtype": "vim.vm.StorageInfo",
                "perDatastoreUsage": [
                    {
                        "_vimtype": "vim.vm.StorageInfo.UsageOnDatastore",
                        "committed": 7701808015,
                        "datastore": "vim.Datastore:datastore-1000",
                        "uncommitted": 1189085184,
                        "unshared": 3318743593
                    }
                ],
                "timestamp": "2026-10-15T13:09:18.419Z"
            },
            "summary": {
                "_vimtype": "vim.vm.Summary",
                "config": {
                    "_vimtype": "vim.vm.Summary.ConfigSummary",
                    "annotation": "Mock annotation",
                    "cpuReservation": 0,
                    "ftInfo": null,
                    "guestFullName": "Other 2.6.x Linux (64-bit)",
                    "guestId": "other26xLinux64Guest",
                    "hwVersion": "vmx-15",
                    "installBootRequired": false,
                    "instanceUuid": "50000000-0000-0000-0000-000000000002",
                    "managedBy": null,
                    "memoryReservation": 0,
                    "memorySizeMB": 4096,
                    "name": "mock-vm",
                    "numCpu": 2,
                    "numEthernetCards": 1,
                    "numVirtualDisks": 1,
                    "numVmiopBackings": 0,
                    "product": {
                        "_vimtype": "vim.vApp.ProductInfo",
                        "appUrl": "",
                        "classId": "",
                        "fullVersion": "",
                        "instanceId": "",
                        "key": 0,
                        "name": "",
                        "productUrl": "",
                        "vendor": "",
                        "vendorUrl": "",
                        "version": ""
                    },
                    "template": false,
                    "tpmPresent": false,
                    "uuid": "42000000-0000-0000-0000-000000000001",
                    "vmPathName": "[mock-datastore] mock-vm/mock-vm.vmx"
                },
                "customValue": [],
                "guest": {
                    "_vimtype": "vim.vm.Summary.GuestSummary",
                    "guestFullName": "Red Hat Enterprise Linux 9 (64-bit)",
                    "guestId": "rhel9_64Guest",
                    "hostName": "nlb",
                    "hwVersion": "vmx-15",
                    "ipAddress": "192.0.2.17",
                    "toolsRunningStatus": "guestToolsRunning",
                    "toolsStatus": "toolsOk",
                    "toolsVersionStatus": "guestToolsUnmanaged",
                    "toolsVersionStatus2": "guestToolsUnmanaged"
                },
                "overallStatus": "green",
                "quickStats": {
                    "_vimtype": "vim.vm.Summary.QuickStats",
                    "activeMemory": 40,
                    "balloonedMemory": 0,
                    "compressedMemory": 0,
                    "consumedOverheadMemory": 42,
                    "distributedCpuEntitlement": 0,
                    "distributedMemoryEntitlement": 1280,
                    "ftLatencyStatus": "gray",
                    "ftLogBandwidth": -1,
                    "ftSecondaryLatency": -1,
                    "grantedMemory": 2224,
                    "guestHeartbeatStatus": "green",
                    "guestMemoryUsage": 40,
                    "hostMemoryUsage": 2266,
                    "memoryTierStats": [],
                    "overallCpuDemand": 0,
                    "overallCpuReadiness": 0,
                    "overallCpuUsage": 0,
                    "privateMemory": 2224,
                    "sharedMemory": 0,
                    "ssdSwappedMemory": 0,
                    "staticCpuEntitlement": 101,
                    "staticMemoryEntitlement": 4790,
                    "swappedMemory": 0,
                    "uptimeSeconds": 4261985
                },
                "runtime": {
                    "_vimtype": "vim.vm.RuntimeInfo",
                    "bootTime": "2026-01-12T13:55:08Z",
                    "cleanPowerOff": null,
                    "connectionState": "connected",
                    "consolidateWorkDone": null,
                    "consolidateWorkTotal": null,
                    "consolidationNeeded": false,
                    "cryptoState": null,
                    "dasVmProtection": null,
                    "device": [
                        {
                            "_vimtype": "vim.vm.DeviceRuntimeInfo",
                            "key": 4000,
                            "runtimeState": {
                                "_vimtype": "vim.vm.DeviceRuntimeInfo.VirtualEthernetCardRuntimeState",
                                "attachmentStatus": "green",
                                "featureRequirement": [],
                                "reservationStatus": null,
                                "uptv2Active": null,
                                "uptv2InactiveReasonOther": [],
                                "uptv2InactiveReasonVm": [],
                                "vmDirectPathGen2Active": false,
                                "vmDirectPathGen2InactiveReasonExtended": null,
                                "vmDirectPathGen2InactiveReasonOther": [
                                    "vmNptIncompatibleNetwork"
                                ],
                                "vmDirectPathGen2InactiveReasonVm": []
                            }
                        }
                    ],
                    "diskChainBroken": null,
                    "faultToleranceState": "notConfigured",
                    "featureMask": [],
                    "featureRequirement": [
                        {
                            "_vimtype": "vim.vm.FeatureRequirement",
                            "featureName": "cpuid.3dnprefetch",
                            "key": "cpuid.3dnprefetch",
                            "value": "Bool:Min:1"
                        }
                    ],
                    "host": "vim.HostSystem:host-6000",
                    "instantCloneFrozen": false,
                    "iommuActive": null,
                    "maxCpuUsage": 4590,
                    "maxMemoryUsage": 4096,
                    "memoryOverhead": null,
                    "minRequiredEVCModeKey": "intel-cascadelake",
                    "needSecondaryReason": null,
                    "numMksConnections": 0,
                    "offlineFeatureRequirement": [
                        {
                            "_vimtype": "vim.vm.FeatureRequirement",
                            "featureName": "cpuid.lm",
                            "key": "cpuid.lm",
                            "value": "Num:Min:1"
                        }
                    ],
                    "onlineStandby": false,
                    "opNotificationTimeout": null,
                    "paused": false,
                    "powerState": "poweredOn",
                    "question": null,
                    "quiescedForkParent": null,
                    "recordReplayState": "inactive",
                    "snapshotInBackground": false,
                    "suspendInterval": 0,
                    "suspendTime": null,
                    "suspendedToMemory": null,
                    "toolsInstallerMounted": false,
                    "vFlashCacheAllocation": null,
                    "vmFailoverInProgress": null
                },
                "storage": {
                    "_vimtype": "vim.vm.Summary.StorageSummary",
                    "committed": 7701808015,
                    "timestamp": "2026-10-15T13:09:18.419205Z",
                    "uncommitted": 1189085184,
                    "unshared": 3318743593
                },
                "vm": "vim.VirtualMachine:vm-2000"
            },
            "tag": [],
            "triggeredAlarmState": [],
            "value": [],
            "identity": {},
            "tags": [],
            "env": {}
        }
    ]

guests:
    description:
        - Information about the VMs. This is identical to the vms return value.
    returned: On success
    type: list
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware.plugins.module_utils._module_pyvmomi_base import ModulePyvmomiBase
from ansible_collections.vmware.vmware.plugins.module_utils._module_rest_base import ModuleRestBase
from ansible_collections.vmware.vmware.plugins.module_utils.argument_spec import rest_compatible_argument_spec
from ansible_collections.vmware.vmware.plugins.module_utils.clients.errors import (
    format_managed_object_not_found_message,
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._vm import (
    VmFacts,
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._converters import (
    properties_from_collector,
    extract_object_attributes_to_dict
)
from ansible_collections.vmware.vmware.plugins.module_utils.facts._gatherers import (
    LocationObjectsGatherer,
    ComputeObjectsGatherer
)


try:
    from pyVmomi import vmodl, vim
except ImportError:
    pass


SUMMARY_SCHEMA_PROPERTIES = ['config', 'summary', 'guest', 'layout', 'snapshot', 'datastore', 'parent', 'parentVApp']


class _PrefetchedVm():
    """
    Stand-in for a vim.VirtualMachine whose top-level properties were already fetched by the property collector,
    so attribute access does not trigger a SOAP call
    """
    def __init__(self, object_content):
        self._moId = object_content.obj._moId
        for prop_name in SUMMARY_SCHEMA_PROPERTIES:
            setattr(self, prop_name, None)  # unset properties are omitted from propSet
        for prop in object_content.propSet:
            setattr(self, prop.name, prop.val)


class VmwareVmInfo(ModuleRestBase):
    def __init__(self, module):
        super(VmwareVmInfo, self).__init__(module)
        self.pyvmomi = ModulePyvmomiBase(module)
        self.vm_svc = self.api_client.vcenter.vm
        self._enabled_gatherers = []
        self._search_properties = None

    @property
    def enabled_gatherers(self):
        if not self._enabled_gatherers:
            gathers = {
                'gather_compute_objects': ComputeObjectsGatherer,
                'gather_location_objects': LocationObjectsGatherer,
            }
            self._enabled_gatherers = [g for option, g in gathers.items() if self.params.get(option)]

        return self._enabled_gatherers

    @property
    def search_properties(self):
        if self._search_properties is None:
            if self.schema_is_vsphere():
                properties = self.params.get('properties')
                if properties is None:
                    properties = ['all']
                properties = set(properties)
            else:
                properties = set(SUMMARY_SCHEMA_PROPERTIES)

            for gatherer in self.enabled_gatherers:
                properties.update(gatherer.vm_properties)

            self._search_properties = list(properties)

        return self._search_properties

    def _get_env(self, vm):
        """
        Gets the guest env facts from a vm and returns them as a dict.
        This requires the VM is running, has vmware tools installed, and the user
        provided a username and password to the VM via params
        """
        if not self.params.get('guest_username'):
            return {}

        try:
            return self.vm_svc.guest.Environment.list(
                vm=vm,
                credentials={
                    'type': 'USERNAME_PASSWORD',
                    'user_name': self.params.get('guest_username'),
                    'password': self.params.get('guest_password'),
                    'interactive_session': False
                },
                names=set()
            )
        except Exception:
            return {}

    def _get_identity(self, vm):
        """
        Gets the guest identity facts (guest os name, guest family, etc) about a VM
        """
        if not self.params['gather_identity']:
            return {}

        guest_svc = self.vm_svc.guest
        try:
            identity = guest_svc.Identity.get(vm=str(vm._GetMoId()))

        except Exception:
            return {}

        return extract_object_attributes_to_dict(identity)

    def schema_is_vsphere(self):
        return (self.params['schema'] == 'vsphere')

    def gather_info_for_vms(self):
        all_vm_info = []
        managed_object_refs = self._collect_vm_managed_object_properties()
        vm_refs, related_objects = self._split_collected_objects(managed_object_refs)

        for vm_ref in vm_refs:
            vm_info = self._hydrate_vm_info_with_collected_props(vm_ref, related_objects)
            self._hydrate_vm_info_with_rest_calls(vm_info, vm_ref.obj)  # real MOR for REST/tags
            all_vm_info += [vm_info]

        return all_vm_info

    def _hydrate_vm_info_with_collected_props(self, managed_object_ref, related_objects=None):
        if related_objects is None:
            related_objects = {}

        if self.schema_is_vsphere():
            vm_info = properties_from_collector(managed_object_ref.propSet)
        else:
            vm_info = VmFacts(_PrefetchedVm(managed_object_ref)).all_facts(self.pyvmomi.content)

        # since vm_info format varies, we need to have a (flat) dict of all props
        vm_props = {p.name: p.val for p in managed_object_ref.propSet}
        for gatherer in self.enabled_gatherers:
            gatherer.add_facts(vm_info, vm_props, related_objects)

        return vm_info

    def _hydrate_vm_info_with_rest_calls(self, vm_info, vm):
        vm_info['identity'] = self._get_identity(vm)
        # legacy output
        vm_info.update(vm_info['identity'])

        vm_info['tags'] = self._get_tags(vm)
        vm_info['env'] = self._get_env(vm)

    def _create_select_set(self):
        select_set = []
        for gather in self.enabled_gatherers:
            select_set += gather.traversal_specs()

        return select_set or None

    def _create_prop_set(self):
        prop_set = [
            vim.PropertyCollector.PropertySpec(
                type=vim.VirtualMachine,
                pathSet=[p for p in self.search_properties if p != 'all'],
                all=('all' in self.search_properties),
            )
        ]
        for gatherer in self.enabled_gatherers:
            prop_set += gatherer.property_specs()

        return prop_set

    def _collect_vm_managed_object_properties(self):
        vms = self.get_vms()
        if not vms:
            return []

        select_set = self._create_select_set()
        prop_set = self._create_prop_set()
        object_set = [vim.PropertyCollector.ObjectSpec(obj=vm, skip=False, selectSet=select_set) for vm in vms]
        filter_spec = vim.PropertyCollector.FilterSpec(
            propSet=prop_set,
            objectSet=object_set,
            reportMissingObjectsInResults=True  # if false, the whole batch is bad instead of just one vm
        )

        try:
            return self.pyvmomi._query_paged_managed_object_properties(filter_spec)
        except vmodl.query.InvalidProperty as e:
            self.module.fail_json(msg="Invalid property path '%s' requested for VMs." % e.name)

    def _fail_on_missing_vm_properties(self, managed_object_ref):
        if self.schema_is_vsphere() and 'all' not in self.search_properties:
            for missing in managed_object_ref.missingSet:
                # VM exists, but a specific property couldn't be read (permissions, etc.)
                # Probably a typo, or an unexpected issue
                self.module.fail_json(msg="Unable to read property '%s' on VM %s: %s" % (
                    missing.path, managed_object_ref.obj._GetMoId(), missing.fault.msg)
                )

    def _split_collected_objects(self, managed_object_refs):
        vm_refs, related_objects = [], {}
        for managed_object_ref in managed_object_refs:
            if any(isinstance(m.fault, vmodl.fault.ManagedObjectNotFound) for m in managed_object_ref.missingSet):
                # object was deleted mid-gather; pass a name so the helper doesn't make a SOAP call on a dead object
                self.module.warn(format_managed_object_not_found_message(managed_object_ref.obj, object_name='unknown'))
                continue

            if isinstance(managed_object_ref.obj, vim.VirtualMachine):
                self._fail_on_missing_vm_properties(managed_object_ref)
                vm_refs.append(managed_object_ref)
            else:
                related_objects[managed_object_ref.obj._moId] = {
                    p.name: p.val for p in managed_object_ref.propSet
                }

        return vm_refs, related_objects

    def get_vms(self):
        """
        Uses the UUID, MOID, or name provided to find the source VM for the template. Returns an error if using the name,
        multiple matches are found, and the user did not provide a name_match strategy.
        """
        if self.params.get('name') or self.params.get('uuid') or self.params.get('moid'):
            vm = self.pyvmomi.get_vms_using_params(fail_on_missing=False)
        else:
            folder = None
            if self.params.get('folder'):
                folder = self.pyvmomi.get_folder_using_params(fail_on_missing=True)
            vm = self.pyvmomi.get_all_vms(folder=folder)

        return vm if vm else []

    def _get_tags(self, vm):
        """
        Gets the tags on a VM. Tags are formatted as a list of dictionaries corresponding to each tag
        """
        output = []
        if not self.params.get('gather_tags'):
            return output

        tags = self.get_tags_by_vm_moid(vm._moId)
        for tag in tags:
            output.append(self.format_tag_identity_as_dict(tag))

        return output


def main():
    argument_spec = rest_compatible_argument_spec()
    argument_spec.update(
        dict(
            name=dict(type='str', aliases=['guest_name']),
            name_match=dict(type='str', choices=['first', 'last'], default=None),
            uuid=dict(type='str'),
            use_instance_uuid=dict(type='bool', default=True),
            moid=dict(type='str'),
            datacenter=dict(type='str', required=False, aliases=['datacenter_name']),
            folder=dict(type='str', required=False),
            folder_paths_are_absolute=dict(type='bool', required=False, default=False),

            gather_tags=dict(type='bool', default=False),
            gather_identity=dict(type='bool', default=True),
            gather_location_objects=dict(type='bool', default=False),
            gather_compute_objects=dict(type='bool', default=False),

            schema=dict(type='str', choices=['summary', 'vsphere'], default='summary'),
            properties=dict(type='list', elements='str'),

            guest_username=dict(type='str', required=False),
            guest_password=dict(type='str', no_log=True, required=False),
        )
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_together=[
            ('guest_username', 'guest_password'),
        ],
        mutually_exclusive=[['name', 'uuid', 'moid']]
    )

    if module.params['schema'] != 'vsphere' and module.params.get('properties'):
        module.fail_json(msg="The option 'properties' is only valid when the schema is 'vsphere'")

    vmware_appliance_mgr = VmwareVmInfo(module)
    vms = vmware_appliance_mgr.gather_info_for_vms()
    # guests is a legacy return key from the module rename, kept in place for backwards compatibility
    module.exit_json(changed=False, guests=vms, vms=vms)


if __name__ == '__main__':
    main()
