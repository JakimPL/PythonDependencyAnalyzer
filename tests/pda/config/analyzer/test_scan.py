import warnings
from pathlib import Path

import pytest

from pda.config import ModuleImportsAnalyzerConfig, ModuleResolutionConfig, ModuleScanConfig, ModulesCollectorConfig
from pda.exceptions import PDAExternalResolutionWarning


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

    def test_external_depth_warns_when_no_external_search_roots_are_available(self) -> None:
        with pytest.warns(PDAExternalResolutionWarning):
            ModuleImportsAnalyzerConfig(
                module_scan=ModuleScanConfig(external_depth=1),
                resolution=ModuleResolutionConfig(include_sys_path=False),
            )

    @pytest.mark.parametrize(
        "module_scan,resolution",
        [
            (
                ModuleScanConfig(external_depth=0),
                ModuleResolutionConfig(include_sys_path=False),
            ),
            (
                ModuleScanConfig(external_depth=1),
                ModuleResolutionConfig(include_sys_path=False, external_roots=(Path(".venv/site-packages"),)),
            ),
            (
                ModuleScanConfig(external_depth=1),
                ModuleResolutionConfig(include_sys_path=True),
            ),
        ],
    )
    def test_external_depth_warning_allows_disabled_or_configured_external_search(
        self,
        module_scan: ModuleScanConfig,
        resolution: ModuleResolutionConfig,
    ) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            ModuleImportsAnalyzerConfig(module_scan=module_scan, resolution=resolution)

        assert not [warning for warning in caught if issubclass(warning.category, PDAExternalResolutionWarning)]
