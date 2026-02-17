# Assignment 3 - Knowledge-Based Agent (Z3)

This project implements the Z3-based knowledge-based agent for the Hazardous Warehouse.

## Files

- [src/hazardous_warehouse_env.py](src/hazardous_warehouse_env.py): Environment with hazards, percepts, actions, and shutdown device.
- [src/hazardous_warehouse_viz.py](src/hazardous_warehouse_viz.py): Example layout used for the manual walkthrough.
- [src/warehouse_kb_agent.py](src/warehouse_kb_agent.py): Z3 KB agent (TELL/ASK, BFS planning, action loop, shutdown bonus).
- [src/manual_reasoning.py](src/manual_reasoning.py): Step-by-step Z3 reasoning walkthrough (Section 3.2/3.6).

## How to Run

```bash
uv run python src/manual_reasoning.py
uv run python src/warehouse_kb_agent.py
```

## Task 3 - Manual Reasoning Results

Manual walkthrough reproduces the textbook inference:

- Step 1 (1,1): safe(2,1) = True, safe(1,2) = True
- Step 2 (2,1): safe(3,1) = False (unknown), safe(2,2) = False (unknown)
- Step 3 (1,2): safe(2,2) = True, not safe(3,1) = True, not safe(1,3) = True

## Task 5 - Agent Run (Example Layout)

Run command:

```bash
uv run python src/warehouse_kb_agent.py
```

Result:

- Steps taken: 24
- Total reward: 968
- Success: True (package retrieved and exit)

## Task 6 - Reflection

The agent can get stuck when all remaining unknown squares cannot be proven safe, even if a human might take a reasonable risk to proceed. It also behaves conservatively when the KB cannot entail safety, which can cause it to exit without the package in some layouts. Adding probabilistic reasoning or expected-utility decision making would help it choose actions under uncertainty.

## Bonus - Shutdown Device

The agent uses shutdown if the forklift location is entailed and lies on the current line of sight, matching the one-shot device rules.
