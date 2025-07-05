"""Represents a Retrosheet base encoding."""

from enum import Enum


class Base(Enum):
    """Retrosheet base encodings."""

    BATTER_AT_HOME = "B"
    FIRST_BASE = "1"
    SECOND_BASE = "2"
    THIRD_BASE = "3"
    HOME = "H"

    def to_order(self):
        if self == Base.BATTER_AT_HOME:
            return 0
        elif self == Base.FIRST_BASE:
            return 1
        elif self == Base.SECOND_BASE:
            return 2
        elif self == Base.THIRD_BASE:
            return 3
        elif self == Base.HOME:
            return 4
        else:
            raise ValueError("Invalid base")

    def prev_base(self):
        if self == Base.FIRST_BASE:
            return Base.BATTER_AT_HOME
        elif self == Base.SECOND_BASE:
            return Base.FIRST_BASE
        elif self == Base.THIRD_BASE:
            return Base.SECOND_BASE
        elif self == Base.HOME:
            return Base.THIRD_BASE
        else:
            raise ValueError("Invalid base")
