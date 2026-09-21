
from __future__ import annotations
from .dxf_stdlib import write_semantic_schedule_dxf

def build_semantic_preview(contract, manifest, output_path):
    # Compatibility name retained, but this artifact is explicitly a prebuild semantic schedule,
    # not a geometric drawing preview.
    return write_semantic_schedule_dxf(contract, manifest, output_path)
