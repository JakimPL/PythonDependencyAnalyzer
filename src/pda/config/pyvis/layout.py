from typing import Literal, TypeAlias

from pydantic import Field, field_validator

from pda.config.base import BaseConfig

LayoutMode: TypeAlias = Literal["hierarchical", "package_ring"]
RelaxationSolver: TypeAlias = Literal["forceAtlas2Based", "barnesHut", "repulsion", "hierarchicalRepulsion"]


class RingConfig(BaseConfig):
    node_spacing: float = Field(
        default=160.0,
        description="Minimum arc distance between modules on the same ring. A ring's radius grows with its "
        "member count to honour this, so crowded rings are pushed outward instead of overlapping.",
    )
    ring_spacing: float = Field(
        default=140.0,
        description="Radial distance between consecutive package-depth rings.",
    )
    min_radius: float = Field(
        default=80.0,
        description="Radius of the innermost ring (package depth 1) around the centre.",
    )
    dependency_blend: float = Field(
        default=0.4,
        description="How strongly topological dependency level positions a node within its depth ring "
        "(0 = pure equi-radial rings; 1 = full band thickness so importers/imports sit on adjacent sub-rings).",
    )
    edge_pull: float = Field(
        default=0.5,
        description="How strongly a node's angle is nudged toward its import neighbours, clamped within its "
        "package wedge (0 = strict package wedges; 1 = maximum in-wedge pull toward connected modules).",
    )
    order_iterations: int = Field(
        default=4,
        description="Number of circular-barycenter sweeps used to order packages and siblings around the rings.",
    )
    nudge_passes: int = Field(
        default=10,
        description="Number of bounded angular nudge passes applied to reduce edge length.",
    )
    repulsion: float = Field(
        default=0.0,
        description="Antigravity strength that pushes overlapping nodes apart (0 = off). Repulsion acts only on "
        "nodes closer than 'node_spacing' and stays within each node's package wedge (angle) and depth band "
        "(radius), so the ring structure is preserved.",
    )
    repulsion_iterations: int = Field(
        default=50,
        description="Number of repulsion relaxation passes applied to separate overlapping nodes.",
    )
    wedge_margin: float = Field(
        default=0.0,
        description="Angular margin (radians) kept clear at each wedge's edges when nudging.",
    )
    jitter: float = Field(
        default=0.0,
        description="Fraction of ring spacing used for deterministic, seeded radial jitter.",
    )
    seed: int = Field(
        default=0,
        description="Fixed seed for the jitter RNG, so a given graph always lays out identically.",
    )

    @field_validator("node_spacing", "ring_spacing", "min_radius")
    @classmethod
    def _validate_radius(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Ring distances must be positive.")

        return value

    @field_validator("dependency_blend", "edge_pull")
    @classmethod
    def _validate_fraction(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Blend factors must be within [0, 1].")

        return value

    @field_validator("wedge_margin", "jitter", "repulsion")
    @classmethod
    def _validate_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Margins must be >= 0.")

        return value

    @field_validator("order_iterations", "nudge_passes", "repulsion_iterations")
    @classmethod
    def _validate_iterations(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Iteration counts must be >= 0.")

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
        description="Pin the centre node during relaxation so the macro ring structure is preserved.",
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
        description="'hierarchical' delegates to vis.js (current tree); 'package_ring' computes positions in Python.",
    )
    ring: RingConfig = Field(default_factory=RingConfig)
    relaxation: RelaxationConfig = Field(default_factory=RelaxationConfig)
