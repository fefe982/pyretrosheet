"""summary."""

import dataclasses
from collections import defaultdict
from pathlib import Path

import pyretrosheet
from pyretrosheet.models.base import Base
from pyretrosheet.models.play import Play
from pyretrosheet.models.play.event import Outcome
from pyretrosheet.models.player import Player
from pyretrosheet.models.radj import RAdj
from pyretrosheet.models.team import TeamLocation

# ruff: noqa: D101
# ruff: noqa: D102
# ruff: noqa: D103
# ruff: noqa: D105
# ruff: noqa: ERA001
# ruff: noqa: PLR2004
# ruff: noqa: T201

players = {}
positions = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
order = [{}, {}, {}, {}, {}, {}, {}, {}, {}, {}]
win = [0, 0, 0]


@dataclasses.dataclass
class Situation:
    score: int
    outs: int
    base: int
    inning: int
    team: TeamLocation

    def __init__(self, score: int, outs: int, base: list[tuple[Base, str]], inning: int, team: TeamLocation):
        self.score = min(max(score, -10), 10)
        self.outs = outs
        self.base = get_base_num(base)
        self.inning = min(inning, 9)
        self.team = team

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, Situation)
            and self.score == value.score
            and self.outs == value.outs
            and self.base == value.base
            and self.inning == value.inning
            and self.team == value.team
        )

    def __hash__(self) -> int:
        return hash((self.score, self.outs, self.base, self.inning, self.team))


def get_base_num(base: list[tuple[Base, str]]):
    r = 0
    for b in base:
        if b[0] == Base.FIRST_BASE:
            r += 1
        elif b[0] == Base.SECOND_BASE:
            r += 2
        elif b[0] == Base.THIRD_BASE:
            r += 4
    return r


@dataclasses.dataclass
class BatterStat:
    plate_appearances: int = 0
    at_bat: int = 0
    single: int = 0
    double: int = 0
    triple: int = 0
    home_run: int = 0

    @property
    def hit(self):
        return self.single + self.double + self.triple + self.home_run

    @property
    def avg(self):
        return self.hit / self.at_bat if self.at_bat > 0 else 0


win_cnt = defaultdict(int)
total_cnt = defaultdict(int)
batter_stat = defaultdict(BatterStat)
batter_name = {}

for game in pyretrosheet.load_games(2024, Path(Path(__file__).parent) / ".." / ".data" / "events"):
    # team_location = TeamLocation.VISITING
    # if game.home_team_id == "NYA":
    #     team_location = TeamLocation.HOME
    # elif game.visiting_team_id != "NYA":
    #     continue
    inning = 0
    team = TeamLocation.HOME
    base = []
    outs = 3
    gamescore = [0, 0]
    situation = Situation(0, 0, [], 0, TeamLocation.HOME)
    situation_cnt = defaultdict(int)
    for event in game.chronological_events:
        if outs == 3:
            outs = 0
            base = []
            if team == TeamLocation.HOME:
                inning += 1
                team = TeamLocation.VISITING
            else:
                team = TeamLocation.HOME
        new_situation = Situation(gamescore[1] - gamescore[0], outs, base, inning, team)
        if new_situation != situation:
            situation = new_situation
            situation_cnt[situation] += 1
        if isinstance(event, Player):
            batter_name[event.id] = event.name
        elif isinstance(event, Play):
            assert event.inning == inning, (event.raw, event.inning, inning)
            assert event.team_location == team, (event.raw, event.inning, event.team_location, inning, team)
            # print(event.raw)
            # for adv in event.event.advances:
            #     print(" ", adv.from_base, " -> ", "out" if adv.is_out else adv.to_base)
            out, score, bat_end, base = event.event.get_final_stat(base, event.batter_id)
            if bat_end is not None:
                batter_stat[event.batter_id].plate_appearances += 1
                if bat_end not in [
                    Outcome.WALK,
                    Outcome.HIT_BY_PITCH,
                    Outcome.SACRIFICE_BUNT,
                    Outcome.SACRIFICE_FLY,
                    Outcome.INTERFERENCE,
                ]:
                    batter_stat[event.batter_id].at_bat += 1
                    if bat_end == Outcome.SINGLE:
                        batter_stat[event.batter_id].single += 1
                    elif bat_end == Outcome.DOUBLE:
                        batter_stat[event.batter_id].double += 1
                    elif bat_end == Outcome.TRIPLE:
                        batter_stat[event.batter_id].triple += 1
                    elif bat_end == Outcome.HOME_RUN:
                        batter_stat[event.batter_id].home_run += 1
            outs += out
            # print(outs, out, score, bat_end, base)
            # print(event.event.description.put_out_at_base)
            if event.team_location == TeamLocation.HOME:
                gamescore[1] += score
            else:
                gamescore[0] += score
            # inning = event.inning
            # team = event.team_location
        elif isinstance(event, RAdj):
            assert outs == 0
            assert len(base) == 0
            base = [(event.base, event.runner_id)]
            situation_cnt[situation] -= 1
            # print("radj", base)
        # else:
        #     print(event)
    if gamescore[0] == gamescore[1]:
        win[1] += 1
    else:
        w = gamescore[0] > gamescore[1]
        if game.home_team_id == "NYA":
            w = not w
        win[0 if w else 2] += 1
    for situation, cnt in situation_cnt.items():
        total_cnt[situation] += cnt
        if gamescore[1] > gamescore[0]:
            win_cnt[situation] += cnt
    # print(gamescore)
# print(win)
# print(win_cnt)

for id, stat in batter_stat.items():
    print(
        f"{batter_name[id]}, {stat.plate_appearances}, {stat.at_bat}, {stat.single}, {stat.double}, {stat.triple}, {stat.home_run}, {stat.avg:.3f}"
    )
