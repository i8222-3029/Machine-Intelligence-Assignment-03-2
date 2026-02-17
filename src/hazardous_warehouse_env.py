"""
Hazardous Warehouse Environment.

A partially observable grid world with hidden hazards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import NamedTuple
import random


class Direction(Enum):
    NORTH = auto()
    EAST = auto()
    SOUTH = auto()
    WEST = auto()

    def turn_left(self) -> "Direction":
        order = [Direction.NORTH, Direction.WEST, Direction.SOUTH, Direction.EAST]
        return order[(order.index(self) + 1) % 4]

    def turn_right(self) -> "Direction":
        order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
        return order[(order.index(self) + 1) % 4]

    def delta(self) -> tuple[int, int]:
        return {
            Direction.NORTH: (0, 1),
            Direction.EAST: (1, 0),
            Direction.SOUTH: (0, -1),
            Direction.WEST: (-1, 0),
        }[self]


class Action(Enum):
    FORWARD = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    GRAB = auto()
    SHUTDOWN = auto()
    EXIT = auto()


class Percept(NamedTuple):
    creaking: bool
    rumbling: bool
    beacon: bool
    bump: bool
    beep: bool


@dataclass
class RobotState:
    x: int
    y: int
    direction: Direction
    has_package: bool = False
    has_shutdown_device: bool = True
    alive: bool = True


@dataclass
class HazardousWarehouseEnv:
    """
    Hazardous Warehouse environment for knowledge-based agents.

    Grid coordinates: (x, y), x in [1..width], y in [1..height], origin bottom-left.
    """

    width: int = 4
    height: int = 4
    num_damaged: int = 2
    seed: int | None = None

    _damaged: set[tuple[int, int]] = field(default_factory=set)
    _forklift: tuple[int, int] | None = None
    _forklift_alive: bool = True
    _package: tuple[int, int] | None = None

    _robot: RobotState = field(default_factory=lambda: RobotState(1, 1, Direction.EAST))

    _steps: int = 0
    _total_reward: float = 0.0
    _last_percept: Percept = field(default_factory=lambda: Percept(False, False, False, False, False))
    _terminated: bool = False
    _success: bool = False
    _history: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self, seed: int | None = None) -> Percept:
        if seed is not None:
            self.seed = seed
        if self.seed is not None:
            random.seed(self.seed)

        all_positions = [
            (x, y)
            for x in range(1, self.width + 1)
            for y in range(1, self.height + 1)
            if (x, y) != (1, 1)
        ]
        random.shuffle(all_positions)

        self._damaged = set(all_positions[: self.num_damaged])
        remaining = all_positions[self.num_damaged :]
        self._forklift = remaining[0]
        self._package = remaining[1]
        self._forklift_alive = True

        self._robot = RobotState(1, 1, Direction.EAST)

        self._steps = 0
        self._total_reward = 0.0
        self._terminated = False
        self._success = False
        self._history = []

        self._last_percept = self._get_percept(bump=False, beep=False)
        self._record_state()
        return self._last_percept

    def step(self, action: Action) -> tuple[Percept, float, bool, dict]:
        if self._terminated:
            return self._last_percept, 0.0, True, {"error": "Episode already terminated"}

        reward = -1.0
        bump = False
        beep = False
        info: dict = {"action": action.name}

        if action == Action.FORWARD:
            bump = self._move_forward()
            if not bump and self._robot.alive:
                pos = (self._robot.x, self._robot.y)
                if pos in self._damaged:
                    self._robot.alive = False
                    reward = -1000.0
                    self._terminated = True
                    info["death"] = "damaged_floor"
                elif pos == self._forklift and self._forklift_alive:
                    self._robot.alive = False
                    reward = -1000.0
                    self._terminated = True
                    info["death"] = "forklift"

        elif action == Action.TURN_LEFT:
            self._robot.direction = self._robot.direction.turn_left()

        elif action == Action.TURN_RIGHT:
            self._robot.direction = self._robot.direction.turn_right()

        elif action == Action.GRAB:
            pos = (self._robot.x, self._robot.y)
            if pos == self._package and not self._robot.has_package:
                self._robot.has_package = True
                info["grabbed"] = True
            else:
                info["grabbed"] = False

        elif action == Action.SHUTDOWN:
            if self._robot.has_shutdown_device:
                self._robot.has_shutdown_device = False
                reward -= 9.0
                beep = self._fire_shutdown()
                info["shutdown_success"] = beep
            else:
                info["shutdown_success"] = False
                info["error"] = "No shutdown device"

        elif action == Action.EXIT:
            pos = (self._robot.x, self._robot.y)
            if pos == (1, 1):
                self._terminated = True
                if self._robot.has_package:
                    reward = 1000.0
                    self._success = True
                    info["exit"] = "success"
                else:
                    info["exit"] = "no_package"
            else:
                info["exit"] = "wrong_location"

        self._steps += 1
        self._total_reward += reward

        if self._robot.alive:
            self._last_percept = self._get_percept(bump=bump, beep=beep)
        else:
            self._last_percept = Percept(False, False, False, bump, beep)

        self._record_state(action)
        return self._last_percept, reward, self._terminated, info

    def _move_forward(self) -> bool:
        dx, dy = self._robot.direction.delta()
        new_x = self._robot.x + dx
        new_y = self._robot.y + dy

        if new_x < 1 or new_x > self.width or new_y < 1 or new_y > self.height:
            return True

        self._robot.x = new_x
        self._robot.y = new_y
        return False

    def _fire_shutdown(self) -> bool:
        if not self._forklift_alive or self._forklift is None:
            return False

        dx, dy = self._robot.direction.delta()
        x, y = self._robot.x, self._robot.y

        while True:
            x += dx
            y += dy
            if x < 1 or x > self.width or y < 1 or y > self.height:
                break
            if (x, y) == self._forklift:
                self._forklift_alive = False
                return True

        return False

    def _get_percept(self, bump: bool, beep: bool) -> Percept:
        pos = (self._robot.x, self._robot.y)
        adjacent = self._get_adjacent(pos)

        creaking = any(adj in self._damaged for adj in adjacent)
        rumbling = self._forklift_alive and self._forklift in adjacent
        beacon = pos == self._package and not self._robot.has_package

        return Percept(
            creaking=creaking,
            rumbling=rumbling,
            beacon=beacon,
            bump=bump,
            beep=beep,
        )

    def _get_adjacent(self, pos: tuple[int, int]) -> list[tuple[int, int]]:
        x, y = pos
        candidates = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
        return [
            (ax, ay)
            for ax, ay in candidates
            if 1 <= ax <= self.width and 1 <= ay <= self.height
        ]

    def _record_state(self, action: Action | None = None) -> None:
        self._history.append(
            {
                "step": self._steps,
                "action": action.name if action else None,
                "robot_x": self._robot.x,
                "robot_y": self._robot.y,
                "direction": self._robot.direction.name,
                "has_package": self._robot.has_package,
                "has_shutdown": self._robot.has_shutdown_device,
                "alive": self._robot.alive,
                "forklift_alive": self._forklift_alive,
                "percept": self._last_percept._asdict(),
                "total_reward": self._total_reward,
            }
        )

    @property
    def robot_position(self) -> tuple[int, int]:
        return (self._robot.x, self._robot.y)

    @property
    def robot_direction(self) -> Direction:
        return self._robot.direction

    @property
    def has_package(self) -> bool:
        return self._robot.has_package

    @property
    def has_shutdown_device(self) -> bool:
        return self._robot.has_shutdown_device

    @property
    def is_alive(self) -> bool:
        return self._robot.alive

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def total_reward(self) -> float:
        return self._total_reward

    @property
    def history(self) -> list[dict]:
        return self._history.copy()

    def get_true_state(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "damaged": list(self._damaged),
            "forklift": self._forklift,
            "forklift_alive": self._forklift_alive,
            "package": self._package,
            "robot": {
                "x": self._robot.x,
                "y": self._robot.y,
                "direction": self._robot.direction.name,
                "has_package": self._robot.has_package,
                "has_shutdown": self._robot.has_shutdown_device,
                "alive": self._robot.alive,
            },
            "terminated": self._terminated,
            "success": self._success,
        }

    def render(self, reveal: bool = False) -> str:
        lines = []
        lines.append("  " + " ".join(str(x) for x in range(1, self.width + 1)))

        for y in range(self.height, 0, -1):
            row = [str(y)]
            for x in range(1, self.width + 1):
                pos = (x, y)
                if pos == (self._robot.x, self._robot.y):
                    if not self._robot.alive:
                        row.append("X")
                    elif self._robot.has_package:
                        row.append("@")
                    else:
                        arrows = {
                            Direction.NORTH: "^",
                            Direction.EAST: ">",
                            Direction.SOUTH: "v",
                            Direction.WEST: "<",
                        }
                        row.append(arrows[self._robot.direction])
                elif reveal:
                    if pos in self._damaged:
                        row.append("D")
                    elif pos == self._forklift:
                        row.append("F" if self._forklift_alive else "f")
                    elif pos == self._package and not self._robot.has_package:
                        row.append("P")
                    else:
                        row.append(".")
                else:
                    row.append("?")
            lines.append(" ".join(row))

        return "\n".join(lines)


if __name__ == "__main__":
    env = HazardousWarehouseEnv(seed=42)

    print("=== Hazardous Warehouse Environment ===")
    print("\nTrue state (hidden from agent):")
    print(env.render(reveal=True))

    print("\nAgent's view:")
    print(env.render(reveal=False))

    print(f"\nInitial percept: {env._last_percept}")
    print(f"Robot at: {env.robot_position}, facing {env.robot_direction.name}")

    actions = [Action.FORWARD, Action.TURN_LEFT, Action.FORWARD]
    for action in actions:
        percept, reward, done, info = env.step(action)
        print(f"\nAction: {action.name}")
        print(f"Percept: {percept}")
        print(f"Reward: {reward}, Done: {done}")
        print(f"Position: {env.robot_position}, Facing: {env.robot_direction.name}")

    print("\n=== Final State ===")
    print(env.render(reveal=True))
