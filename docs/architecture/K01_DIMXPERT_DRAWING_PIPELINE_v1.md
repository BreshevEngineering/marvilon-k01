# K01 DimXpert-driven drawing pipeline

## Authority chain

```text
requirement / functional characteristic
        ↓
controlled Product Characteristic ID
        ↓
native CAD semantic feature
        ↓
native SOLIDWORKS DimXpert / PMI
        ↓
tolerance / stack-up analysis
        ↓
derived SLDDRW / PDF drawing
        ↓
drawing semantic lint + visual QA
        ↓
inspection characteristic / method
        ↓
inspection result / traceability
```

The drawing must not become an independent tolerance database.

## Rules

1. Native SOLIDWORKS geometry owns nominal shape.
2. Controlled Product Characteristics define the functional release intent.
3. Native DimXpert/PMI is the preferred machine-readable carrier for tolerance, datum and GD&T authority.
4. A drawing may project only accepted product-definition states. It must not invent a tolerance to fill a blank.
5. `AutoDimension` is prohibited for release drawings.
6. Tolerance chains are solved before release tolerances are frozen.
7. Every release-critical characteristic has an ID, semantic source/binding, tolerance/GD&T, view/section and inspection method.
8. DimXpert extraction/binding must be machine-verifiable before drawing release.
9. Drawing PASS requires semantic lint + human visual QA + native SLDDRW/PDF pair.
10. Drawing release must be traceable to inspection characteristics.

## P007 / K01-D-006 exemplar

P007 is the first professional drawing exemplar, not the current active line.

Current known state:
- candidate drawing exists;
- P007 live-geometry/product-characteristic workpack exists;
- C01-C08 and C11 require native PMI/DimXpert authoring/review;
- C10 containment process is OPEN;
- C12 leak/containment acceptance requirement is OPEN;
- C02 has a live-CAD vs legacy-draft conflict that must be resolved in favor of controlled product definition, not by changing CAD merely to match an old drawing.

P007 drawing work resumes only after the current P0 Baseline-02C promotion and applicable P1-P3 requirements/tolerances/process inputs are controlled.
