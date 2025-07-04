"""Encapsulates Retrosheet play basic description as part of play data."""

import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto

from pyretrosheet.models.base import Base


class EventType(Enum):
    OUT = auto()
    DOUBLE_PLAY = auto()
    TRIPLE_PLAY = auto()
    CATCHER_INTERFERENCE = auto()
    SINGLE = auto()
    DOUBLE = auto()
    TRIPLE = auto()
    GROUND_RULE_DOUBLE = auto()
    ERROR = auto()
    FIELDERS_CHOICE = auto()
    ERROR_ON_FOUL_FLY_BALL = auto()
    HOME_RUN_LEAVING_PARK = auto()
    HOME_RUN_INSIDE_PARK = auto()
    HIT_BY_PITCH = auto()
    STRIKEOUT = auto()
    NO_PLAY = auto()
    INTENTIONAL_WALK = auto()
    WALK = auto()
    BALK = auto()
    CAUGHT_STEALING = auto()
    DEFENSIVE_INDIFFERENCE = auto()
    OTHER_ADVANCE = auto()
    PASSED_BALL = auto()
    WILD_PITCH = auto()
    PICKED_OFF = auto()
    PICKED_OFF_CAUGHT_STEALING = auto()
    STOLEN_BASE = auto()
    FILEDERS_CHOICE = auto()


@dataclass
class Description:
    """Encodes a basic play description.

    Args:
        batter_event: event performed by the batter, if any
        runner_event: event performed by a runner, if any
        fielder_assists: map of the fielder positions of players to number of assists, if any
        fielder_put_outs: map of the fielder positions of players to number of put outs, if any
        fielder_errors: map of the fielder positions of players to number of errors committed, if any
        fielder_handlers: map of the fielder positions of players to number of times the fielder
            handled the ball for a play that did not result in an out, if any
        put_out_at_base: if a put out is made at a base not normally covered by the fielder,
            the base runner is given explicitly
        stolen_base: a stolen base, if any
        raw: the raw play description
    """

    events: list[EventType]
    fielder_assists: dict[int, int]
    fielder_put_outs: dict[int, int]
    fielder_handlers: dict[int, int]
    fielder_errors: dict[int, int]
    put_out_at_base: Base | None
    stolen_base: Base | None
    implied_advance: list[Base]
    raw: str

    @classmethod
    def from_event_description(cls, description: str) -> "Description":
        """Load a description from the description part of a play's event.

        Args:
            description: the description part of a play's event
        """
        events = _get_event_type(description)
        fielding_out_plays = _get_fielding_out_plays(description, events)
        fielding_handler_plays = _get_fielding_handler_plays(description, events)
        return cls(
            events=[_[0] for _ in events],
            fielder_assists=_get_fielder_assists(fielding_out_plays),
            fielder_put_outs=_get_fielder_put_outs(fielding_out_plays),
            fielder_handlers=_get_fielder_handlers(fielding_handler_plays),
            fielder_errors=_get_fielder_errors(description, events),
            put_out_at_base=_get_put_out_at_base(description, events),
            stolen_base=_get_stolen_base(description, events),
            raw=description,
            implied_advance=[],
        )


