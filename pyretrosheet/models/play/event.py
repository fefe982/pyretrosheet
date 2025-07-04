"""Encapsulates Retrosheet event as part of play data."""
import re
from dataclasses import dataclass

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
