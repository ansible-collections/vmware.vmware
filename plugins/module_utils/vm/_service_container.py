from abc import ABC, abstractmethod
from typing import Dict, Any, Callable


class ServiceContainer:
    """
    Dependency injection container for VM module components
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}

    def register_instance(self, name: str, instance: Any):
        """
        Register a service instance
        """
        self._services[name] = instance

    def register_factory(self, name: str, factory: Callable[[], Any]):
        """
        Register a factory function for lazy initialization
        """
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        """
        Get a service instance, creating if needed
        """
        if name in self._services:
            return self._services[name]

        if name in self._factories:
            instance = self._factories[name]()
            self._services[name] = instance
            return instance

        raise ValueError("Service '%s' not found" % name)

    def has(self, name: str) -> bool:
        """
        Check if service is registered
        """
        return name in self._services or name in self._factories


class ServiceAware(ABC):
    """
    Base class for components that use dependency injection
    """
    def __init__(self, container: ServiceContainer):
        self.container = container
        self._configure_dependencies()

    @abstractmethod
    def _configure_dependencies(self):
        """
        Configure dependencies from container
        """
        # Override in subclasses to configure specific dependencies
        pass
