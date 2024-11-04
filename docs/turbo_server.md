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
