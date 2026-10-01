# Migrating from `community.vmware.vmware_vm_inventory`

The `community.vmware.vmware_vm_inventory` inventory plugin is deprecated and is
scheduled for removal. Its supported replacement is
`vmware.vmware.vms`, which collects VMware virtual machines from a vCenter (or
ESXi) environment.

This guide walks through converting an existing
`community.vmware.vmware_vm_inventory` configuration to `vmware.vmware.vms`.

> **Note:** The two plugins are not drop-in compatible. Several options were
> renamed, some changed their default behavior, and a couple inverted their
> meaning. Read the [Behavioral differences](#behavioral-differences) section
> carefully before migrating a production configuration.

## Quick start

1. Install the collection:

   ```bash
   ansible-galaxy collection install vmware.vmware
   ```

2. Rename your inventory configuration file. The new plugin only recognizes
   files ending in one of:

   - `vms.yml` / `vms.yaml`
   - `vmware_vms.yml` / `vmware_vms.yaml`

   The old `vmware.yml`, `vmware.yaml`, `vmware_vm_inventory.yml`, and
   `vmware_vm_inventory.yaml` names are **not** recognized by the new plugin.

3. Change the `plugin` key from `community.vmware.vmware_vm_inventory` to
   `vmware.vmware.vms`.

4. Update option names and values using the [option mapping](#option-mapping)
   below.

## Option mapping

| `community.vmware.vmware_vm_inventory` | `vmware.vmware.vms`        | Notes |
| -------------------------------------- | ------------------------- | ----- |
| `plugin: community.vmware.vmware_vm_inventory` | `plugin: vmware.vmware.vms` | |
| `hostname`                             | `hostname`                | Env `VMWARE_HOST` still works. The `VMWARE_SERVER` alias is no longer read. |
| `username`                             | `username`                | Env `VMWARE_USER` still works. The `VMWARE_USERNAME` alias is no longer read. |
| `password`                             | `password`                | Env `VMWARE_PASSWORD` still works. |
| `port`                                 | `port`                    | Env `VMWARE_PORT`. |
| `validate_certs`                       | `validate_certs`          | Env `VMWARE_VALIDATE_CERTS`. |
| `proxy_host`                           | `proxy_host`              | Env `VMWARE_PROXY_HOST`. |
| `proxy_port`                           | `proxy_port`              | Env `VMWARE_PROXY_PORT`. |
| `with_tags`                            | `gather_tags`             | Renamed. Still requires the vSphere Automation SDK. |
| `hostnames`                            | `hostnames`               | Default value changed — see [Behavioral differences](#behavioral-differences). |
| `properties`                           | `properties`              | Same default list in `vmware.vmware.vms`. |
| `keyed_groups`                         | `keyed_groups`            | Same default. |
| `with_nested_properties`               | `flatten_nested_properties` | **Inverted meaning** — see below. |
| `with_sanitized_property_name`         | `sanitize_property_names` | Renamed. |
| `filters`                              | `filter_expressions`      | **Inverted meaning** — see below. (alias: `filters`) |
| `resources`                            | `search_paths`            | Different format — see below. |
| `with_path`                            | `gather_path` and/or `group_by_paths` | See below. |
| `subproperties`                        | `properties`              | No dedicated option; list the specific property paths in `properties`. |
| `enable_backward_compatibility`        | *(removed)*               | No equivalent. |
| `groups`, `compose`, `strict`, `cache*` | same                     | Provided by the `constructed` and `inventory_cache` fragments, unchanged. |

## Behavioral differences

### `hostnames` default changed

- `community.vmware.vmware_vm_inventory` defaults to
  `['config.name + "_" + config.uuid']`.
- `vmware.vmware.vms` defaults to `['name']`.

If you relied on the old default, your `inventory_hostname` values will change.
To keep the previous names, set the old template explicitly:

```yaml
hostnames:
  - 'config.name + "_" + config.uuid'
```

### `filters` → `filter_expressions` (inverted logic)

This is the most important difference to get right.

- In `community.vmware.vmware_vm_inventory`, `filters` is an **allow list**: a VM
  is included only if **all** expressions evaluate to `true`.
- In `vmware.vmware.vms`, `filter_expressions` is a **deny list**: a VM is
  **excluded** if **any** expression evaluates to `true`.

To migrate, negate each expression. The `filter_expressions` option also accepts
the alias `filters`, but the semantics are still the deny-list semantics.

**Before** (community — include only powered-on RHEL 8 VMs):

```yaml
filters:
  - 'summary.runtime.powerState == "poweredOn"'
  - 'config.guestId == "rhel8_64Guest"'
```

**After** (vmware.vmware — exclude everything that is not a powered-on RHEL 8 VM):

```yaml
filter_expressions:
  - 'summary.runtime.powerState != "poweredOn"'
  - 'config.guestId != "rhel8_64Guest"'
```

### `with_nested_properties` → `flatten_nested_properties` (inverted logic)

- `with_nested_properties: true` (the community default) returns properties as
  nested dictionaries.
- `flatten_nested_properties: false` (the new default) is equivalent — nested
  properties stay nested.

So the **default behavior is the same** and most users need to do nothing. Only
translate if you set the option explicitly:

| Community                        | vmware.vmware                     |
| -------------------------------- | --------------------------------- |
| `with_nested_properties: true`   | `flatten_nested_properties: false` |
| `with_nested_properties: false`  | `flatten_nested_properties: true`  |

### `resources` → `search_paths`

`community.vmware.vmware_vm_inventory` scoped the search with `resources`, a list
of nested `vim_type: [names]` dictionaries. `vmware.vmware.vms` uses
`search_paths`, a simple list of vSphere inventory/folder paths that are searched
recursively.

**Before** (community — limit to two clusters in a datacenter):

```yaml
resources:
  - datacenter:
      - DC1
    resources:
      - compute_resource:
          - Cluster1
          - Cluster2
```

**After** (vmware.vmware — use the inventory paths of those clusters):

```yaml
search_paths:
  - /DC1/host/Cluster1
  - /DC1/host/Cluster2
```

### `with_path`

`community.vmware.vmware_vm_inventory` used the single `with_path` option both to
compute each VM's path and to group by it. `vmware.vmware.vms` splits these
concerns:

- `gather_path` (default `true`) controls whether the `path` hostvar is
  populated.
- `group_by_paths` (default `false`) creates groups based on each VM's path.
- `group_by_paths_prefix` optionally prefixes those group names.

To reproduce `with_path: true` with grouping:

```yaml
gather_path: true
group_by_paths: true
```

## New options worth knowing

`vmware.vmware.vms` adds options that have no `community.vmware` equivalent:

- `gather_compute_objects` — adds `cluster` and `esxi_host` objects (name + moid)
  to each VM, which is handy for keyed groups and filtering.
- `set_ansible_host` — toggles whether `ansible_host` is set automatically.
- `rename_reserved_variables` — prefixes variables that would otherwise collide
  with ansible-core reserved names (such as `name` and `tags`).

See the [plugin documentation](https://github.com/ansible-collections/vmware.vmware/blob/main/plugins/inventory/vms.py)
for the full, current list of options and examples.

## Full before/after example

**Before** — `vmware.yml` using `community.vmware.vmware_vm_inventory`:

```yaml
plugin: community.vmware.vmware_vm_inventory
strict: false
hostname: vcenter.example.com
username: administrator@vsphere.local
password: "{{ lookup('env', 'VMWARE_PASSWORD') }}"
validate_certs: false
with_tags: true
with_path: true
with_nested_properties: true
filters:
  - 'summary.runtime.powerState == "poweredOn"'
keyed_groups:
  - key: config.guestId
    separator: ''
```

**After** — `vmware_vms.yml` using `vmware.vmware.vms`:

```yaml
plugin: vmware.vmware.vms
strict: false
hostname: vcenter.example.com
username: administrator@vsphere.local
password: "{{ lookup('env', 'VMWARE_PASSWORD') }}"
validate_certs: false
gather_tags: true
gather_path: true
group_by_paths: true
# with_nested_properties: true is the default behavior, so no flatten option needed
filter_expressions:
  # negated: exclude VMs that are NOT powered on
  - 'summary.runtime.powerState != "poweredOn"'
keyed_groups:
  - key: config.guestId
    separator: ''
```

## Verifying the migration

Run the new inventory and compare the output against the old one:

```bash
ansible-inventory -i vmware_vms.yml --list
```

Pay particular attention to:

- Host names (if you did not set `hostnames` explicitly).
- Group membership from `keyed_groups` and `group_by_paths`.
- Which VMs are present after translating `filters` to `filter_expressions`.
