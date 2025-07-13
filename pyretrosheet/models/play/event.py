"""Encapsulates Retrosheet event as part of play data."""

import re
from dataclasses import dataclass, field
from enum import Enum, auto

from pyretrosheet.models.base import Base
from pyretrosheet.models.exceptions import ParseError
from pyretrosheet.models.play.advance import Advance
from pyretrosheet.models.play.description import Description, EventType
from pyretrosheet.models.play.ignored import trim_ignored_characters
from pyretrosheet.models.play.modifier import Modifier, ModifierType


class Outcome(Enum):
    """The outcome of a play."""

    SINGLE = auto()
    DOUBLE = auto()
    TRIPLE = auto()
    HOME_RUN = auto()
    STRIKE_OUT = auto()
    OUT = auto()
    WALK = auto()
    HIT_BY_PITCH = auto()
    ERROR = auto()
    SACRIFICE_FLY = auto()
    SACRIFICE_BUNT = auto()
    INTERFERENCE = auto()
    FIELDERS_CHOICE = auto()


_ModifierType_to_Outcome = {
    ModifierType.SACRIFICE_FLY: Outcome.SACRIFICE_FLY,
    ModifierType.SACRIFICE_HIT_BUNT: Outcome.SACRIFICE_BUNT,
}

_EvnetType_To_Outcome = {
    EventType.SINGLE: Outcome.SINGLE,
    EventType.DOUBLE: Outcome.DOUBLE,
    EventType.GROUND_RULE_DOUBLE: Outcome.DOUBLE,
    EventType.TRIPLE: Outcome.TRIPLE,
    EventType.HOME_RUN_INSIDE_PARK: Outcome.HOME_RUN,
    EventType.HOME_RUN_LEAVING_PARK: Outcome.HOME_RUN,
    EventType.STRIKEOUT: Outcome.STRIKE_OUT,
    EventType.ERROR: Outcome.ERROR,
    EventType.HIT_BY_PITCH: Outcome.HIT_BY_PITCH,
    EventType.WALK: Outcome.WALK,
    EventType.INTENTIONAL_WALK: Outcome.WALK,
    EventType.CATCHER_INTERFERENCE: Outcome.INTERFERENCE,
    EventType.OUT: Outcome.OUT,
    EventType.DOUBLE_PLAY: Outcome.OUT,
    EventType.TRIPLE_PLAY: Outcome.OUT,
    EventType.FIELDERS_CHOICE: Outcome.FIELDERS_CHOICE,
}


class UnkownOutcomeError(Exception):
    """Error when unable to find an outcome for an event."""

    def __init__(self, event: str):
        super().__init__(f"Unable to find outcome for event {event}")


class IllegalStateError(Exception):
    """Error when an event is in an illegal state."""

    def __init__(self, base: Base):
        super().__init__(f"{base} is not found in state")


@dataclass
class Event:
    """The event of a play as defined in Retrosheet."""

    description: Description
    modifiers: list[Modifier]
    advances: list[Advance]
    raw: str
    runner: dict[Base, Base | None] = field(init=False)

    def __post_init__(self):
        """Post-initialization."""
        self.runner = {adv.from_base: None if adv.is_out else adv.to_base for adv in self.advances}
        self.runner.update(dict.fromkeys(self.description.put_out_at_base, None))
        if Base.BATTER_AT_HOME not in self.runner and self.description.implicit_advance != Base.BATTER_AT_HOME:
            self.runner[Base.BATTER_AT_HOME] = self.description.implicit_advance
        for b in self.description.stolen_base:
            pb = b.prev_base()
            if pb not in self.runner:
                self.runner[pb] = b
        for b in self.description.caught_stolen[0]:
            pb = b.prev_base()
            if pb not in self.runner:
                self.runner[pb] = None
        for b in self.description.caught_stolen[1]:
            pb = b.prev_base()
            if pb not in self.runner:
                self.runner[pb] = b
        for b in self.description.pick_off[0]:
            if b not in self.runner:
                self.runner[b] = None
        for b in self.description.pick_off[1]:
            if b not in self.runner:
                self.runner[b] = b

    @classmethod
    def from_play_event(cls, event: str) -> "Event":
        """Load an event from a play line event value.

        Args:
            event: the event description (last part of a play line)
                Examples include: '8/F78', '9/SF.3-H', 'S9/L9S.2-H;1-3'
        """
        event_trimmed = trim_ignored_characters(event)

        event_splits = event_trimmed.split(".")
        description_and_modifiers = event_splits[0]
        advances = []
        for event_split in event_splits[1:]:
            advances.extend(event_split.split(";"))

        # I shamelessly used ChatGPT for this pattern since it's difficult to separate the description and modifiers
        # consistently.
        # Examples (description and modifiers split out):
        # A => 'A', []
        # A/B/C => 'A', ['B', 'C']
        # A(1/2) => 'A(1/2)', []
        # A(1/2)/B => 'A(1/2)', ['B']
        parts = re.split(r"/(?![^(]*\))|$", description_and_modifiers)
        try:
            description = parts[0]
            modifiers = [p for p in parts[1:] if p]
        except AttributeError as e:
            raise ParseError("description_and_modifiers", event_trimmed) from e

        return cls(
            description=Description.from_event_description(description),
            modifiers=[Modifier.from_event_modifier(m) for m in modifiers],
            advances=[Advance.from_event_advance(a) for a in advances],
            raw=event,
        )

    def get_out_come(self):
        """Get the outcome of the event."""
        for modifiers in self.modifiers:
            if modifiers.type in _ModifierType_to_Outcome:
                return _ModifierType_to_Outcome[modifiers.type]
        for event in self.description.events:
            if event in _EvnetType_To_Outcome:
                return _EvnetType_To_Outcome[event]
        raise UnkownOutcomeError(self.description.raw)

    def get_final_stat(self, prev_state: list[tuple[Base, str]], batter: str):
        """Get the final state of the event."""
        out = 0
        base = []
        bat_end = None
        score = 0
        if Base.BATTER_AT_HOME in self.runner:
            if self.runner[Base.BATTER_AT_HOME] == Base.HOME:
                score += 1
            elif self.runner[Base.BATTER_AT_HOME] is None:
                out += 1
            else:
                base.append((self.runner[Base.BATTER_AT_HOME], batter))
            bat_end = self.get_out_come()
        for b in prev_state:
            if b[0] in self.runner:
                if self.runner[b[0]] is None:
                    out += 1
                elif self.runner[b[0]] == Base.HOME:
                    score += 1
                else:
                    base.append((self.runner[b[0]], b[1]))
            else:
                base.append(b)
        for b in self.runner:
            if b is not Base.BATTER_AT_HOME and not any(b == s[0] for s in prev_state):
                raise IllegalStateError(b)
        return out, score, bat_end, base
