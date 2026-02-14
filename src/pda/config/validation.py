import warnings
from typing import Self

from pydantic import Field, model_validator

from pda.config.base import BaseConfig
from pda.exceptions import PDAValidationOptionsWarning


class ValidationOptions(BaseConfig):
    allow_missing_spec: bool = Field(
        default=False,
        description="Whether to allow missing module specs during validation, "
        "treating them as invalid modules instead of raising an error.",
    )
    validate_origin: bool = Field(
        default=True,
        description="Whether to validate the module's origin path during spec validation",
    )
    expect_python: bool = Field(
        default=True,
        description="Whether to expect the module's origin to be a Python file during spec validation.",
    )
    raise_error: bool = Field(
        default=True,
        description="Whether to raise an error during finding module specs "
        "if the module cannot be found or validated, instead of returning None.",
    )

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        if not self.validate_origin and self.expect_python:
            warnings.warn(
                "Option 'expect_python' has no effect when 'validate_origin' is False",
                PDAValidationOptionsWarning,
            )

        return self

    @classmethod
    def strict(cls) -> Self:
        return cls(
            allow_missing_spec=True,
            validate_origin=True,
            expect_python=True,
            raise_error=True,
        )

    @classmethod
    def permissive(cls) -> Self:
        return cls(
            allow_missing_spec=True,
            validate_origin=False,
            expect_python=False,
            raise_error=False,
        )
