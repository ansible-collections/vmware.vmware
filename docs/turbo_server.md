# Using the Turbo Server and Cache

The VMware modules make a lot of API calls that can take a (relatively) long time to finish. To help speed things up, you can enable some caching functionality.

The cache relies on the turbo server provided by `cloud.common`. (ADD LINK HERE)

## Enabling and Configuring

To enable the cache, set the environment variable:
```bash
export ENABLE_TURBO_SERVER=1
```

The cache expires every 15 seconds by default. To change the length of time before the cache expires, set the environment variable:
```bash
export ANSIBLE_TURBO_LOOKUP_TTL=120
```

You can also set these variables in your playbook, if that's more convenient:
```yaml
- name: Example
  hosts: localhost
  environment:
    ENABLE_TURBO_SERVER: 1
    ANSIBLE_TURBO_LOOKUP_TTL: 120
  tasks:
  ...
```

### Clearing The Cache

You may find the need to clear the cache manually. This will make sure that all cached method return values are invalidated. You can do so with the `clear_cache` module:
```yaml
- name: Clear the cache
  vmware.vmware.clear_cache: {}
```

### Killing the turbo server

You may want to kill the turbo server before its expriation time. This will clear the cache and also delete any cached module files. You can do so by terminating the process running on the remote host (the host that the vmware.vmware task was run on):
```bash
ps -ef | grep turbo | grep -v grep | awk '{print $2}' | xargs kill
```

## Development

To use the turbo server in your module, you need to replace the AnsibleModule import with the custom class from this repo.
```python
from ansible_collections.vmware.vmware.plugins.module_utils._vmware_ansible_module import (
    AnsibleModule
)
```

You can leverage the cache from `functools` to save the results from a method. One use case would be caching an authentication session or the results from looking up VM information. To use the cache, import `functools` and then add the cache decorator to the method:
```python
import functools

@functools.cache
def my_method():
    ....
```

When attaching the cache decorator to methods, the argument inputs are hashed and compared to previous calls to determine if a cached result can be used. This means if your method uses a class, the class must have a reasonable hash and equals method defined. For example:
```python
class PyVmomi(object):
    def __init__(self, module):
        """
        Constructor
        """
        self.module = module
        self.params = module.params
        ....

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            return False
        return bool(all([
            (self.params['hostname'] == value.params['hostname']),
            (self.params['username'] == value.params['username'])
        ]))

    def __hash__(self):
        return hash(self.params['hostname'] + self.params['username'])
```

To clear the cache from within a module, you can call the builtin `clear_vmware_cache` method. If the user is not using the turbo server, the module does nothing so you can call this method safely without checking.
```python
def main():
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    ....
    module.clear_vmware_cache()
```
