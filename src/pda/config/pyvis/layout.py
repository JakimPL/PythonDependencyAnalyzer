from typing import Literal, TypeAlias

from pydantic import Field, field_validator

from pda.config.base import BaseConfig

LayoutMode: TypeAlias = Literal["hierarchical", "package_cloud"]
FlowDirection: TypeAlias = Literal["LR", "RL", "UD", "DU"]
RelaxationSolver: TypeAlias = Literal["forceAtlas2Based", "barnesHut", "repulsion", "hierarchicalRepulsion"]


class FlowConfig(BaseConfig):
    direction: FlowDirection = Field(
        default="LR",
        description="Axis along which inter-package dependencies flow (LR/RL = horizontal, UD/DU = vertical).",
    )
    level_separation: float = Field(
        default=200.0,
        description="Gap between the edges of clouds on consecutive levels, along the flow axis "
        "(added to the clouds' radii; inter-group spacing, independent of cloud size).",
    )
    band_spacing: float = Field(
        default=140.0,
        description="Gap between the edges of clouds sharing a level, perpendicular to the flow "
        "(added to the clouds' radii; inter-group spacing, independent of cloud size).",
    )
    crossing_reduction: bool = Field(
        default=True,
        description="Reorder packages within a level to reduce inter-package edge crossings.",
    )
    crossing_iterations: int = Field(
        default=4,
        description="Number of barycenter sweeps used when crossing reduction is enabled.",
    )

    @field_validator("level_separation", "band_spacing")
    @classmethod
    def _validate_separation(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Separation distances must be positive.")

        return value

    @field_validator("crossing_iterations")
    @classmethod
    def _validate_iterations(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Crossing iterations must be >= 0.")

        return value


class ClusterConfig(BaseConfig):
    node_spacing: float = Field(
        default=160.0,
        description="Minimum arc distance between sibling modules within a cloud (intra-group spacing). "
        "A ring's radius grows with its member count to honour this, so dense rings spread out "
        "instead of overlapping.",
    )
    ring_spacing: float = Field(
        default=140.0,
        description="Radial distance between consecutive sub-module depth rings within a package cloud.",
    )
    min_radius: float = Field(
        default=80.0,
        description="Radius of the innermost ring around a package centre.",
    )
    jitter: float = Field(
        default=0.1,
        description="Fraction of ring spacing used for deterministic, seeded radial/angular jitter.",
    )
    seed: int = Field(
        default=0,
        description="Fixed seed for the jitter RNG, so a given graph always lays out identically.",
    )

    @field_validator("node_spacing", "ring_spacing", "min_radius")
    @classmethod
    def _validate_radius(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Cluster distances must be positive.")

        return value

    @field_validator("jitter")
    @classmethod
    def _validate_jitter(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Jitter must be >= 0.")

        return value


class RelaxationConfig(BaseConfig):
    enabled: bool = Field(
        default=False,
        description="If true, computed positions seed a gentle physics simulation instead of staying fixed.",
    )
    solver: RelaxationSolver = Field(
        default="forceAtlas2Based",
        description="vis.js physics solver used during relaxation.",
    )
    gravity: int = Field(
        default=-50,
        description="The more negative the gravity value is, the stronger the repulsion is.",
    )
    central_gravity: float = Field(
        default=0.005,
        description="Pull towards the centre during relaxation; kept low to preserve the seeded structure.",
    )
    spring_length: float = Field(
        default=100.0,
        description="Rest length of edges during relaxation.",
    )
    spring_constant: float = Field(
        default=0.04,
        description="Stiffness of edges during relaxation.",
    )
    damping: float = Field(
        default=0.4,
        description="Velocity damping during relaxation.",
    )
    stabilization_iterations: int = Field(
        default=150,
        description="Maximum stabilization iterations; bounds how far nodes drift from their seed.",
    )
    anchor_centers: bool = Field(
        default=True,
        description="Pin each package centre during relaxation so the macro directional flow is preserved.",
    )

    @field_validator("stabilization_iterations")
    @classmethod
    def _validate_stabilization(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Stabilization iterations must be >= 0.")

        return value


class LayoutConfig(BaseConfig):
    mode: LayoutMode = Field(
        default="hierarchical",
        description="'hierarchical' delegates to vis.js (current tree); 'package_cloud' computes positions in Python.",
    )
    group_level: int = Field(
        default=0,
        description="Absolute dotted-name level that defines a cloud (0 = top-level package).",
    )
    flow: FlowConfig = Field(default_factory=FlowConfig)
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    relaxation: RelaxationConfig = Field(default_factory=RelaxationConfig)

    @field_validator("group_level")
    @classmethod
    def _validate_group_level(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Group level must be >= 0.")

        return value
