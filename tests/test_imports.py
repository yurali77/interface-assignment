from importlib import import_module


def test_core_packages_import() -> None:
    packages = (
        "interface_automation",
        "interface_automation.models",
        "interface_automation.surface",
        "interface_automation.replay",
    )
    for name in packages:
        import_module(name)
