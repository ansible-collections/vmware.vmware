from ansible_collections.vmware.vmware.plugins.module_utils.vm._service_container import ServiceContainer

sc = ServiceContainer()

sc.register_instance("test", "test")

print(sc.get("test"))
