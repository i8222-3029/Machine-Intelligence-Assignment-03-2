"""
Knowledge-Based Agent for the Hazardous Warehouse (Propositional Z3).
"""

from __future__ import annotations

from collections import deque

from z3 import Bool, Or, And, Not, Solver, unsat

from hazardous_warehouse_env import HazardousWarehouseEnv, Action, Direction, Percept


def z3_entails(solver: Solver, query) -> bool:
    """Return True if solver's KB entails query (refutation with push/pop)."""
    solver.push()
    solver.add(Not(query))
    result = solver.check() == unsat
    solver.pop()
    return result


def damaged(x: int, y: int):
    return Bool(f"D_{x}_{y}")


def forklift_at(x: int, y: int):
    return Bool(f"F_{x}_{y}")


def creaking_at(x: int, y: int):
    return Bool(f"C_{x}_{y}")


def rumbling_at(x: int, y: int):
    return Bool(f"R_{x}_{y}")


def safe(x: int, y: int):
    return Bool(f"OK_{x}_{y}")


def get_adjacent(x: int, y: int, width: int = 4, height: int = 4) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if 1 <= nx <= width and 1 <= ny <= height:
            result.append((nx, ny))
    return result


def build_warehouse_kb(width: int = 4, height: int = 4) -> Solver:
    solver = Solver()

    solver.add(Not(damaged(1, 1)))
    solver.add(Not(forklift_at(1, 1)))

    for x in range(1, width + 1):
        for y in range(1, height + 1):
            adj = get_adjacent(x, y, width, height)

            solver.add(creaking_at(x, y) == Or([damaged(a, b) for a, b in adj]))
            solver.add(rumbling_at(x, y) == Or([forklift_at(a, b) for a, b in adj]))
            solver.add(safe(x, y) == And(Not(damaged(x, y)), Not(forklift_at(x, y))))

    return solver


_DIRECTION_ORDER = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]


def _direction_index(d: Direction) -> int:
    return _DIRECTION_ORDER.index(d)


def turns_between(current: Direction, target: Direction) -> list[Action]:
    if current == target:
        return []
    ci = _direction_index(current)
    ti = _direction_index(target)
    right_steps = (ti - ci) % 4
    left_steps = (ci - ti) % 4
    if right_steps <= left_steps:
        return [Action.TURN_RIGHT] * right_steps
    return [Action.TURN_LEFT] * left_steps


def delta_to_direction(dx: int, dy: int) -> Direction:
    return {
        (0, 1): Direction.NORTH,
        (0, -1): Direction.SOUTH,
        (1, 0): Direction.EAST,
        (-1, 0): Direction.WEST,
    }[(dx, dy)]


