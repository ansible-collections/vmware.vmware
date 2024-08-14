# Ansible Collection: vmware.vmware

This repo hosts the `vmware.vmware` Ansible Collection.

The collection includes the VMware modules and plugins to help the management of VMware infrastructure.

## Communication

* Join the Ansible forum:
  * [Get Help](https://forum.ansible.com/c/help/6): get help or help others.
  * [Posts tagged with 'vmware'](https://forum.ansible.com/tag/vmware): subscribe to participate in collection-related conversations.
  * [Social Spaces](https://forum.ansible.com/c/chat/4): gather and interact with fellow enthusiasts.
  * [News & Announcements](https://forum.ansible.com/c/news/5): track project-wide announcements including social events.

* The Ansible [Bullhorn newsletter](https://docs.ansible.com/ansible/devel/community/communication.html#the-bullhorn): used to announce releases and important changes.

For more information about communication, see the [Ansible communication guide](https://docs.ansible.com/ansible/devel/community/communication.html).

## Ansible version compatibility

This collection has been tested against following Ansible versions: **>=2.15.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.

## Installation and Usage

### Installing the Collection from Ansible Galaxy

Before using the VMware collection, you need to install the collection with the `ansible-galaxy` CLI:

    ansible-galaxy collection install vmware.vmware

You can also include it in a `requirements.yml` file and install it via `ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
- name: vmware.vmware
```

### Required Python libraries

VMware community collection depends on Python 3.9+ and on following third party libraries:

* [`Pyvmomi`](https://github.com/vmware/pyvmomi)
* [`vSphere Automation SDK for Python`](https://github.com/vmware/vsphere-automation-sdk-python/)

### Installing required libraries and SDK

Installing collection does not install any required third party Python libraries or SDKs. You need to install the required Python libraries using following command:

    pip install -r ~/.ansible/collections/ansible_collections/vmware/vmware/requirements.txt

## License

GNU General Public License v3.0 or later

See [LICENSE](LICENSE) to see the full text.
