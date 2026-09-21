# Datum C kinematic decision

> **Implementation update — EDR-023 (2026-09-09):** the A/B/C kinematic reasoning below remains valid, but the
> earlier **round pin + radial slot** implementation is superseded by the later Gate04B/serviceable-joint baseline:
> **relieved/diamond P017 + round P003 mating hole**. This later implementation preserves radial relief in the pin
> instead of the mating slot and has current Gate04B v7 native PASS evidence. See
> `control/decisions/EDR-023_DATUM_C_KINEMATIC_BASELINE.json`.

The first draft used a peripheral round pin in a round mating hole. That is not
the preferred production locator because the central Ø10 pilot Datum B already
fixes transverse position. A second fully round locator would redundantly constrain
the pitch radius and can cause assembly binding from independent machining
tolerances.

The governing kinematic hierarchy remains:

- A: mating face;
- B: Ø10 H7/g6 central pilot;
- C: one peripheral locator that constrains only tangential clocking while allowing radial relief.

Current EDR-023 implementation:

- P016: Ø3 H7 press-pin hole at the pattern-derived free-gap midpoint;
- P017: relieved/diamond locator; tangential major width controls clocking and radial minor provides relief;
- P003: simple Ø3.02 +0.01/0 round mating hole.

Earlier radial-slot geometry is retained as superseded design history, not as the current build baseline.
