# K01 P006 and fastener review

## P006 retaining plug

Current controlled geometry:
- AISI 316L / EN 1.4404;
- L8;
- M12×1;
- front relief Ø9.10 × 0.06 controlling P002 axial float;
- thread-region BREP cylinder ≈Ø10.8 over 6 mm;
- rear head OD11.5 × 2 mm;
- through bore Ø6.

### Is M12×1 too large?

No. It is not selected by axial load; it is selected by packaging around the
Ø9.10 relief/bushing envelope.

Using the measured thread-root envelope:
- M12×1 root envelope ≈Ø10.8;
- radial metal between Ø10.8 root and Ø9.10 relief ≈0.85 mm.

M10×1 is geometrically incompatible with a Ø9.10 relief.
M11×1 is a non-preferred size and would leave only a very small root wall.
Therefore M12×1 is the smallest sensible standard fine-thread size for the
current P002 retention geometry.

### Is 6 mm engagement excessive?

6 mm = 0.5D. The actual functional load is tiny compared with thread capacity.
It could be shortened structurally, but doing so gives almost no useful package
benefit and reduces robustness for repeated assembly. Keep 6 mm.

### Missing service feature

The current P006 is essentially axisymmetric and lacks a good reproducible drive
feature. Add a service-tool feature at final drawing/CAD pass:
- preferred candidate: 2× Ø1.5 blind pin-spanner holes, 180°, PCD8.5,
  depth ≈1.2, on the rear head face.

This preserves the present axial envelope and avoids wrenching the thread/body
with pliers.

## P003 ↔ P016 fasteners

Current P016 native CAD has:
- 3× M4-6H at PCD24 / 120°;
- full thread depth ≈8 mm;
- P003 clearance holes Ø4.5 through a 3 mm flange.

Three screws are appropriate because the Ø10 pilot and Datum A/C locate the
joint; screws clamp the O-ring face only.

Recommended purchased screw baseline:
- 3× M4×10 A4-70;
- no permanent threadlocker;
- approved anti-galling practice for stainless threads.

With the 3 mm P003 flange, M4×10 gives ~7 mm nominal engagement before local
chamfer/tolerance effects, matching the earlier minimum-full-thread design.
Do not use M4×12 without checking bottom clearance.

Final tightening torque remains tied to screw finish/lubrication and O-ring
compression; do not freeze a generic torque value yet.
