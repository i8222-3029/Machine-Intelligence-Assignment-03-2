"""
Manual reasoning walkthrough for the Hazardous Warehouse KB.

Reproduces the step-by-step inference from Section 3.2 / 3.6 using Z3.
"""

from z3 import Not

from hazardous_warehouse_env import Percept
from warehouse_kb_agent import (
    build_warehouse_kb,
    z3_entails,
    safe,
    creaking_at,
    rumbling_at,
)


def tell_percepts(solver, percept: Percept, x: int, y: int) -> None:
    """TELL the solver the percepts observed at (x, y)."""
    if percept.creaking:
        solver.add(creaking_at(x, y))
    else:
        solver.add(Not(creaking_at(x, y)))
    if percept.rumbling:
        solver.add(rumbling_at(x, y))
    else:
        solver.add(Not(rumbling_at(x, y)))


if __name__ == "__main__":
    solver = build_warehouse_kb()

    print("Step 1: At (1,1), no creaking, no rumbling")
    tell_percepts(
        solver,
        Percept(creaking=False, rumbling=False, beacon=False, bump=False, beep=False),
        1,
        1,
    )
    print("safe(2,1):", z3_entails(solver, safe(2, 1)))
    print("safe(1,2):", z3_entails(solver, safe(1, 2)))

    print("\nStep 2: At (2,1), creaking, no rumbling")
    tell_percepts(
        solver,
        Percept(creaking=True, rumbling=False, beacon=False, bump=False, beep=False),
        2,
        1,
    )
    print("safe(3,1):", z3_entails(solver, safe(3, 1)))
    print("not safe(3,1):", z3_entails(solver, Not(safe(3, 1))))
    print("safe(2,2):", z3_entails(solver, safe(2, 2)))

    print("\nStep 3: At (1,2), no creaking, rumbling")
    tell_percepts(
        solver,
        Percept(creaking=False, rumbling=True, beacon=False, bump=False, beep=False),
        1,
        2,
    )
    print("safe(2,2):", z3_entails(solver, safe(2, 2)))
    print("not safe(3,1):", z3_entails(solver, Not(safe(3, 1))))
    print("not safe(1,3):", z3_entails(solver, Not(safe(1, 3))))

    print("\nStep 4: Re-ask after more evidence")
    print("safe(3,1):", z3_entails(solver, safe(3, 1)))
    print("not safe(3,1):", z3_entails(solver, Not(safe(3, 1))))
    print("safe(1,3):", z3_entails(solver, safe(1, 3)))
    print("not safe(1,3):", z3_entails(solver, Not(safe(1, 3))))
