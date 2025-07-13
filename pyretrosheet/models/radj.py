"""Defines the RAdj dataclass for representing runner adjustments in the pyretrosheet models."""

from dataclasses import dataclass

from pyretrosheet.models.base import Base

# ruff:noqa: D101


@dataclass
class RAdj:
    runner_id: str
    base: Base