class WarehouseKBAgent:
    def __init__(self, env: HazardousWarehouseEnv) -> None:
        self.env = env
        self.solver = build_warehouse_kb(env.width, env.height)
        self.x = 1
        self.y = 1
        self.direction = Direction.EAST
        self.has_package = False
        self.visited: set[tuple[int, int]] = {(1, 1)}
        self.known_safe: set[tuple[int, int]] = {(1, 1)}
        self.known_dangerous: set[tuple[int, int]] = set()
        self.action_queue: list[Action] = []
        self.step_count = 0
        self.forklift_disabled = False

    def tell_percepts(self, percept: Percept) -> None:
        x, y = self.x, self.y
        if percept.creaking:
            self.solver.add(creaking_at(x, y))
        else:
            self.solver.add(Not(creaking_at(x, y)))
        if percept.rumbling:
            self.solver.add(rumbling_at(x, y))
        else:
            self.solver.add(Not(rumbling_at(x, y)))
        if percept.beep:
            self.forklift_disabled = True

    def update_safety(self) -> None:
        for x in range(1, self.env.width + 1):
            for y in range(1, self.env.height + 1):
                pos = (x, y)
                if pos in self.known_safe or pos in self.known_dangerous:
                    continue
                if z3_entails(self.solver, safe(x, y)):
                    self.known_safe.add(pos)
                elif z3_entails(self.solver, Not(safe(x, y))):
                    self.known_dangerous.add(pos)

    def _entailed_forklift_positions(self) -> set[tuple[int, int]]:
        positions: set[tuple[int, int]] = set()
        for x in range(1, self.env.width + 1):
            for y in range(1, self.env.height + 1):
                if z3_entails(self.solver, forklift_at(x, y)):
                    positions.add((x, y))
        return positions

    def _forklift_in_line_of_sight(self) -> bool:
        if self.forklift_disabled or not self.env.has_shutdown_device:
            return False

        dx, dy = self.direction.delta()
        x, y = self.x, self.y
        entailed = self._entailed_forklift_positions()
        if not entailed:
            return False

        while True:
            x += dx
            y += dy
            if x < 1 or x > self.env.width or y < 1 or y > self.env.height:
                return False
            if (x, y) in entailed:
                return True

    def plan_path(self, start: tuple[int, int], goal_set: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
        queue = deque([(start, [start])])
        seen = {start}
        while queue:
            (cx, cy), path = queue.popleft()
            if (cx, cy) in goal_set:
                return path
            for nx, ny in get_adjacent(cx, cy, self.env.width, self.env.height):
                if (nx, ny) not in seen and (nx, ny) in self.known_safe:
                    seen.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
        return None

    def path_to_actions(self, path: list[tuple[int, int]]) -> tuple[list[Action], Direction]:
        actions: list[Action] = []
        direction = self.direction
        for i in range(1, len(path)):
            dx = path[i][0] - path[i - 1][0]
            dy = path[i][1] - path[i - 1][1]
            target_dir = delta_to_direction(dx, dy)
            actions.extend(turns_between(direction, target_dir))
            actions.append(Action.FORWARD)
            direction = target_dir
        return actions, direction

    def choose_action(self, percept: Percept) -> Action:
        if self.action_queue:
            return self.action_queue.pop(0)

        if self._forklift_in_line_of_sight():
            return Action.SHUTDOWN

        if percept.beacon and not self.has_package:
            return Action.GRAB

        if self.has_package:
            if (self.x, self.y) == (1, 1):
                return Action.EXIT
            path = self.plan_path((self.x, self.y), {(1, 1)})
            if path and len(path) > 1:
                actions, _ = self.path_to_actions(path)
                self.action_queue = actions[1:]
                return actions[0]
            return Action.EXIT

        safe_unvisited = self.known_safe - self.visited
        if safe_unvisited:
            path = self.plan_path((self.x, self.y), safe_unvisited)
            if path and len(path) > 1:
                actions, _ = self.path_to_actions(path)
                self.action_queue = actions[1:]
                return actions[0]

        if (self.x, self.y) == (1, 1):
            return Action.EXIT
        path = self.plan_path((self.x, self.y), {(1, 1)})
        if path and len(path) > 1:
            actions, _ = self.path_to_actions(path)
            self.action_queue = actions[1:]
            self.action_queue.append(Action.EXIT)
            return actions[0]
        return Action.EXIT

    def execute_action(self, action: Action) -> tuple[Percept, float, bool, dict]:
        percept, reward, done, info = self.env.step(action)

        if action == Action.FORWARD and not percept.bump:
            dx, dy = self.direction.delta()
            self.x += dx
            self.y += dy
            self.visited.add((self.x, self.y))
        elif action == Action.TURN_LEFT:
            self.direction = self.direction.turn_left()
        elif action == Action.TURN_RIGHT:
            self.direction = self.direction.turn_right()
        elif action == Action.GRAB and info.get("grabbed"):
            self.has_package = True

        self.step_count += 1
        return percept, reward, done, info

    def run(self, verbose: bool = True) -> None:
        percept = self.env._last_percept
        self.tell_percepts(percept)
        self.update_safety()

        if verbose:
            print(f"Start at ({self.x},{self.y}) facing {self.direction.name}")
            print(f"  Percept: {percept}")
            print(f"  Known safe: {sorted(self.known_safe)}")

        while True:
            action = self.choose_action(percept)
            percept, reward, done, info = self.execute_action(action)

            if verbose:
                print(f"\nStep {self.step_count}: {action.name}")
                print(f"  Position: ({self.x},{self.y}), Facing: {self.direction.name}")
                print(f"  Percept: {percept}")
                print(f"  Info: {info}")

            if done:
                if verbose:
                    print("\n" + "=" * 40)
                    print(f"Episode ended. Reward: {self.env.total_reward:.0f}")
                    print(f"Steps taken: {self.step_count}")
                    success = info.get("exit") == "success"
                    print(f"Success: {success}")
                return

            if action == Action.FORWARD and not percept.bump:
                self.tell_percepts(percept)
                self.update_safety()
                if verbose:
                    print(f"  Known safe: {sorted(self.known_safe)}")
                    print(f"  Known dangerous: {sorted(self.known_dangerous)}")


if __name__ == "__main__":
    from hazardous_warehouse_viz import configure_rn_example_layout

    env = HazardousWarehouseEnv(seed=0)
    configure_rn_example_layout(env)

    print("True state (hidden from the agent):")
    print(env.render(reveal=True))
    print()

    agent = WarehouseKBAgent(env)
    agent.run(verbose=True)
