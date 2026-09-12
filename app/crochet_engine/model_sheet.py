"""Deterministic visual model-sheet renderer for the Amigurumi Design Model.

The model sheet is a human-readable visualization of the semantic decomposition.
It is deliberately deterministic: labels/counts come from structured data, while
simple silhouettes are chosen from the part role. It is not a ground-truth
3D reconstruction and never replaces the Design Model.
"""
from __future__ import annotations

import html
import math
from typing import Any, Dict, List


def _esc(v: Any) -> str:
    return html.escape(str(v if v is not None else ""))


def _role_shape(role: str, cx: float, cy: float, w: float, h: float) -> str:
    role = (role or "other").lower()
    x, y = cx - w / 2, cy - h / 2
    stroke = "#302b3a"
    fill = "#efeafe"
    if role in {"body", "torso"}:
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role == "head":
        return f'<path d="M {cx:.1f} {y+h*.18:.1f} C {x:.1f} {y+h*.18:.1f}, {x:.1f} {y+h*.85:.1f}, {cx:.1f} {y+h:.1f} C {x+w:.1f} {y+h*.85:.1f}, {x+w:.1f} {y+h*.18:.1f}, {cx:.1f} {y+h*.18:.1f} Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role in {"arm", "leg", "neck", "tail"}:
        return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{min(w,h)/2:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2" transform="rotate(-8 {cx:.1f} {cy:.1f})"/>'
    if role in {"ear", "horn"}:
        return f'<path d="M {cx:.1f} {y:.1f} L {x+w:.1f} {y+h:.1f} L {x:.1f} {y+h:.1f} Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role in {"eye", "nose", "detail"}:
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role == "muzzle":
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role == "wing":
        return f'<path d="M {x:.1f} {cy:.1f} Q {cx:.1f} {y:.1f} {x+w:.1f} {cy:.1f} Q {cx:.1f} {y+h:.1f} {x:.1f} {cy:.1f} Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    if role == "plate":
        return f'<path d="M {cx:.1f} {y:.1f} L {x+w:.1f} {y+h:.1f} L {x:.1f} {y+h:.1f} Z" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'


def render_model_sheet(design: Dict[str, Any]) -> str:
    """Return an SVG data URL for a deterministic technical model sheet."""
    subject = str(design.get("subject") or "Soggetto amigurumi")
    parts = list(design.get("parts") or [])
    if not parts:
        parts = [{"id": "body", "label": "Corpo", "role": "body", "count": 1, "parent_id": None, "symmetry_group": None}]

    # Keep the sheet readable even for unusually detailed subjects.
    cols = 4
    card_w, card_h = 220, 170
    rows = max(1, math.ceil(len(parts) / cols))
    width = 920
    height = 150 + rows * card_h + 70

    svg: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<rect x="0" y="0" width="100%" height="118" fill="#f7f4ff"/>',
        f'<text x="42" y="45" font-family="Arial,sans-serif" font-size="28" font-weight="700" fill="#171322">MODEL SHEET</text>',
        f'<text x="42" y="78" font-family="Arial,sans-serif" font-size="20" font-weight="600" fill="#5a4abf">{_esc(subject)}</text>',
        '<text x="42" y="101" font-family="Arial,sans-serif" font-size="13" fill="#6d6878">Scomposizione costruttiva — visualizzazione tecnica, non pattern</text>',
        f'<text x="850" y="50" text-anchor="end" font-family="Arial,sans-serif" font-size="13" fill="#6d6878">{len(parts)} tipi di pezzo</text>',
        f'<text x="850" y="72" text-anchor="end" font-family="Arial,sans-serif" font-size="13" fill="#6d6878">{sum(max(1,int(p.get("count",1) or 1)) for p in parts)} pezzi totali</text>',
    ]

    for i, p in enumerate(parts):
        col, row = i % cols, i // cols
        ox, oy = 30 + col * 225, 135 + row * card_h
        role = str(p.get("role") or "other")
        label = str(p.get("label") or p.get("id") or role)
        count = max(1, int(p.get("count", 1) or 1))
        sym = p.get("symmetry_group")
        parent = p.get("parent_id")
        svg += [
            f'<rect x="{ox}" y="{oy}" width="210" height="145" rx="16" fill="#fbfafc" stroke="#ded9e9"/>',
            f'<text x="{ox+14}" y="{oy+23}" font-family="Arial,sans-serif" font-size="14" font-weight="700" fill="#211c2b">{_esc(label)}</text>',
            f'<text x="{ox+196}" y="{oy+23}" text-anchor="end" font-family="Arial,sans-serif" font-size="12" fill="#665a92">×{count}</text>',
        ]
        # Use estimated dimensions only as a relative visual cue.
        ew = float(p.get("estimated_width_cm") or 0)
        eh = float(p.get("estimated_height_cm") or 0)
        scale = max(1.0, min(1.6, 65 / max(ew, eh, 1)))
        sw = max(28, min(92, (ew or 3.5) * scale * 1.6))
        sh = max(22, min(72, (eh or 3.5) * scale * 1.6))
        svg.append(_role_shape(role, ox + 105, oy + 75, sw, sh))
        meta = role
        if sym:
            meta += f"  •  {sym}"
        if parent:
            meta += f"  •  parent: {parent}"
        svg.append(f'<text x="{ox+14}" y="{oy+126}" font-family="Arial,sans-serif" font-size="11" fill="#777181">{_esc(meta)}</text>')
    svg += [
        f'<line x1="30" y1="{height-48}" x2="890" y2="{height-48}" stroke="#e5e1ea"/>',
        f'<text x="30" y="{height-23}" font-family="Arial,sans-serif" font-size="11" fill="#777181">Fonte: Amigurumi Design Model • Le quantità e le etichette provengono dalla scomposizione strutturata.</text>',
        '</svg>'
    ]
    import base64
    payload = base64.b64encode("".join(svg).encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{payload}"
