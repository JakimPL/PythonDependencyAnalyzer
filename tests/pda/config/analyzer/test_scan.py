import pytest

from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig, ModulesCollectorConfig


class TestDepthValidation:
    @pytest.mark.parametrize("field", ["stdlib_depth", "external_depth"])
    def test_negative_rejected(self, field: str) -> None:
        with pytest.raises(ValueError):
            ModuleScanConfig(**{field: -1})

    def test_none_and_zero_allowed(self) -> None:
        config = ModuleScanConfig(stdlib_depth=None, external_depth=0)

        assert config.stdlib_depth is None
        assert config.external_depth == 0


class TestWrapperDefaults:
    def test_collector_defaults_recurse_everything(self) -> None:
        config = ModulesCollectorConfig()

        assert config.stdlib_depth is None
        assert config.external_depth is None
        assert config.collapse_level is None
        assert config.max_depth is None

    def test_imports_defaults_are_boundary_only(self) -> None:
        config = ModuleImportsAnalyzerConfig()

        assert config.stdlib_depth == 1
        assert config.external_depth == 1
        assert config.collapse_level is None

    def test_wrapper_depth_passthroughs_delegate(self) -> None:
        config = ModulesCollectorConfig(module_scan=ModuleScanConfig(stdlib_depth=2, external_depth=0))

        assert config.stdlib_depth == 2
        assert config.external_depth == 0

    @pytest.mark.parametrize("config_class", [ModulesCollectorConfig, ModuleImportsAnalyzerConfig])
    def test_collapse_level_validation(self, config_class: type) -> None:
        with pytest.raises(ValueError):
            config_class(collapse_level=-1)
