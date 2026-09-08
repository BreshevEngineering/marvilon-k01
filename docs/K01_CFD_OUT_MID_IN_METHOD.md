# K01 CFD OUT / MID / IN — final design-freeze method

## Decision
Do **not** attach the whole external calibration module to the Flow Simulation fluid model.

The controlled K01 architecture keeps all K01 hardware outside the Long Run gas
volume except the Ø5 working rod. Therefore the only geometry that must change
between OUT/MID/IN for the axial gas-load envelope is the **gas-wetted rod
intrusion**.

Use the existing Long Run / optical-cell CFD model and a dedicated CFD rod
reference/configuration.

## Three positions
Relative to the Long Run inner wall:
- OUT = 0.00 mm protrusion; target tip flush with the inner Ø20 wall.
- MID = 5.00 mm protrusion.
- IN  = 10.00 mm protrusion; target tip reaches channel axis.

Preferred implementation: translate the CFD rod body/configuration by 0/5/10 mm.
A simplified shortened rod is acceptable only if the internal gas-wetted
geometry is exactly equivalent and the external/non-wetted part is not in the
fluid domain.

Do not edit the production P001 part just to create CFD states.

## Must remain identical between cases
- all inlet/outlet/pressure BC;
- gas properties;
- temperatures for this design-freeze set;
- mesh policy and local refinements;
- lid/closure definitions;
- Goal definition.

Release goal:
`SG Force(X)2` on gas-wetted rod surfaces only.

Envelope:
`F_CFD,max = max(|Fx_OUT|, |Fx_MID|, |Fx_IN|)`.

Current design-freeze actuator criterion uses allowable CFD max = 0.345 N.
If the three-position envelope is comfortably below it, no hot sweep is needed
for design freeze; hot verification remains production validation.
