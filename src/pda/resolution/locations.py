from importlib.machinery import ModuleSpec
from pathlib import Path

from pda.resolution.classification import ModuleClassifier
from pda.resolution.models.identity import ModuleIdentity
from pda.resolution.models.location import ModuleCoordinates, ModuleLocation
from pda.specification.imports.origin import OriginType
from pda.tools.paths import resolve_path


class ModuleLocationFactory:
    def __init__(self, classifier: ModuleClassifier) -> None:
        self._classifier = classifier

    def from_spec(self, spec: ModuleSpec) -> ModuleCoordinates:
        origin_type = OriginType.from_origin(spec.origin)
        origin = self._origin_from_spec(spec, origin_type)
        locations: tuple[Path, ...] = tuple(
            resolved_location
            for raw_location in (spec.submodule_search_locations or ())
            if (resolved_location := resolve_path(raw_location)) is not None
        )
        location = ModuleLocation(
            origin=origin,
            origin_type=origin_type,
            submodule_search_locations=locations,
            matched_root=self._classifier.matched_root(origin, locations),
            namespace_portions=self._classifier.namespace_portions_for(origin, locations),
        )
        return ModuleCoordinates(
            identity=ModuleIdentity(spec.name),
            location=location,
        )

    def _origin_from_spec(
        self,
        spec: ModuleSpec,
        origin_type: OriginType,
    ) -> Path | None:
        if origin_type in {
            OriginType.BUILT_IN,
            OriginType.FROZEN,
            OriginType.NONE,
        }:
            return None

        return resolve_path(spec.origin)
