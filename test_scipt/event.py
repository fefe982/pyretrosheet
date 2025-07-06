"""summary."""

import dataclasses
from collections import defaultdict
from pathlib import Path

import pyretrosheet
from pyretrosheet.models.base import Base
from pyretrosheet.models.play import Play
from pyretrosheet.models.player import Player
from pyretrosheet.models.radj import RAdj
from pyretrosheet.models.team import TeamLocation

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

    def __init__(self, score: int, outs: int, base: list[Base], inning: int, team: TeamLocation):
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


def get_base_num(base: list[Base]):
    r = 0
    for b in base:
        if b == Base.FIRST_BASE:
            r += 1
        elif b == Base.SECOND_BASE:
            r += 2
        elif b == Base.THIRD_BASE:
            r += 4
    return r


win_cnt = defaultdict(int)
total_cnt = defaultdict(int)

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
        if isinstance(event, RAdj):
            assert outs == 0
            assert len(base) == 0
            base = [event.base]
            situation_cnt[situation] -= 1
            # print("radj", base)
        elif isinstance(event, Play):
            assert event.inning == inning, (event.raw, event.inning, inning)
            assert event.team_location == team, (event.raw, event.inning, event.team_location, inning, team)
            # print(event.raw)
            # for adv in event.event.advances:
            #     print(" ", adv.from_base, " -> ", "out" if adv.is_out else adv.to_base)
            out, score, bat_end, base = event.event.get_final_stat(base)
            outs += out
            # print(outs, out, score, bat_end, base)
            # print(event.event.description.put_out_at_base)
            if event.team_location == TeamLocation.HOME:
                gamescore[1] += score
            else:
                gamescore[0] += score
            # inning = event.inning
            # team = event.team_location
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
print(win_cnt)
