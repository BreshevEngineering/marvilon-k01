# K01 P007 D3 Repair V18

Scope: repair only the three blockers proven by D3 V17 on the SAME V12 exemplar:

- C01 Datum A native symbol attachment -> one member of the controlled composite coplanar datum feature;
- C01 annotation view -> controlled `AV_J2_LONGITUDINAL` mapping (`*Front`);
- C02 annotation view -> controlled `AV_J2_LONGITUDINAL` mapping (`*Front`).

The repair does not regenerate the drawing, alter canonical P007, add dimensions, close L3, or authorize D7 by itself.

Run preflight first. Apply creates a timestamped backup of the workspace part and then automatically re-runs D3 V17.

## V18A SW2018 interop correction

The local SW2018/API 26 proven rule is mandatory:

`Face2 -> Entity -> IEntity.Select4`

Direct `Face2.Select4` does not exist in the installed C# interop. V18A also verifies the selection manager reports exactly one selected `swSelFACES` entity before inserting Datum A.
