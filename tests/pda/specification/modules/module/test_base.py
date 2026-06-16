import pytest

from pda.specification import UnavailableModule


class TestModulePrefix:
    @pytest.mark.parametrize(
        "name, level, expected",
        [
            ("package.subpackage.module", 0, "package"),
            ("package.subpackage.module", 1, "package.subpackage"),
            ("package.subpackage.module", 2, "package.subpackage.module"),
            # Clamping: level beyond the number of components yields the full name.
            ("package.subpackage.module", 5, "package.subpackage.module"),
            ("single", 0, "single"),
            ("single", 3, "single"),
        ],
    )
    def test_prefix(self, name: str, level: int, expected: str) -> None:
        module = UnavailableModule(name=name)
        assert module.prefix(level) == expected

    def test_prefix_strips_init(self) -> None:
        module = UnavailableModule(name="package.subpackage.__init__")
        assert module.qualified_name == "package.subpackage"
        assert module.prefix(0) == "package"
        assert module.prefix(1) == "package.subpackage"
