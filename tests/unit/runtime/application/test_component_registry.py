import pytest

from runtime.application.component_registry import ComponentRegistry


def test_registry_is_empty_initially():
    registry = ComponentRegistry()

    assert len(registry) == 0


def test_registry_can_register_component():
    registry = ComponentRegistry()

    component = object()

    registry.register("component", component)

    assert registry.get("component") is component
    assert registry.contains("component")
    assert "component" in registry
    assert len(registry) == 1


def test_registry_preserves_component_identity():
    registry = ComponentRegistry()

    component = object()

    registry.register("component", component)

    retrieved = registry.get("component")

    assert retrieved is component


def test_registry_rejects_duplicate_component_name():
    registry = ComponentRegistry()

    registry.register("component", object())

    with pytest.raises(
        ValueError,
        match="Component already registered: component",
    ):
        registry.register("component", object())


def test_registry_rejects_empty_component_name():
    registry = ComponentRegistry()

    with pytest.raises(
        ValueError,
        match="Component name cannot be empty",
    ):
        registry.register("", object())


def test_registry_get_unknown_component_raises_key_error():
    registry = ComponentRegistry()

    with pytest.raises(
        KeyError,
        match="Component not found: unknown",
    ):
        registry.get("unknown")


def test_registry_contains_returns_false_for_unknown_component():
    registry = ComponentRegistry()

    assert registry.contains("unknown") is False
    assert "unknown" not in registry