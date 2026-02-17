"""
Visualization helpers for the Hazardous Warehouse.

This module provides a deterministic example layout from the textbook.
"""

from __future__ import annotations

from hazardous_warehouse_env import HazardousWarehouseEnv, Direction


def configure_rn_example_layout(env: HazardousWarehouseEnv) -> None:
    """
    Configure the example layout used in the manual reasoning walkthrough.

    Layout (4x4):
    - Damaged floor: (3, 1), (3, 3)
    - Forklift: (1, 3)
    - Package: (2, 3)
    """
    env.width = 4
    env.height = 4

    env._damaged = {(3, 1), (3, 3)}
    env._forklift = (1, 3)
    env._forklift_alive = True
    env._package = (2, 3)

    env._robot.x = 1
    env._robot.y = 1
    env._robot.direction = Direction.EAST
    env._robot.has_package = False
    env._robot.has_shutdown_device = True
    env._robot.alive = True

    env._steps = 0
    env._total_reward = 0.0
    env._terminated = False
    env._success = False
    env._history = []

    env._last_percept = env._get_percept(bump=False, beep=False)
    env._record_state()


if __name__ == "__main__":
    env = HazardousWarehouseEnv(seed=0)
    configure_rn_example_layout(env)

    print("Example layout (reveal=True):")
    print(env.render(reveal=True))
