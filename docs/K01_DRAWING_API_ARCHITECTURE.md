# K01 drawing automation — required architecture

Drawings shall be generated from the native SolidWorks design, not manually
redrawn as independent geometry.

## Authority

`K01_master.json`
→ controlled functional dimensions / fits / requirements

Native SLDPRT/SLDASM
→ exact geometry, local manufacturing features, material

Drawing generator
→ views, sections, dimensions, datum symbols, fit callouts, process notes,
   BOM table, revision block

No independent hand-maintained drawing geometry is allowed.

## API pipeline

1. Read default drawing template from SolidWorks user preferences.
2. Create/update `K01-D-xxx_<Part>.SLDDRW`.
3. Insert model views from stable SLDPRT/SLDASM.
4. Create section/detail views from named model reference geometry.
5. Import model dimensions where they are controlled and trustworthy.
6. Add API-controlled dimensions/notes for master-owned fits and process data.
7. Add datum A/B/C symbols to named reference geometry.
8. For K01-D-012 assembly drawing, insert a SolidWorks BOM table generated from
   the assembly, then QA it against the API BOM projection.
9. Export PDF + DXF only as release derivatives.
10. Write a JSON drawing manifest with source SHA/path/revision.

## Order

Do not generate final P003/P007 drawings until:
- Datum C passes;
- serviceable P003↔P007 interface passes assembly QA.

After those two geometry gates, drawing generation is the next API workstream.
