"""Deterministic compiler from Amigurumi Design Model to Shape Graph.

The AI decides semantic identity/parts; this module turns the structured design
into a conservative, compilable crochet plan without asking the model to invent
geometry a second time.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import math
from .engine import ProfilePoint, egg_profile, sphere_profile, tapered_profile, Gauge, compile_project
from .shape_graph import ShapeGraph, ShapeNode, ShapeEdge, Vec3, Euler, ConnectionPoint

ROLE_TECHNIQUE = {
    "body": "spirale_sc",
    "head": "spirale_sc",
    "neck": "tubo_sc",
    "muzzle": "spirale_sc",
    "tail": "tubo_sc",
    "leg": "tubo_sc",
    "arm": "tubo_sc",
    "ear": "disco_sc",
    "horn": "cono_sc",
    "wing": "lamina_sc",
    "eye": "ricamo/applicazione",
    "plate": "applicazione",
    "detail": "dettaglio/applicazione",
    "other": "spirale_sc",
}


def select_technique(part: Dict[str, Any]) -> str:
    role = str(part.get("role", "other")).lower()
    construction = str(part.get("construction", "")).lower()
    if "ricam" in construction or "embroid" in construction:
        return "ricamo"
    if "disco" in construction or role == "ear":
        return "disco_sc"
    if "cono" in construction or role == "horn":
        return "cono_sc"
    if "tubo" in construction or role in {"leg", "arm", "neck", "tail"}:
        return "tubo_sc"
    return ROLE_TECHNIQUE.get(role, "spirale_sc")


def _dims(part: Dict[str, Any], target_h: float, body_h: float) -> tuple[float, float, float]:
    h = part.get("estimated_height_cm")
    w = part.get("estimated_width_cm")
    d = part.get("estimated_depth_cm")
    h = float(h) if isinstance(h, (int, float)) and h > 0 else max(1.2, body_h * (0.35 if part.get("role") in {"head"} else 0.22))
    w = float(w) if isinstance(w, (int, float)) and w > 0 else max(0.9, h * 0.65)
    d = float(d) if isinstance(d, (int, float)) and d > 0 else max(0.7, w * 0.75)
    # Normalize the whole design to the requested target height.  The previous
    # expression only scaled down designs larger than target_h, leaving smaller
    # designs undersized and causing systematic target-height errors.
    scale = target_h / max(body_h, 1.0)
    return h * scale, w * scale, d * scale


def _anisotropic(points: list[ProfilePoint], width: float, depth: float) -> list[ProfilePoint]:
    """Attach width/depth to a radial profile and convert ellipse circumference
    to an equivalent diameter so the existing stitch compiler remains valid.
    This is a deterministic bridge toward true anisotropic geometry.
    """
    width = max(float(width), 0.4)
    depth = max(float(depth), 0.4)
    out = []
    for p in points:
        t = p.z_cm / max(points[-1].z_cm, 1e-6)
        # Preserve the profile's longitudinal taper while respecting independent
        # frontal width and side depth.
        factor = p.diameter_cm / max(points[0].diameter_cm, 1e-6)
        a = max(0.2, width * factor) / 2.0
        b = max(0.2, depth * factor) / 2.0
        # Ramanujan II ellipse circumference. Equivalent diameter keeps the
        # downstream stitch-count mathematics compatible with the radial engine.
        h = ((a-b)**2) / max((a+b)**2, 1e-9)
        circumference = math.pi * (a+b) * (1 + (3*h)/(10 + math.sqrt(max(0.0, 4-3*h))))
        eq_d = circumference / math.pi
        out.append(ProfilePoint(p.z_cm, eq_d, width_cm=2*a, depth_cm=2*b))
    return out


def _profile(role: str, h: float, w: float, d: float = 1.0, construction: str = "", label: str = "", notes: str = "") -> tuple[list[ProfilePoint], str, int]:
    """Build a role + shape-cue driven radial profile.

    The Design Model may describe distinctive geometry in construction/notes/label.
    We translate those cues deterministically instead of forcing every part into
    the same generic egg.  The radial engine still cannot represent arbitrary
    asymmetric 3-D meshes, so this is deliberately conservative.
    """
    text = " ".join(str(x or "") for x in (role, construction, label, notes)).lower()
    width = max(float(w), 0.8)
    depth = max(float(d), width * 0.55)
    # Radial diameter is a conservative equivalent of the visible width/depth.
    diameter = max(0.8, min(width, max(depth, width * 0.65)))

    if role in {"eye", "plate", "detail"} or "disco" in text or "piatto" in text or "flat" in text:
        hh = max(h, diameter * 0.22)
        return _anisotropic(sphere_profile(diameter, hh, .22), width, depth), "disc", 6
    if role == "horn" or "cono" in text or "cone" in text:
        return _anisotropic(tapered_profile(diameter * .75, max(.22, diameter * .16), max(h, 1.0), .25), width, depth), "cone", 6
    if role == "tail":
        # Tails are elongated; a stronger taper preserves the semantic cue.
        tip = diameter * (0.18 if any(k in text for k in ("affusol", "pointed", "lunga", "long")) else .42)
        return _anisotropic(tapered_profile(diameter * .85, max(.22, tip), max(h, 1.0), .25), width, depth), "tail", 6
    if role in {"leg", "arm", "neck"} or "tubo" in text or "limb" in text:
        base = diameter * (0.78 if "gamba" in text or "leg" in text else 0.70)
        tip = diameter * (0.48 if "zampa" in text or "gamba" in text else 0.42)
        return _anisotropic(tapered_profile(base, tip, max(h, 1.0), .25), width, depth), "tapered", 6
    if role == "head":
        if any(k in text for k in ("triang", "affusol", "pointed", "wedge", "cuneiform")):
            # The reference-style wedge head is broad at the neck/base and
            # narrows toward the crown. A generic egg loses this identity cue.
            return _anisotropic(
                tapered_profile(width * .86, width * .55, max(h, 1.0), .25),
                width, depth
            ), "tapered_head", 6
        if any(k in text for k in ("muso", "snout", "muzzle", "allung", "elongat")):
            return _anisotropic(egg_profile(width * 1.08, max(h, width * .9), .25), width, depth), "elongated_egg", 6
        return _anisotropic(egg_profile(width, max(h, width), .25), width, depth), "egg", 6
    # Body/torso: elongated bodies are fuller through the middle; compact bodies
    # remain egg-like.  Both are still mathematically compiled by the same engine.
    if any(k in text for k in ("allung", "elongat", "slender", "snello", "rettang")):
        return _anisotropic(tapered_profile(diameter * .72, diameter * .58, max(h, 1.0), .25), width, depth), "elongated", 6
    return _anisotropic(egg_profile(width, max(h, width), .25), width, depth), "egg", 6


def _rotate_vector(v: tuple[float, float, float], rotation: Euler) -> tuple[float, float, float]:
    """Apply the same XYZ Euler convention used by ShapeNode.world_connection."""
    x, y, z = v
    rx, ry, rz = (math.radians(value) for value in (rotation.rx, rotation.ry, rotation.rz))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    y, z = y * cx - z * sx, y * sx + z * cx
    x, z = x * cy + z * sy, -x * sy + z * cy
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def _semantic_pose(part: Dict[str, Any], parent_part: Optional[Dict[str, Any]]) -> Euler:
    """Infer a conservative pose from the direction from parent center to child center.

    Image anchors are centers; the local crochet profile grows along +Z. A root
    part has no relational direction and therefore remains unrotated unless a
    future explicit pose field is supplied.
    """
    if parent_part is None:
        return Euler()
    cf = part.get("center_front") or {}
    cs = part.get("center_side") or {}
    pcf = parent_part.get("center_front") or {}
    pcs = parent_part.get("center_side") or {}
    if not isinstance(cf, dict) or not isinstance(pcf, dict):
        return Euler()
    dx = float(cf.get("x", .5)) - float(pcf.get("x", .5))
    dz = float(pcf.get("y", .5)) - float(cf.get("y", .5))
    dy = 0.0
    if isinstance(cs, dict) and isinstance(pcs, dict):
        dy = float(cs.get("x", .5)) - float(pcs.get("x", .5))
    horizontal = max(math.hypot(dx, dy), .06)
    # Local +Z should point from parent toward the child center. Yaw controls
    # front/back horizontal displacement; pitch controls depth displacement.
    # The image-plane vertical component is handled by the node's natural +Z
    # axis, so a head above a torso does not get an artificial 70° pitch.
    yaw = max(-55.0, min(55.0, math.degrees(math.atan2(dx, max(dz, .06)))))
    pitch = max(-45.0, min(45.0, math.degrees(math.atan2(-dy, max(dz, .06)))))
    roll = max(-30.0, min(30.0, math.degrees(math.atan2(dy, max(horizontal, .06))) * .35))
    return Euler(pitch, yaw, roll)


def design_to_shape_graph(design: Dict[str, Any], target_height_cm: float = 15.0) -> Dict[str, Any]:
    subject = str(design.get("subject") or "Soggetto amigurumi").strip()
    parts = list(design.get("parts") or [])
    if not parts:
        raise ValueError("Design Model privo di parti.")
    graph = ShapeGraph(subject + " amigurumi", metadata={
        "source": "design_model_compiler", "units": "cm",
        "confidence": float(design.get("overall_confidence", .5) or .5),
    })
    body_part = next((p for p in parts if p.get("role") == "body"), parts[0])
    body_h = float(body_part.get("estimated_height_cm") or target_height_cm)
    if body_h <= 0: body_h = target_height_cm

    created: Dict[str, list[str]] = {}
    for idx, part in enumerate(parts):
        pid = str(part.get("id") or f"part_{idx+1}")
        role = str(part.get("role") or "other").lower()
        count = max(1, int(part.get("count") or 1))
        # A symmetric count is represented as separate physical nodes so the
        # assembly graph can explicitly connect both sides.
        ids = [pid if count == 1 else f"{pid}_{i+1}" for i in range(count)]
        created[pid] = ids
        for i, nid in enumerate(ids):
            h, w, d = _dims(part, target_height_cm, body_h)
            profile, primitive, start = _profile(role, h, w, d, str(part.get("construction") or ""), str(part.get("label") or ""), str(part.get("notes") or ""))
            x = 0.0
            y = 0.0
            z = 0.0
            cf = part.get("center_front") or {}
            cs = part.get("center_side") or {}
            if isinstance(cf, dict):
                x = (float(cf.get("x", .5)) - .5) * max(w, target_height_cm * .35)
                z = (1.0 - float(cf.get("y", .5))) * target_height_cm
            if isinstance(cs, dict):
                y = (float(cs.get("x", .5)) - .5) * target_height_cm * .35
            if count > 1:
                # Do not invent a large left/right displacement for every
                # symmetric group. In a side/three-quarter reference (such as
                # BENCH-001) bilateral parts are primarily separated in depth.
                # A Design Model may override this with symmetry_axis="front"
                # when the reference is explicitly frontal.
                axis = str(part.get("symmetry_axis") or "depth").lower()
                side = -1 if i % 2 == 0 else 1
                offset = side * max(w * .65, .8)
                if axis in {"front", "horizontal", "x", "width"}:
                    x += offset
                else:
                    y += offset
            parent_part = next((p for p in parts if str(p.get("id") or "") == str(part.get("parent_id") or "")), None)
            rotation = _semantic_pose(part, parent_part)
            # Image anchors describe the visible CENTER of a part, while the
            # deterministic crochet profile is authored from its BASE (z=0).
            # Place the base so the geometric midpoint remains on the observed
            # image anchor. This prevents heads/limbs from drifting upward by
            # half their height and makes parent-child assembly anchors physically
            # meaningful.
            cx, cy, cz = _rotate_vector((0.0, 0.0, max(h, .5) * .5), rotation)
            position = Vec3(x - cx, y - cy, z - cz)
            node = ShapeNode(
                id=nid, name=str(part.get("label") or role.title()), kind="detail" if role in {"eye", "plate", "detail"} else "piece",
                primitive=primitive, position=position, rotation=rotation, scale=Vec3(1, 1, 1),
                profile=profile if role not in {"eye", "plate", "detail"} else profile,
                start_stitches=start, symmetry_group=part.get("symmetry_group"),
                metadata={"source":"design_model_compiler", "confidence":float(part.get("confidence", .5) or .5),
                          "role":role, "technique":select_technique(part), "design_part_id":pid,
                          "construction":str(part.get("construction") or ""),
                          "image_anchor_px":part.get("center_front"), "image_span_px":None,
                          "depth_hint":part.get("depth_hint"), "pose_source":"semantic_anchors",
                          "semantic_pose":rotation.to_dict()},
            )
            node.add_connection(ConnectionPoint("base", Vec3(0,0,0), max(w*.35,.4), "join"))
            node.add_connection(ConnectionPoint("top", Vec3(0,0,max(h,.5)), max(w*.25,.3), "join"))
            graph.add_node(node)

    # Deterministic topology: explicit parent_id wins; otherwise attach non-root
    # parts to the body. This is conservative and guarantees a connected tree.
    roots = created.get(str(body_part.get("id") or ""), [])
    if not roots:
        roots = [next(iter(graph.nodes))]
    root = roots[0]
    edge_no = 1
    for part in parts:
        pid = str(part.get("id") or "")
        for child_id in created.get(pid, []):
            if child_id == root:
                continue
            parent_pid = part.get("parent_id")
            parent_ids = created.get(str(parent_pid), []) if parent_pid else roots
            parent_id = parent_ids[0] if parent_ids else root
            if parent_id == child_id or parent_id not in graph.nodes:
                parent_id = root
            parent = graph.nodes[parent_id]
            child = graph.nodes[child_id]
            # The child base is the semantic assembly anchor. Store the same
            # world-space anchor on the parent, converted to the parent's local
            # coordinates, so assembly validation can verify that the two
            # connection points actually coincide instead of comparing arbitrary
            # radii.
            child_base_world = child.world_connection("base")
            attach_local = parent.local_from_world(child_base_world)
            attach_name = f"attach_{child_id}"
            parent.add_connection(ConnectionPoint(attach_name, attach_local, max(child.connections["base"].radius_cm, .4), "join"))
            graph.add_edge(ShapeEdge(f"e{edge_no}", parent_id, attach_name, child_id, "base", "sew", .0, "Compilato dal Design Model; anchor di assemblaggio coincidente."))
            edge_no += 1
    validation = graph.validate()
    if not validation.ok:
        raise ValueError("Design Model → Shape Graph non valido: " + "; ".join(validation.errors))
    return graph.to_dict()


def compile_design(design: Dict[str, Any], target_height_cm: float, hook_mm: float,
                   stitches10: Optional[float] = None, rounds10: Optional[float] = None, image: Any = None) -> Dict[str, Any]:
    graph_data = design_to_shape_graph(design, target_height_cm)
    graph = ShapeGraph.from_dict(graph_data)
    pose_report = None
    if image is not None:
        try:
            from .depth_pose import estimate_depth_pose
            pose_report = estimate_depth_pose(graph, image, target_height_cm)
        except Exception as exc:
            graph.metadata["pose_warning"] = str(exc)[:300]
    spc = float(stitches10 or max(18, min(40, 28 * (2.5 / max(hook_mm, .5)))))
    rpc = float(rounds10 or max(20, min(45, 32 * (2.5 / max(hook_mm, .5)))))
    project = graph.compile(Gauge(spc, rpc), include_details=True)
    checks = list(project.checks)
    checks.append(f"Gauge: {spc:.1f} maglie/10 cm; {rpc:.1f} giri/10 cm.")
    assembly = graph.assembly_instructions()
    if pose_report is not None:
        checks.append(f"Pose/Depth: confidence media {pose_report.mean_confidence:.2f}.")
        checks.extend(f"ATTENZIONE: {w}" for w in pose_report.warnings)
    return {"shape_graph": graph.to_dict(), "pattern": project.pattern, "assembly": "\n".join(assembly),
            "parts": [n.name for n in graph.nodes.values() if n.kind != "detail"],
            "checks": checks, "techniques": [{n.id: n.metadata.get("technique", "spirale_sc")} for n in graph.nodes.values()],
            "pose": pose_report.to_dict() if pose_report is not None else {"status":"semantic","confidence":0.0,"notes":"Orientamento da anchor semantici; nessuna immagine fornita."},
            "graph_validation": {"ok": graph.validate().ok, "errors": graph.validate().errors, "warnings": graph.validate().warnings}}