def _get_event_type(description: str) -> list[tuple[EventType, re.Match]]:
    pattern_to_batter_event = {
        r"(?P<a0>\d+)?(?P<p0>\d)(\((?P<b0>.)\))?": EventType.OUT,
        r"(?P<a0>\d+)?(?P<p0>\d)\((?P<b0>.)\)(?P<a1>\d+)?(?P<p1>\d)(\((?P<b1>.)\))?": EventType.DOUBLE_PLAY,
        r"(?P<a0>\d+)?(?P<p0>\d)\((?P<b0>.)\)(?P<a1>\d+)?(?P<p1>\d)\((?P<b1>.)\)(?P<a2>\d+)?(?P<p2>\d)(\((?P<b2>.)\))?": EventType.TRIPLE_PLAY,
        r"H(R)?": EventType.HOME_RUN_LEAVING_PARK,
        r"H(R)?\d": EventType.HOME_RUN_INSIDE_PARK,
        # S, D, and T optionally include the fielder info
        r"S(\d+)?": EventType.SINGLE,
        r"D(\d+)?": EventType.DOUBLE,
        r"T(\d+)?": EventType.TRIPLE,
        r"\d*E\d": EventType.ERROR,
        r"FLE\d": EventType.ERROR_ON_FOUL_FLY_BALL,
        r"FC\d": EventType.FIELDERS_CHOICE,
        r"C": EventType.CATCHER_INTERFERENCE,
        r"HP": EventType.HIT_BY_PITCH,
        r"DGR": EventType.GROUND_RULE_DOUBLE,
        r"K": EventType.STRIKEOUT,
        r"W": EventType.WALK,
        r"I(W)?": EventType.INTENTIONAL_WALK,
        r"NP": EventType.NO_PLAY,
        r"BK": EventType.BALK,
        r"CS[23H]\(.*\)": EventType.CAUGHT_STEALING,
        r"DI": EventType.DEFENSIVE_INDIFFERENCE,
        r"OA": EventType.OTHER_ADVANCE,
        r"PB": EventType.PASSED_BALL,
        r"WP": EventType.WILD_PITCH,
        r"PO[123H]\(.*\)": EventType.PICKED_OFF,
        r"POCS[123H]\(.*\)": EventType.PICKED_OFF_CAUGHT_STEALING,
        r"SB[23H]": EventType.STOLEN_BASE,
        r"FC": EventType.FILEDERS_CHOICE,
    }
    descriptions = re.split(r"[+;]", description)
    events = []
    for desc in descriptions:
        for pattern, batter_event in pattern_to_batter_event.items():
            if match := re.fullmatch(pattern, desc):
                events.append((batter_event, match))
                break
        else:
            assert False, f"Could not determine event type for description: {desc} in event: {description}"
    return events


def _get_fielding_out_plays(description: str, events: list[tuple[EventType, re.Match]]) -> list[str]:
    """Get the fielding plays resulting in outs.

    Plays in this context is a string that contains the fielding positions of the fielders involved in the out.

    Args:
        description: the description part of a play's event
        batter_event: the batting event, if it exists
        runner_event: the runner event, if it exists
    """
    fielding_out_plays: list[str] = []
    for event_type, m in events:
        match event_type:
            case EventType.OUT | EventType.DOUBLE_PLAY | EventType.TRIPLE_PLAY:
                for i in range(3):
                    try:
                        p = m.group(f"a{i}")
                        if p is None:
                            p = ""
                    except IndexError:
                        p = ""
                    try:
                        p += m.group(f"p{i}")
                    except IndexError:
                        break
                    fielding_out_plays.append(p)

            case EventType.CAUGHT_STEALING | EventType.PICKED_OFF | EventType.PICKED_OFF_CAUGHT_STEALING:
                # errors, 'E', does not result in an out so we skip these runner events
                if not re.fullmatch(r".*\(.*E.*\)", description):
                    fielding_out_plays.append(re.fullmatch(r".*\((.*)\)", description).group(1))  # type: ignore

    corrected_fielding_out_plays = []
    for play in fielding_out_plays:
        # ! represents an exceptional play, which we can ignore here
        corrected_part = play
        if "!" in play:
            corrected_part = play.replace("!", "")
        corrected_fielding_out_plays.append(corrected_part)

    return corrected_fielding_out_plays


def _get_fielding_handler_plays(description: str, events: list[tuple[EventType, re.Match]]) -> list[str]:
    """Get fielding handler plays (plays that did not result in error or outs).

    Plays in this context is a string that contains the fielding positions of the fielders involved in the handling
    of the play.

    Args:
        description: the description part of a play's event
        batter_event: the batting event, if it exists
        runner_event: the runner event, if it exists
    """
    fielding_handler_plays: list[str] = []
    for event_type, m in events:
        match event_type:
            case (
                EventType.SINGLE
                | EventType.DOUBLE
                | EventType.TRIPLE
                | EventType.FIELDERS_CHOICE
                | EventType.HOME_RUN_INSIDE_PARK
            ):
                # will not match in the case of fielder info not being present, e.g. description = "S"
                if match := re.fullmatch(r"(S|D|T|FC|H|HR)(\d+)", description):
                    fielding_handler_plays.append(match.group(2))
            case EventType.CAUGHT_STEALING | EventType.PICKED_OFF | EventType.PICKED_OFF_CAUGHT_STEALING:
                match = re.fullmatch(r".*\((.*)\)", description)
                fielder_positions = match.group(1)  # type: ignore
                fielder_positions_not_part_of_an_error = []
                parts = fielder_positions.split("/")
                for part in parts:
                    has_error = False
                    for i, fielder_position in enumerate(part):
                        if fielder_position == "E" or part[i - 1] == "E":
                            has_error = True
                            continue

                        fielder_positions_not_part_of_an_error.append(fielder_position)

                    # no outs would occur if there is an error
                    if fielder_positions_not_part_of_an_error and has_error:
                        fielding_handler_plays.append("".join(fielder_positions_not_part_of_an_error))

    return fielding_handler_plays


