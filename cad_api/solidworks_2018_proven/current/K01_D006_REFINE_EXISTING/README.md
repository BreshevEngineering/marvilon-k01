# K01-D-006 existing-drawing refinement

Purpose: do not recreate the drawing manually. Reuse the current linked SLDDRW as the seed.

The tool:
- reads the current D006 drawing path and current proven P007 PMI candidate from reports;
- makes a timestamped copy only;
- keeps the original drawing and part byte-invariant;
- repositions/rescales existing views using SW2018 `IView.Position` / `ScaleDecimal`;
- attempts `InsertModelAnnotations3` in the existing views;
- filters the inserted annotations so only annotations that report a DimXpert feature/name are retained;
- removes newly inserted non-DimXpert and duplicate annotations;
- exports PDF/BMP for visual QA.

This is an acceleration path, not a new drawing generator.
Manual work after this step is limited to final presentation moves that are hard to automate safely.
