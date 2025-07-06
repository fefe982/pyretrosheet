"""Encapsulates Retrosheet event as part of play data."""

import re
from dataclasses import dataclass, field

from pyretrosheet.models.base import Base
from pyretrosheet.models.exceptions import ParseError
from pyretrosheet.models.play.advance import Advance
from pyretrosheet.models.play.description import Description
from pyretrosheet.models.play.ignored import trim_ignored_characters
from pyretrosheet.models.play.modifier import Modifier


@dataclass
class Event:
    """The event of a play as defined in Retrosheet."""

    description: Description
    modifiers: list[Modifier]
    advances: list[Advance]
    raw: str
    runner: dict[Base, Base | None] = field(init=False)

    def __post_init__(self):
        self.runner = {}
        for adv in self.advances:
            self.runner[adv.from_base] = None if adv.is_out else adv.to_base
        for o in self.description.put_out_at_base:
            self.runner[o] = None
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

        # # there are cases of double slashes which I do not believe adds any extra info - remove them
        # description_and_modifiers = description_and_modifiers.replace("//", "/")

        # # remove trailing slashes - does not encode anything
        # if description_and_modifiers.endswith("/"):
        #     description_and_modifiers = description_and_modifiers[:-1]

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

    def get_final_stat(self, prev_state: list[Base]):
        out = 0
        base = []
        bat_end = False
        score = 0
        if Base.BATTER_AT_HOME in self.runner:
            bat_end = True
            if self.runner[Base.BATTER_AT_HOME] == Base.HOME:
                score += 1
            elif self.runner[Base.BATTER_AT_HOME] is None:
                out += 1
            else:
                base.append(self.runner[Base.BATTER_AT_HOME])
        for b in prev_state:
            if b in self.runner:
                if self.runner[b] is None:
                    out += 1
                elif self.runner[b] == Base.HOME:
                    score += 1
                else:
                    base.append(self.runner[b])
            else:
                base.append(b)
        for b in self.runner:
            if b is not Base.BATTER_AT_HOME and b not in prev_state:
                raise RuntimeError("Base not in previous state: ")
        return out, score, bat_end, base