def _get_fielder_assists(fielding_out_plays: list[str]) -> dict[int, int]:
    """Get a map of fielder positions and the number of assists they made on the play.

    Args:
        fielding_out_plays: plays where fielding outs occurred
    """
    fielder_assists: defaultdict[int, int] = defaultdict(int)
    for play in fielding_out_plays:
        if len(play) == 0:
            continue

        for fielder_position in play[:-1]:
            fielder_assists[int(fielder_position)] += 1

    return dict(fielder_assists)


def _get_fielder_put_outs(fielding_out_plays: list[str]) -> dict[int, int]:
    """Get a map of fielder positions and the number of put outs they made on the play.

    Args:
        fielding_out_plays: plays where fielding outs occurred
    """
    fielder_put_outs: defaultdict[int, int] = defaultdict(int)
    for play in fielding_out_plays:
        put_out_position = int(play[-1])
        fielder_put_outs[put_out_position] += 1

    return dict(fielder_put_outs)


def _get_fielder_handlers(fielding_handler_plays: list[str]) -> dict[int, int]:
    """Get a map of fielder positions and the number of handling actions they made on the play.

    Args:
        fielding_handler_plays: plays where fielding handling occurred
    """
    fielder_handlers: defaultdict[int, int] = defaultdict(int)
    for play in fielding_handler_plays:
        for fielder_position in play:
            fielder_handlers[int(fielder_position)] += 1

    return dict(fielder_handlers)


def _get_fielder_errors(description: str, events: list[tuple[EventType, re.Match]]) -> dict[int, int]:
    """Get a map of fielder positions and the number of errors they made on the play.

    Args:
        description: the description part of a play's event
        batter_event: the batting event, if it exists
        runner_event: the runner event, if it exists
    """
    fielder_errors: defaultdict[int, int] = defaultdict(int)
    for event_type, _ in events:
        match event_type:
            case EventType.ERROR:
                if match := re.fullmatch(r"E(\d+)", description):
                    for fielder_position in match.group(1):
                        fielder_errors[int(fielder_position)] += 1

                if match := re.fullmatch(r"\dE(\d+)", description):
                    for fielder_position in match.group(1):
                        fielder_errors[int(fielder_position)] += 1

            case EventType.ERROR_ON_FOUL_FLY_BALL:
                match = re.fullmatch(r"FLE(\d+)", description)
                for fielder_position in match.group(1):  # type: ignore
                    fielder_errors[int(fielder_position)] += 1

            case EventType.CAUGHT_STEALING | EventType.PICKED_OFF | EventType.PICKED_OFF_CAUGHT_STEALING:
                if match := re.fullmatch(r".*\((.*E.*)\)", description):
                    fielder_positions = match.group(1)
                    for i, fielder_position in enumerate(fielder_positions):
                        if fielder_position == "E":
                            # the fielder position following the 'E' is the player that made the error
                            fielder_errors[int(fielder_positions[i + 1])] += 1

    return dict(fielder_errors)


def _get_put_out_at_base(description: str, events: list[tuple[EventType, re.Match]]) -> Base | None:
    """Get the base of a put out if it's a non-conventional base put out at.

    Args:
        description: the description part of a play's event
        batter_event: the batting event, if it exists
    """
    for event_type, _ in events:
        if event_type == EventType.OUT:
            match = re.fullmatch(r"\d+\((.)\)", description)
            if match:
                return Base(match.group(1))
    return None


def _get_stolen_base(description: str, events: list[tuple[EventType, re.Match]]) -> Base | None:
    for event_type, _ in events:
        if event_type == EventType.STOLEN_BASE:
            return Base(re.fullmatch(r".*SB([23H])", description).group(1))  # type: ignore

    return None
