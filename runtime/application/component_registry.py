from __future__ import annotations

from typing import Any, TypeVar


T = TypeVar("T")


class ComponentRegistry:
    """
    Registry for Application-level runtime components.

    ComponentRegistry is responsible only for:

        - registering components
        - retrieving components
        - checking component existence

    It does NOT:

        - create components
        - manage component lifecycle
        - execute components
        - resolve dependency graphs

    ApplicationAssembly is responsible for component construction
    and composition.
    """

    def __init__(self) -> None:
        self._components: dict[str, Any] = {}

    def register(
        self,
        name: str,
        component: Any,
    ) -> None:
        """
        Register an Application component.

        Component names must be unique.
        """
        if not name:
            raise ValueError("Component name cannot be empty.")

        if name in self._components:
            raise ValueError(
                f"Component already registered: {name}"
            )

        self._components[name] = component

    def get(self, name: str) -> Any:
        """
        Retrieve a registered component.

        Raises:
            KeyError: if the component does not exist.
        """
        try:
            return self._components[name]
        except KeyError:
            raise KeyError(
                f"Component not found: {name}"
            ) from None

    def contains(self, name: str) -> bool:
        """
        Return whether a component is registered.
        """
        return name in self._components

    def __contains__(self, name: str) -> bool:
        return self.contains(name)

    def items(self) -> tuple[tuple[str, Any], ...]:
        """
        Return a read-only snapshot of registered components.

        Dict insertion order is preserved so Application lifecycle
        orchestration is deterministic.
        """
        return tuple(self._components.items())

    def __len__(self) -> int:
        return len(self._components)