"""SeedForge R3.1 core winding cell (M1 feed/tension + M2 synchronized winder).

Why this file exists
--------------------
The R3 package shipped STEP/STL for W01-W08 but (a) no generator source for
them, (b) inconsistent rotation-axis heights (W01 motor axis 37.0 mm,
W02 608 bore 25.0 mm, W05 guide bore 26.0 mm above their mounting faces),
(c) a W03 "LM8UU carriage" with no LM8UU bores, and (d) no linear-axis motor
mount, rod supports or load-cell mount.  The parts below close those gaps on
one shared datum while keeping every R3 part that already works (W01, W05,
F01-F07, W06).  See docs/project/r3-gap-analysis.md.

Datum (all millimetres)
-----------------------
* Base (plywood) top surface is z = 0.
* Mandrel axis is the +X axis at y = 0, z = AXIS_H.  AXIS_H = 37.0 comes from
  the retained R3 W01 NEMA17 mount.
* The linear (traverse) axis is parallel to X at y = LIN_Y, z = LIN_Z.
* The veneer arrives from -Y, through the guide, onto the top of the mandrel.

Status labels
-------------
CAD-VALIDATED here means: solids are valid, meshes are watertight, parts fit
the A1 Mini envelope and the layout below has no solid interference at the
sampled carriage positions.  It does NOT mean the parts have been printed,
that purchased parts match the proxies, or that the mechanism works.
Every purchased-part dimension is a nominal catalogue value:
MEASURE BEFORE FINAL FABRICATION.
"""
from __future__ import annotations

import functools
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sf_cad_common import CAD_ROOT, PALETTE, REPO_ROOT, export_part, load_step, write_glb  # noqa: E402
import paper_reference  # noqa: E402

# --------------------------------------------------------------------------- parameters
AXIS_H = 37.0          # mandrel axis height (from R3 W01)
LIN_Y = -127.0         # traverse axis centre line (y): carriage +y face clears the guide plate
LIN_Z = 22.0           # traverse axis height; NEMA17 half-width 21.15 + clearance
ROD_SPACING = 56.0     # R3 W03 note: LM8UU bores 56 mm apart
ROD_D = 8.0
ROD_LEN = 250.0        # standard 250 mm rod and T8x8 screw
SCREW_LEN = 250.0
HOME_TRIP_X = 45.0     # carriage centre x where the home switch trips (= firmware position 0)
END_TRIP_X = 149.0     # carriage centre x where the end switch trips (firmware soft limit 100 mm = x 145)
LM8UU_OD, LM8UU_L = 15.0, 24.0
BORE_LM8UU = 15.2      # tune with Z01 coupon
BORE_ROD = 8.2
NEMA = 42.3
NEMA_HOLE = 31.0
NEMA_BOSS = 22.0
# Fastener standard: M2 only (see m2_fasteners.py).  M2 clearance, M2 thread-forming pilot in
# PETG, and M2 wood screws (2.2 x 13-16 mm) into the plywood through clearance holes.
M2_CLR, M2_PILOT = 2.4, 1.8
BASE_CLR = M2_CLR      # base screws: M2 wood screws
M2_NUT_AF = 4.0        # M2 nut across flats (+0.3 clearance where trapped)
NUT_BODY_BORE = 10.6   # T8 flange nut body (nominal 10.2)
NUT_PCD = 16.0         # T8 flange nut holes (3.5 mm, 16 mm PCD nominal); M2 screws pass through
CARRIAGE_LEN = 40.0
NEMA_POCKET = 42.6     # NEMA17 body 42.3 + clearance (W15/W16 clamps)
LC_TOP = 24.7          # load-cell top (cell 12.7 tall on the F08 channel floor at z = 12)
LC_POCKET = 13.0       # load-cell channel width/height (cell 12.7 nominal)
LC_PRELOAD = 0.3       # F08 wall tops sit this far below the cell top so the cap clamps the cell
LC_CAP_X = (-24.0, -6.0)
LC_CAP_Y = 9.25
ROLLER_Z = 33.7        # sensing-roller axle (MR62ZZ, 6 mm OD -> top at 36.7, as in R3.1)
CAM_X = 70.0           # camera centre over the wound region (x 50-90)
CAM_PLATE_Z = 110.0    # camera deck underside; board 2 mm below, M12 lens pointing down
MAST_Y0 = 62.0         # front face of the plywood mast
F06_TOP_TO_STRIP = 0.6 # strip centre below F06 top face (channel 1.2 deep) - layout assumption
STRIP_T = 0.5
MANDREL_D = 0.8
MANDREL_LEN = 100.0
CHUCK_JAW_X = 21.0     # x of chuck jaw face (generic mini chuck on 5 mm shaft)
W05_X = 104.0          # W05 tower centre
GUIDE_STANDOFF = 27.0  # F06 exit face to mandrel contact point: the 28 mm wide guide rotated
                       # +-60 deg about the contact point must not touch the mandrel:
                       # d > (14 sin60 + 1) / cos60 = 26.2 mm
SLOT_R_IN = GUIDE_STANDOFF + 27.5 - 20.0   # F06 holes are +-20 mm from its centre (55 mm long)
SLOT_R_OUT = SLOT_R_IN + 40.0
ANGLE_RANGE = 60.0     # +/- degrees of guide rotation (5 deg index marks); 0 = strip square to the mandrel
FAN_R0, FAN_R1, FAN_HALF = 29.0, 86.0, 66.0  # guide plate: annular sector about the contact point

# Derived
ROD_Y = (LIN_Y + ROD_SPACING / 2, LIN_Y - ROD_SPACING / 2)
STRIP_Z = AXIS_H + MANDREL_D / 2 + STRIP_T / 2        # strip centre on mandrel top
F06_BASE_Z = STRIP_Z - (8.0 - F06_TOP_TO_STRIP)         # F06 is 8 mm tall
ARM_PLATE_T = 4.0
CARR_HALF_W = ROD_SPACING / 2 + BORE_LM8UU / 2 + 3.0
CARR_TOP = LIN_Z + 12.0
CARR_Y_FACE = LIN_Y + CARR_HALF_W                       # +y face (mandrel side)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl_x(d, x0, x1, y, z):
    return cq.Workplane("YZ").circle(d / 2).extrude(x1 - x0).translate((x0, y, z))


def cyl_y(d, y0, y1, x, z):
    return cq.Workplane("XZ").circle(d / 2).extrude(-(y1 - y0)).translate((x, y0, z))


def cyl_z(d, z0, z1, x, y):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


# --------------------------------------------------------------------------- new printed parts
def w09_linear_motor_end() -> cq.Workplane:
    """Linear-axis motor end block. Local: +x face at x=0, screw axis at y=0, z=LIN_Z.
    The NEMA17 face holes are M3-threaded, so with the M2-only standard the motor is held by
    the W16 body clamp and its 22 mm boss registers in a 3 mm-deep pocket on the -x face."""
    h = 48.0
    b = box(-16, 0, -39, 39, 0, h).union(box(-16, 12, -39, 39, 0, 5))
    b = b.cut(cyl_x(NEMA_BOSS + 0.4, -17, 1, 0, LIN_Z))              # boss register + coupler clearance
    for y in (ROD_SPACING / 2, -ROD_SPACING / 2):
        b = b.cut(cyl_x(BORE_ROD, -12, 1, y, LIN_Z))
        b = b.cut(cyl_z(M2_PILOT, LIN_Z, h + 1, -6, y))           # rod set-screw
    for y in (-30, 30):
        b = b.cut(cyl_z(BASE_CLR, -1, 6, 6, y))                    # base screws
    return b.edges("|Z").fillet(1.0)


def w10_linear_idler_end() -> cq.Workplane:
    """Linear-axis idler end: rod sockets + 608ZZ pocket for the T8 screw end."""
    h = 48.0
    b = box(0, 16, -39, 39, 0, h).union(box(-12, 16, -39, 39, 0, 5))
    b = b.cut(cyl_x(10.0, -1, 17, 0, LIN_Z))
    b = b.cut(cyl_x(22.2, 16 - 7.2, 17, 0, LIN_Z))               # 608ZZ 22x7
    for y in (ROD_SPACING / 2, -ROD_SPACING / 2):
        b = b.cut(cyl_x(BORE_ROD, -1, 12, y, LIN_Z))
        b = b.cut(cyl_z(M2_PILOT, LIN_Z, h + 1, 6, y))
    for y in (-30, 30):
        b = b.cut(cyl_z(BASE_CLR, -1, 6, -6, y))
    return b.edges("|Z").fillet(1.0)


def w11_carriage() -> cq.Workplane:
    """LM8UU traverse carriage (replaces R3 W03, which had no bearing bores).

    Local: centre x=0, screw axis y=0, z in global height.  Print standing on
    its -x face so the bearing bores print round.
    """
    hw = CARR_HALF_W
    b = box(-CARRIAGE_LEN / 2, CARRIAGE_LEN / 2, -hw, hw, LIN_Z - 10.6, CARR_TOP)
    for y in (ROD_SPACING / 2, -ROD_SPACING / 2):
        b = b.cut(cyl_x(BORE_LM8UU, -30, 30, y, LIN_Z))
    b = b.cut(cyl_x(NUT_BODY_BORE, -30, 30, 0, LIN_Z))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        b = b.cut(cyl_x(M2_PILOT, -CARRIAGE_LEN / 2 - 1, -CARRIAGE_LEN / 2 + 12,
                        NUT_PCD / 2 * math.cos(a), LIN_Z + NUT_PCD / 2 * math.sin(a)))
    for x in (-12, 12):                                            # arm screws (+y face)
        b = b.cut(cyl_y(M2_PILOT, hw - 10, hw + 1, x, LIN_Z + 6))
    return b.edges("|X").fillet(1.5)


def w12_guide_arm() -> cq.Workplane:
    """Guide arm: bolts to the carriage +y face and carries F06/F07 on a
    fan-shaped plate.  Two concentric arc slots are centred on the strip
    contact point on the mandrel, so changing the guide angle does not move
    the contact point.  The fan keeps the plate >= 11 mm away from the mandrel
    axis in y so it clears the chuck and the W05 end support.
    Local x=0 is the carriage centre; y/z are global.  Print plate-down.
    """
    y_face = CARR_Y_FACE
    top = F06_BASE_Z
    a0, a1 = math.radians(-90 - FAN_HALF), math.radians(-90 + FAN_HALF)
    n = 24
    outer = [(FAN_R1 * math.cos(a0 + (a1 - a0) * i / n), FAN_R1 * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    inner = [(FAN_R0 * math.cos(a1 - (a1 - a0) * i / n), FAN_R0 * math.sin(a1 - (a1 - a0) * i / n)) for i in range(n + 1)]
    fan = cq.Workplane("XY").polyline(outer + inner).close().extrude(ARM_PLATE_T).translate((0, 0, top - ARM_PLATE_T))
    fan = fan.intersect(box(-200, 200, y_face, 0, top - ARM_PLATE_T - 1, top + 1))   # never past the carriage face
    web = box(-18, 18, y_face, y_face + 14, top - ARM_PLATE_T, top)
    flange = box(-18, 18, y_face, y_face + 4.0, LIN_Z - 6, top)
    gusset = (cq.Workplane("YZ").polyline([(y_face + 4, top - ARM_PLATE_T), (y_face + 4, LIN_Z - 2),
                                           (y_face + 14, top - ARM_PLATE_T)]).close()
              .extrude(4).translate((-2, 0, 0)))
    arm = fan.union(web).union(flange).union(gusset)
    for x in (-12, 12):
        arm = arm.cut(cyl_y(M2_CLR, y_face - 1, y_face + 5, x, LIN_Z + 6))
    for r in (SLOT_R_IN, SLOT_R_OUT):
        s0, s1 = math.radians(-90 - ANGLE_RANGE), math.radians(-90 + ANGLE_RANGE)
        m = 36
        for i in range(2 * m + 1):
            ang = s0 + (s1 - s0) * i / (2 * m)
            arm = arm.cut(cyl_z(M2_CLR, top - ARM_PLATE_T - 1, top + 1, r * math.cos(ang), r * math.sin(ang)))
    for deg in range(-60, 61, 5):                     # engraved index marks along the outer slot
        ang = math.radians(-90 + deg)
        r0 = SLOT_R_OUT + 3.0
        L = 3.5 if deg % 15 == 0 else 2.0
        mark = (cq.Workplane("XY").rect(L, 0.6).extrude(0.6)
                .rotate((0, 0, 0), (0, 0, 1), math.degrees(ang))
                .translate(((r0 + L / 2) * math.cos(ang), (r0 + L / 2) * math.sin(ang), top - 0.6)))
        arm = arm.cut(mark)
    return arm


def w13_w05_riser() -> cq.Workplane:
    """Spacer that lifts the retained R3 W05 end guide (bore at 26.0 mm) to the
    37.0 mm mandrel axis: 11.0 mm thick, W05 footprint and hole pattern."""
    b = box(-21, 21, -18, 18, 0, 11.0)
    for x in (-17, 17):                                # base screws (fit before W05 goes on top)
        for y in (-14, 14):
            b = b.cut(cyl_z(BASE_CLR, -1, 12, x, y))
    for x in (-13, 13):
        for y in (-9.2, 9.2):
            b = b.cut(cyl_z(M2_CLR, -1, 12, x, y))
    return b.edges("|Z").fillet(1.0)


def f08_load_cell_mount() -> cq.Workplane:
    """Clamp cradle for the fixed end of a 1 kg bar load cell (nominal 80 x 12.7 x 12.7 mm -
    MEASURE YOUR CELL).  The cell's own threaded holes are M4/M5, so with the M2-only
    standard its fixed end (30 mm) is clamped in a channel by the F13 cap and four M2
    thread-forming screws; the gauge region stays free.  Calibrate in place with hanging
    masses (docs/calibration.md).  Local: channel floor at z = 12, fixed end spans x = -30..0.
    """
    b = box(-40, 10, -22, 22, 0, 6).union(box(-30, 0, -12, 12, 0, LC_TOP - LC_PRELOAD))
    b = b.cut(box(-31, 1, -LC_POCKET / 2, LC_POCKET / 2, 12.0, 40))
    for x in LC_CAP_X:
        for y in (-LC_CAP_Y, LC_CAP_Y):
            b = b.cut(cyl_z(M2_PILOT, 14.0, 30, x, y))
    for x in (-34, 4):
        for y in (-16, 16):
            b = b.cut(cyl_z(BASE_CLR, -1, 7, x, y))
    return b.edges("|Z").fillet(1.0)


def f13_load_cell_cap() -> cq.Workplane:
    """Cap for F08: presses the load-cell end into the channel (0.3 mm preload gap) with four
    M2 screws.  Local frame as F08 (cap sits on the cell top at z = LC_TOP)."""
    b = box(-30, 0, -12, 12, LC_TOP, LC_TOP + 4.0)
    for x in LC_CAP_X:
        for y in (-LC_CAP_Y, LC_CAP_Y):
            b = b.cut(cyl_z(M2_CLR, LC_TOP - 1, LC_TOP + 5, x, y))
    return b.edges("|Z").fillet(1.0)


def f12_sensing_roller_yoke() -> cq.Workplane:
    """Sleeve over the free end of the load cell carrying the tension-sensing roller: two
    MR62ZZ bearings (2 x 6 x 2.5 mm) on an M2 x 16 screw axle along x, between two cheeks.
    One M2 thread-forming screw from the top locks the sleeve on the cell.  Replaces the
    623ZZ-on-M3 roller of R3.1.  Local: cell end at x = 0, cell bottom at z = 12."""
    b = box(-14, 0, -9.5, 9.5, 9.0, LC_TOP + 3.0)
    b = b.cut(box(-15, 1, -LC_POCKET / 2, LC_POCKET / 2, 11.85, LC_TOP + 0.15))
    b = b.cut(cyl_z(M2_PILOT, LC_TOP, LC_TOP + 4, -7, 0))
    for x0, x1 in ((-14, -11), (-3, 0)):
        b = b.union(box(x0, x1, -5, 5, LC_TOP + 2.9, ROLLER_Z + 4.0))
    b = b.cut(cyl_x(M2_CLR, -15, -10.5, 0, ROLLER_Z)).cut(cyl_x(M2_PILOT, -3.5, 1, 0, ROLLER_Z))
    return b


def w15_nema17_body_clamp(axis_h: float) -> cq.Workplane:
    """NEMA17 body clamp.  A NEMA17's face holes are M3-threaded, which the M2-only standard
    cannot use, so the motor body is held in a split collar (two M2 pinch screws across the
    top slit) whose flange takes four M2 wood screws into the plywood.  The motor face still
    registers on its mount (W01 / W09).  Local: collar spans x = -28..0, motor axis at y = 0,
    z = axis_h.  Print standing on the -x face (no bridges)."""
    L, half, wall = 28.0, NEMA_POCKET / 2, 4.0
    top = axis_h + half + wall
    b = box(-L, 0, -half - wall, half + wall, 0, top).union(box(-L, 0, -half - wall - 10, half + wall + 10, 0, 4))
    pocket = (cq.Workplane("YZ").rect(NEMA_POCKET, NEMA_POCKET).extrude(L + 2).edges("|X").chamfer(3.0)
              .translate((-L - 1, 0, axis_h)))
    b = b.cut(pocket)
    ear = box(-L, 0, -6, 6, top - 0.01, top + 7.0)
    b = b.union(ear)
    b = b.cut(box(-L - 1, 1, -0.75, 0.75, axis_h + half - 0.5, top + 8))         # pinch slit
    for x in (-L + 7, -7):
        b = b.cut(cyl_y(M2_CLR, -7, -0.75, x, top + 3.5)).cut(cyl_y(M2_PILOT, 0.75, 7, x, top + 3.5))
        for y in (-half - wall - 5, half + wall + 5):
            b = b.cut(cyl_z(BASE_CLR, -1, 5, x, y))
    return b


def w15_rotation_clamp() -> cq.Workplane:
    return w15_nema17_body_clamp(AXIS_H)


def w16_linear_clamp() -> cq.Workplane:
    return w15_nema17_body_clamp(LIN_Z)


def w17_mast_foot() -> cq.Workplane:
    """Foot bracket for the camera mast (a 30 x 18 mm plywood strip cut from the base offcut).
    Two M2 wood screws into the mast, four into the base.  Local: mast front face at y = 0
    (mast toward +y), mast centred on x = 0, base at z = 0."""
    b = box(-20, 20, -24, 0, 0, 4).union(box(-15, 15, -4, 0, 0, 40))
    for x in (-17, 17):
        b = b.union(cq.Workplane("YZ").polyline([(-22, 4), (-4, 4), (-4, 30)]).close().extrude(3).translate((x - 1.5, 0, 0)))
    for z in (16, 32):
        b = b.cut(cyl_y(M2_CLR, -5, 1, 0, z))
    for x in (-15, 15):
        for y in (-19, -8):
            b = b.cut(cyl_z(BASE_CLR, -1, 5, x, y))
    return b


def w18_camera_arm() -> cq.Workplane:
    """Camera arm: screws to the top of the plywood mast (two M2 wood screws) and holds a
    38 x 38 mm USB board camera on four M2 screws (34 mm square pattern - MEASURE) with
    the M12 lens looking down through a 16 mm hole.  Replaces W06 + the 2020 extrusion.
    Local: global y and z; camera centre at x = 0, mast front face at y = MAST_Y0."""
    z0 = CAM_PLATE_Z
    plate = box(-15, 15, MAST_Y0 - 4, MAST_Y0, z0, z0 + 60)
    arm = box(-10, 10, 18, MAST_Y0 - 3.9, z0, z0 + 6)
    gus = cq.Workplane("YZ").polyline([(MAST_Y0 - 4, z0 + 6), (MAST_Y0 - 4, z0 + 40), (MAST_Y0 - 30, z0 + 6)]).close().extrude(4).translate((-2, 0, 0))
    deck = box(-21, 21, -21, 21, z0, z0 + 4)
    b = plate.union(arm).union(gus).union(deck)
    b = b.cut(cyl_z(16.0, z0 - 1, z0 + 5, 0, 0))
    for x in (-17, 17):
        for y in (-17, 17):
            b = b.union(cyl_z(5.0, z0 - 2.0, z0 + 0.01, x, y))             # 2 mm standoffs under the deck
            b = b.cut(cyl_z(M2_PILOT, z0 - 3, z0 + 5, x, y))
    for z in (z0 + 25, z0 + 50):
        b = b.cut(cyl_y(M2_CLR, MAST_Y0 - 5, MAST_Y0 + 1, 0, z))
    return b


def f09_spool_stand_left_bored() -> cq.Workplane:
    """R3 F01 with the missing 608ZZ pocket added (F01 shipped without any
    bearing bore while its partner F02 has one at z = 65 mm).  Pocket 22.2 x
    7.2 mm from the inner face, 12 mm axle clearance through."""
    s = r3("F01_spool_stand_left")
    s = s.cut(cyl_x(22.2, -18.0 - 7.2, -17.0, 0, 65.0).val()).cut(cyl_x(12.0, -31.0, -17.0, 0, 65.0).val())
    return cq.Workplane(obj=s)


def f10_spool_hub_8mm() -> cq.Workplane:
    """R3 F03 hub re-bored from 5.2 to 8.2 mm so it runs on an 8 mm axle in
    608ZZ bearings (R3 specified 608 bearings, whose bore is 8 mm, with a
    5 mm axle - those parts cannot be assembled together)."""
    s = r3("F03_spool_hub")
    return cq.Workplane(obj=s.cut(cyl_z(8.2, -10, 30, 0, 0).val()))


def f11_dancer_pivot_post() -> cq.Workplane:
    """Pivot post for the R3 F04 dancer arm.  The arm's 6.3 mm end hole fits a
    6 mm potentiometer shaft, so the pot bushing (M7, 7.2 mm hole - MEASURE)
    is the pivot and the pot reads dancer angle on Uno A0.  Spring anchor hole
    for a light extension spring."""
    b = box(-25, 25, -20, 20, 0, 5).union(box(-6, 6, -20, -12, 0, 70))
    b = b.cut(cyl_y(7.2, -21, -11, 0, 62.0))                       # pot bushing
    b = b.cut(cyl_y(3.2, -21, -11, 0, 40.0))                       # anti-rotation tab / spring anchor
    for x in (-19, 19):
        for y in (-14, 14):
            b = b.cut(cyl_z(BASE_CLR, -1, 6, x, y))
    return b.edges("|Z").fillet(1.0)


def w14_limit_switch_clamp() -> cq.Workplane:
    """Clamps onto an 8 mm guide rod and carries a KW12-style lever microswitch
    (nominal 20 x 10 x 6.4 mm, 2 x M2 holes 9.5 mm apart - MEASURE).  Sliding
    the clamp along the rod sets the home/end trip points physically.  Local:
    rod axis along x through the origin; the switch pad extends toward -y.
    """
    ring = cyl_x(17.0, -5, 5, 0, 0)
    ears = box(-5, 5, -3, 3, 7.0, 13.0)
    pad = box(-5, 5, -32, -6, -8.5, -1.5)
    b = ring.union(ears).union(pad)
    b = b.cut(cyl_x(8.2, -6, 6, 0, 0)).cut(box(-6, 6, -0.75, 0.75, 3.0, 14.0))     # bore + pinch slot
    b = b.cut(cyl_y(M2_CLR, -4, 0, 0, 10.0)).cut(cyl_y(M2_PILOT, 0, 4, 0, 10.0))     # M2 pinch screw
    for y in (-14.25, -23.75):
        b = b.cut(cyl_x(2.2, -6, 6, y, -5.0))                                        # switch screws (along x)
    return b


NEW_PARTS = {
    "W09_linear_motor_end_block": (w09_linear_motor_end, "M2 winder", 1, "PETG",
                                   "Rod sockets + NEMA17 boss register for the traverse axis (motor held by W16). Print on its base, 40% infill, 4 walls."),
    "W10_linear_idler_end_block": (w10_linear_idler_end, "M2 winder", 1, "PETG",
                                   "Rod sockets + 608ZZ pocket supporting the free end of the T8x8 screw."),
    "W11_lm8uu_traverse_carriage": (w11_carriage, "M2 winder", 1, "PETG",
                                    "Two LM8UU bores (15.2 mm, tune with Z01) + T8 flange-nut mount (16 mm PCD). Print standing on the -x face."),
    "W12_angle_adjustable_guide_arm": (w12_guide_arm, "M1/M2", 1, "PETG",
                                       "Carries F06/F07. Concentric arc slots centred on the mandrel contact point give +/-60 deg of guide angle with 5 deg index marks."),
    "W13_w05_axis_riser_11mm": (w13_w05_riser, "M2 winder", 1, "PETG",
                                "Lifts retained W05 end guide to the 37.0 mm mandrel axis."),
    "W14_limit_switch_rod_clamp": (w14_limit_switch_clamp, "M2 winder", 2, "PETG",
                                   "Home and end microswitch clamp on the outer 8 mm rod; slide to set trip points (home: carriage x 45 mm)."),
    "F08_load_cell_mount": (f08_load_cell_mount, "M1 feed", 1, "PETG",
                            "Channel cradle for the fixed end of a 1 kg bar load cell; clamped by F13 with 4 x M2."),
    "F12_sensing_roller_yoke": (f12_sensing_roller_yoke, "M1 feed", 1, "PETG",
                                "Slides over the load-cell free end; 2 x MR62ZZ on an M2 axle form the tension-sensing roller."),
    "F13_load_cell_clamp_cap": (f13_load_cell_cap, "M1 feed", 1, "PETG",
                                "Cap that clamps the load cell into F08 (0.3 mm preload) with 4 x M2."),
    "W15_nema17_body_clamp_rotation": (w15_rotation_clamp, "M2 winder", 1, "PETG",
                                       "Split collar holding the rotation NEMA17 body (axis 37 mm); 2 x M2 pinch, 4 x M2 wood screws. Print on the -x face, 4 walls."),
    "W16_nema17_body_clamp_linear": (w16_linear_clamp, "M2 winder", 1, "PETG",
                                     "Split collar holding the traverse NEMA17 body (axis 22 mm, 0.7 mm floor rests on the plywood). Print on the -x face, 4 walls."),
    "W17_camera_mast_foot": (w17_mast_foot, "M7 vision", 1, "PETG",
                             "Foot bracket for the 30 x 18 mm plywood camera mast; M2 wood screws."),
    "W18_camera_arm": (w18_camera_arm, "M7 vision", 1, "PETG",
                       "Arm from the mast top holding a 38 x 38 mm USB board camera (4 x M2, 34 mm pattern - MEASURE) over the coil. Print on the mast-side face."),
    "F09_spool_stand_left_608_bore": (f09_spool_stand_left_bored, "M1 feed", 1, "PETG",
                                      "Supersedes R3 F01 (which had no bearing bore). Derived from the R3 F01 STEP."),
    "F10_spool_hub_8mm_bore": (f10_spool_hub_8mm, "M1 feed", 2, "PETG",
                               "Supersedes R3 F03 (5.2 mm bore) for an 8 mm axle in 608ZZ bearings. Derived from the R3 F03 STEP."),
    "F11_dancer_pivot_post": (f11_dancer_pivot_post, "M1 feed", 1, "PETG",
                              "Pivot post for F04: 10k pot bushing is the pivot (A0 dancer angle). MEASURE pot bushing."),
}


# --------------------------------------------------------------------------- purchased-part proxies
def nema17(body_len=40.0, shaft_len=24.0):
    """NEMA17 proxy: face at x=0, body toward -x, shaft toward +x along y=z=0."""
    body = box(-body_len, 0, -NEMA / 2, NEMA / 2, -NEMA / 2, NEMA / 2).edges("|X").chamfer(3.5)
    boss = cyl_x(NEMA_BOSS, 0, 2, 0, 0)
    shaft = cyl_x(5.0, 0, shaft_len, 0, 0)
    return body, boss.union(shaft)


def lm8uu():
    return cyl_x(LM8UU_OD, -LM8UU_L / 2, LM8UU_L / 2, 0, 0).cut(cyl_x(8.0, -13, 13, 0, 0))


def coupler(x0, length=25.0, d=19.0):
    return cyl_x(d, x0, x0 + length, 0, 0)


def spool_proxy(d=110.0, w=30.0):
    flange = cyl_x(d, -w / 2, -w / 2 + 2, 0, 0).union(cyl_x(d, w / 2 - 2, w / 2, 0, 0))
    core = cyl_x(50.0, -w / 2, w / 2, 0, 0)
    return flange.union(core)


def veneer_coil(n_turns=8, pitch=5.0, width=2.5):
    return paper_reference.helix_ribbon(MANDREL_D, STRIP_T, width, n_turns, n_turns * pitch)


def strip_segment(p0, p1, width=2.5, t=STRIP_T):
    p0, p1 = cq.Vector(*p0), cq.Vector(*p1)
    d = p1 - p0
    L = d.Length
    seg = cq.Workplane("XY").box(L, width, t).translate((L / 2, 0, 0))
    # rotate +x onto d
    yaw = math.degrees(math.atan2(d.y, d.x))
    pitch = -math.degrees(math.asin(d.z / L))
    return seg.rotate((0, 0, 0), (0, 1, 0), pitch).rotate((0, 0, 0), (0, 0, 1), yaw).translate(p0.toTuple())


# --------------------------------------------------------------------------- layout
@dataclass
class Layout:
    carriage_x: float = 60.0
    guide_angle_deg: float = 0.0     # guide rotation about the contact point (0 = strip square to axis)


@functools.lru_cache(maxsize=None)
def r3(stem):
    return load_step(CAD_ROOT / "step" / "machine" / f"{stem}.step")


def place(shape, dx=0.0, dy=0.0, dz=0.0, rz=0.0, rx=0.0, ry=0.0):
    s = shape if isinstance(shape, cq.Shape) else shape.val() if len(shape.vals()) == 1 else cq.Compound.makeCompound(shape.vals())
    if rx:
        s = s.rotate((0, 0, 0), (1, 0, 0), rx)
    if ry:
        s = s.rotate((0, 0, 0), (0, 1, 0), ry)
    if rz:
        s = s.rotate((0, 0, 0), (0, 0, 1), rz)
    return s.translate(cq.Vector(dx, dy, dz))


def build_layout(lay: Layout, new_parts: dict, with_material=True):
    """Return list of (name, shape, rgba, category)."""
    P = PALETTE
    out = []
    add = lambda n, s, c, cat: out.append((n, s, c, cat))  # noqa: E731
    base_x0, base_x1, base_y0, base_y1 = -120.0, 260.0, -377.0, 130.0
    add("base_plywood_18mm", place(box(base_x0, base_x1, base_y0, base_y1, -18, 0)), P["base"], "purchased")

    # ---- M2 rotation train (W01 retained from R3)
    add("W01_nema17_rotation_mount", place(r3("W01_nema17_rotation_mount")), P["printed"], "printed_r3")
    body, shaft = nema17()
    add("motor_rotation_NEMA17", place(body, dx=-33.0, dz=AXIS_H), P["motor"], "purchased")
    add("motor_rotation_shaft", place(shaft, dx=-33.0, dz=AXIS_H), P["metal"], "purchased")
    add("W15_nema17_body_clamp_rotation", place(new_parts["W15_nema17_body_clamp_rotation"], dx=-33.0 - 8.0),
        P["printed_accent"], "printed_new")
    add("chuck_adapter_5mm", place(cyl_x(11.0, -21.0, -8.0, 0, AXIS_H)), P["dark_metal"], "purchased")
    add("mini_drill_chuck", place(cyl_x(17.0, -8.0, CHUCK_JAW_X - 3, 0, AXIS_H)
                                   .union(cyl_x(9.0, CHUCK_JAW_X - 3, CHUCK_JAW_X, 0, AXIS_H))), P["dark_metal"], "purchased")
    m_x0 = CHUCK_JAW_X - 8.0
    add("mandrel_0p8mm_steel", place(cyl_x(MANDREL_D, m_x0, m_x0 + MANDREL_LEN, 0, AXIS_H)), P["metal"], "purchased")
    add("W13_w05_axis_riser_11mm", place(new_parts["W13_w05_axis_riser_11mm"], dx=W05_X), P["printed_accent"], "printed_new")
    add("W05_mandrel_end_guide", place(r3("W05_mandrel_end_guide"), dx=W05_X, dz=11.0), P["printed"], "printed_r3")
    add("guide_tube_ptfe", place(cyl_x(2.0, W05_X - 7, W05_X + 7, 0, AXIS_H).cut(cyl_x(1.0, W05_X - 8, W05_X + 8, 0, AXIS_H))),
        P["silicone"], "purchased")

    # ---- M2 traverse axis
    x_w09_face = -36.0
    add("W09_linear_motor_end_block", place(new_parts["W09_linear_motor_end_block"], dx=x_w09_face, dy=LIN_Y), P["printed_accent"], "printed_new")
    body, shaft = nema17()
    add("motor_linear_NEMA17", place(body, dx=x_w09_face - 16, dy=LIN_Y, dz=LIN_Z), P["motor"], "purchased")
    add("motor_linear_shaft", place(shaft, dx=x_w09_face - 16, dy=LIN_Y, dz=LIN_Z), P["metal"], "purchased")
    add("W16_nema17_body_clamp_linear", place(new_parts["W16_nema17_body_clamp_linear"], dx=x_w09_face - 16 - 8.0, dy=LIN_Y),
        P["printed_accent"], "printed_new")
    rod_x0 = x_w09_face - 12
    x_w10 = rod_x0 + ROD_LEN - 12
    add("W10_linear_idler_end_block", place(new_parts["W10_linear_idler_end_block"], dx=x_w10, dy=LIN_Y), P["printed_accent"], "printed_new")
    for i, y in enumerate(ROD_Y):
        add(f"rod_8mm_{i+1}", place(cyl_x(ROD_D, rod_x0, rod_x0 + ROD_LEN, y, LIN_Z)), P["metal"], "purchased")
    add("coupler_5x8", place(coupler(-40.0), dy=LIN_Y, dz=LIN_Z), P["dark_metal"], "purchased")
    # limit switches on the outer rod: the lever tip touches the carriage end face at the trip position
    y_out = ROD_Y[1]
    for name, sgn in (("home", 1), ("end", -1)):
        face = HOME_TRIP_X - CARRIAGE_LEN / 2 if sgn > 0 else END_TRIP_X + CARRIAGE_LEN / 2
        xc = face - sgn * 14.4
        add(f"W14_limit_switch_clamp_{name}", place(new_parts["W14_limit_switch_rod_clamp"], dx=xc, dy=y_out, dz=LIN_Z),
            P["printed_accent"], "printed_new")
        body = box(5.0, 11.4, -29, -9, -10.0, 0.0) if sgn > 0 else box(-11.4, -5.0, -29, -9, -10.0, 0.0)
        lever = box(11.4, 14.4, -12, -9.5, -8, -2) if sgn > 0 else box(-14.4, -11.4, -12, -9.5, -8, -2)
        add(f"microswitch_{name}", place(body, dx=xc, dy=y_out, dz=LIN_Z), P["dark_metal"], "purchased")
        add(f"microswitch_lever_{name}", place(lever, dx=xc, dy=y_out, dz=LIN_Z), P["metal"], "purchased")
    scr_x0 = -27.0
    add("leadscrew_T8x8", place(cyl_x(8.0, scr_x0, scr_x0 + SCREW_LEN, LIN_Y, LIN_Z)), P["metal"], "purchased")
    add("bearing_608ZZ", place(cyl_x(22.0, x_w10 + 16 - 7, x_w10 + 16, LIN_Y, LIN_Z).cut(cyl_x(8, x_w10, x_w10 + 20, LIN_Y, LIN_Z))),
        P["metal"], "purchased")
    cx = lay.carriage_x
    add("W11_lm8uu_traverse_carriage", place(new_parts["W11_lm8uu_traverse_carriage"], dx=cx, dy=LIN_Y), P["printed_accent"], "printed_new")
    for i, y in enumerate(ROD_Y):
        add(f"lm8uu_{i+1}", place(lm8uu(), dx=cx, dy=y, dz=LIN_Z), P["metal"], "purchased")
    nut = cyl_x(22.0, -3.5, 0, 0, 0).union(cyl_x(10.2, 0, 12, 0, 0))
    add("t8_flange_nut", place(nut, dx=cx - CARRIAGE_LEN / 2 - 0.01, dy=LIN_Y, dz=LIN_Z), P["metal"], "purchased")
    add("W12_angle_adjustable_guide_arm", place(new_parts["W12_angle_adjustable_guide_arm"], dx=cx), P["printed_accent"], "printed_new")

    # F06 guide + F07 lid: long axis along +y toward the mandrel, rotated about the contact point.
    f06 = r3("F06_veneer_guide_45deg_lower")     # local: length along x, holes at x=+-20, y=-0.9
    f07 = r3("F07_veneer_guide_lid")
    ang = lay.guide_angle_deg
    for name, shp, z in (("F06_veneer_guide_lower", f06, F06_BASE_Z), ("F07_veneer_guide_lid", f07, F06_BASE_Z + 8.0)):
        s = shp.rotate((0, 0, 0), (0, 0, 1), 90).translate((0.9, -(GUIDE_STANDOFF + 27.5), z))   # exit face 16 mm from contact
        s = s.rotate((0, 0, 0), (0, 0, 1), ang).translate((cx, 0, 0))
        add(name, s, P["printed"], "printed_r3")

    # ---- M1 feed and tension (layout reference)
    y_spool, z_spool, xs = -317.0, 65.0, 60.0
    st_l = new_parts["F09_spool_stand_left_608_bore"].rotate((0, 0, 0), (0, 0, 1), 180)
    st_r = r3("F02_spool_stand_right").rotate((0, 0, 0), (0, 0, 1), 180)
    add("F09_spool_stand_left_608_bore", place(st_l, dx=xs - 37 - 30, dy=y_spool), P["printed_accent"], "printed_new")
    add("F02_spool_stand_right", place(st_r, dx=xs + 37 + 30, dy=y_spool), P["printed"], "printed_r3")
    add("axle_8mm", place(cyl_x(8.0, xs - 75, xs + 75, y_spool, z_spool)), P["metal"], "purchased")
    for i, sx in enumerate((-1, 1)):
        hub = new_parts["F10_spool_hub_8mm_bore"].rotate((0, 0, 0), (0, 1, 0), 90 * sx)
        add(f"F10_spool_hub_{i+1}", place(hub, dx=xs + sx * 15.0, dy=y_spool, dz=z_spool), P["printed_accent"], "printed_new")
    add("veneer_spool", place(spool_proxy(d=100.0, w=28.0), dx=xs, dy=y_spool, dz=z_spool), P["wood_dark"], "purchased")
    # dancer: F04 arm on a 10k pot shaft (pivot) carrying an F05 roller; arm swings in the y-z plane
    y_d, arm_ang = -242.0, 60.0                         # arm points toward -y, 60 deg above horizontal
    x_post = xs - 0.5
    add("F11_dancer_pivot_post", place(new_parts["F11_dancer_pivot_post"].rotate((0, 0, 0), (0, 0, 1), 90), dx=x_post, dy=y_d),
        P["printed_accent"], "printed_new")
    add("pot_10k", place(cyl_x(16.0, 0.0, 9.0, 0, 0), dx=x_post + 20.0, dy=y_d, dz=62.0), P["dark_metal"], "purchased")
    pivot = (xs + 8.0, y_d, 62.0)
    arm = (r3("F04_dancer_arm").translate((34.0, 0, -3.0))            # pivot hole to origin, centred in thickness
           .rotate((0, 0, 0), (0, 1, 0), 90)                          # length along -z, thickness along x
           .rotate((0, 0, 0), (1, 0, 0), 180 + (90 - arm_ang)))       # point toward -y and up
    add("F04_dancer_arm", place(arm, dx=pivot[0], dy=pivot[1], dz=pivot[2]), P["printed"], "printed_r3")
    rd = (xs, y_d - 68.0 * math.cos(math.radians(arm_ang)), 62.0 + 68.0 * math.sin(math.radians(arm_ang)))
    add("F05_dancer_roller", place(r3("F05_dancer_roller").rotate((0, 0, 0), (0, 1, 0), 90).translate((-5.0, 0, 0)),
                                   dx=rd[0], dy=rd[1], dz=rd[2]), P["printed"], "printed_r3")
    # load cell: bar along +x on the F08 pedestal, sensing roller above its free end on the strip line
    y_lc = -205.0
    add("F08_load_cell_mount", place(new_parts["F08_load_cell_mount"], dx=xs - 50.0, dy=y_lc), P["printed_accent"], "printed_new")
    add("load_cell_1kg_bar", place(box(-80.0, 0.0, -6.35, 6.35, 12.0, 24.7), dx=xs, dy=y_lc), P["metal"], "purchased")
    add("F13_load_cell_clamp_cap", place(new_parts["F13_load_cell_clamp_cap"], dx=xs - 50.0, dy=y_lc), P["printed_accent"], "printed_new")
    add("F12_sensing_roller_yoke", place(new_parts["F12_sensing_roller_yoke"], dx=xs, dy=y_lc), P["printed_accent"], "printed_new")
    roller_z = ROLLER_Z
    add("sensing_rollers_MR62ZZ", place(cyl_x(6.0, -10.5, -5.5, 0, 0).union(cyl_x(2.0, -13.5, -2.5, 0, 0)), dx=xs, dy=y_lc, dz=roller_z),
        P["dark_metal"], "purchased")

    # ---- fixed camera (M7 QA in the first build target): overhead camera + back-light under the coil.
    # A side camera would need its back-light on the feed side, in the strip path, so the
    # silhouette is taken from above with a horizontal panel below the mandrel.
    # panel x 36-96 covers the whole wound region (carriage x 45-95); at z 20-23 it passes under the
    # open front of W05 and clears W01 (x <= 33) and the W13 riser (x >= 83, z <= 11)
    add("backlight_panel", place(box(36.0, 96.0, -10.0, 10.0, 20.0, 23.0)), (240, 244, 248, 255), "purchased")
    add("backlight_standoffs", place(box(38.0, 42.0, -4.0, 4.0, 0.0, 20.0).union(box(74.0, 78.0, -4.0, 4.0, 0.0, 20.0))),
        P["dark_metal"], "purchased")
    # budget camera: 38 x 38 mm USB board camera with an M12 lens, on the W18 arm; mast = plywood strip
    add("camera_mast_plywood", place(box(-15.0, 15.0, MAST_Y0, MAST_Y0 + 18.0, 0.0, 175.0), dx=CAM_X), P["base"], "purchased")
    add("W17_camera_mast_foot", place(new_parts["W17_camera_mast_foot"], dx=CAM_X, dy=MAST_Y0), P["printed_accent"], "printed_new")
    add("W18_camera_arm", place(new_parts["W18_camera_arm"], dx=CAM_X), P["printed_accent"], "printed_new")
    cam = box(-19, 19, -19, 19, CAM_PLATE_Z - 4.0, CAM_PLATE_Z - 2.0).union(cyl_z(14.0, CAM_PLATE_Z - 24.0, CAM_PLATE_Z - 4.0, 0, 0))
    add("camera_proxy", place(cam, dx=CAM_X), P["dark_metal"], "purchased")

    if with_material:
        coil_x0 = cx - 8 * 5.0
        coil = veneer_coil().val().rotate((0, 0, 0), (0, 1, 0), 90).translate((max(coil_x0, CHUCK_JAW_X + 6), 0, AXIS_H))
        add("veneer_coil_wound", coil, P["wood"], "material")
        g = math.radians(lay.guide_angle_deg)
        r_in = GUIDE_STANDOFF + 55.0
        p_guide = (cx + r_in * math.sin(g), -r_in * math.cos(g), STRIP_Z)
        p_lc = (xs, y_lc, roller_z + 5.25)
        p_d = (xs, rd[1], rd[2] + 15.25)
        add("veneer_strip_feed", place(strip_segment(p_lc, p_guide)), P["wood_light"], "material")
        add("veneer_strip_guide", place(strip_segment(p_guide, (cx, -0.6, STRIP_Z))), P["wood_light"], "material")
        add("veneer_strip_dancer", place(strip_segment(p_d, p_lc)), P["wood_light"], "material")
        add("veneer_strip_spool", place(strip_segment((xs, y_spool, z_spool + 50.25), p_d)), P["wood_light"], "material")
    return out


# --------------------------------------------------------------------------- checks
def interference_report(new_parts):
    """Boolean-intersect moving parts against fixed parts over the traverse range."""
    moving = {"W11_lm8uu_traverse_carriage", "W12_angle_adjustable_guide_arm", "F06_veneer_guide_lower",
              "F07_veneer_guide_lid", "lm8uu_1", "lm8uu_2", "t8_flange_nut"}
    ignore_pairs = {("W11_lm8uu_traverse_carriage", "microswitch_lever_home"),   # designed contact at the trip points
                    ("W11_lm8uu_traverse_carriage", "microswitch_lever_end"),
                    ("lm8uu_1", "rod_8mm_1"), ("lm8uu_2", "rod_8mm_2"), ("t8_flange_nut", "leadscrew_T8x8"),
                    ("W11_lm8uu_traverse_carriage", "rod_8mm_1"), ("W11_lm8uu_traverse_carriage", "rod_8mm_2"),
                    ("W11_lm8uu_traverse_carriage", "leadscrew_T8x8")}
    results = []
    for angle in (-60.0, -45.0, -30.0, 0.0, 30.0, 45.0, 60.0):
        for cx in range(20, 171, 5):
            parts = build_layout(Layout(carriage_x=float(cx), guide_angle_deg=angle), new_parts, with_material=False)
            mov = [(n, s) for n, s, _, _ in parts if n in moving]
            fix = [(n, s) for n, s, _, _ in parts if n not in moving and n != "base_plywood_18mm"]
            hits = []
            for mn, ms in mov:
                mb = ms.BoundingBox()
                for fn, fs in fix:
                    if (mn, fn) in ignore_pairs:
                        continue
                    fb = fs.BoundingBox()
                    if mb.xmax < fb.xmin or fb.xmax < mb.xmin or mb.ymax < fb.ymin or fb.ymax < mb.ymin or mb.zmax < fb.zmin or fb.zmax < mb.zmin:
                        continue
                    v = ms.intersect(fs).Volume()
                    if v > 1e-3:
                        hits.append((mn, fn, round(v, 3)))
            results.append({"carriage_x": cx, "guide_angle_deg": angle, "collisions": hits})
    return results


def static_interference(new_parts):
    parts = build_layout(Layout(), new_parts, with_material=False)
    fixed = [(n, s) for n, s, _, _ in parts if n != "base_plywood_18mm"]
    allowed = {frozenset(p) for p in [("motor_rotation_shaft", "chuck_adapter_5mm"), ("motor_rotation_shaft", "mini_drill_chuck"),
                                      ("mandrel_0p8mm_steel", "mini_drill_chuck"), ("mandrel_0p8mm_steel", "guide_tube_ptfe"),
                                      ("guide_tube_ptfe", "W05_mandrel_end_guide"), ("motor_rotation_shaft", "W01_nema17_rotation_mount"),
                                      ("motor_linear_shaft", "W09_linear_motor_end_block"), ("motor_linear_shaft", "coupler_5x8"),
                                      ("coupler_5x8", "leadscrew_T8x8"), ("leadscrew_T8x8", "W10_linear_idler_end_block"),
                                      ("leadscrew_T8x8", "bearing_608ZZ"), ("bearing_608ZZ", "W10_linear_idler_end_block"),
                                      ("rod_8mm_1", "W09_linear_motor_end_block"), ("rod_8mm_2", "W09_linear_motor_end_block"),
                                      ("rod_8mm_1", "W10_linear_idler_end_block"), ("rod_8mm_2", "W10_linear_idler_end_block"),
                                      ("rod_8mm_1", "lm8uu_1"), ("rod_8mm_2", "lm8uu_2"), ("leadscrew_T8x8", "t8_flange_nut"),
                                      ("lm8uu_1", "W11_lm8uu_traverse_carriage"), ("lm8uu_2", "W11_lm8uu_traverse_carriage"),
                                      ("t8_flange_nut", "W11_lm8uu_traverse_carriage"), ("rod_8mm_1", "W11_lm8uu_traverse_carriage"),
                                      ("rod_8mm_2", "W11_lm8uu_traverse_carriage"), ("leadscrew_T8x8", "W11_lm8uu_traverse_carriage"),
                                      ("load_cell_1kg_bar", "F08_load_cell_mount"), ("load_cell_1kg_bar", "F13_load_cell_clamp_cap"), ("camera_proxy", "W18_camera_arm"),
                                      ("backlight_panel", "backlight_standoffs"),
                                      ("pot_10k", "F11_dancer_pivot_post"), ("F04_dancer_arm", "F05_dancer_roller"),
                                      ("axle_8mm", "F09_spool_stand_left_608_bore"), ("axle_8mm", "F02_spool_stand_right"),
                                      ("axle_8mm", "F10_spool_hub_1"), ("axle_8mm", "F10_spool_hub_2"), ("axle_8mm", "veneer_spool"),
                                      ("veneer_spool", "F10_spool_hub_1"), ("veneer_spool", "F10_spool_hub_2"),
                                      ("pot_10k", "F11_dancer_pivot_post"), ("pot_10k", "F04_dancer_arm"),
                                      ("sensing_rollers_MR62ZZ", "F12_sensing_roller_yoke"),
                                      ("W14_limit_switch_clamp_home", "rod_8mm_2"), ("W14_limit_switch_clamp_end", "rod_8mm_2"),
                                      ("microswitch_home", "microswitch_lever_home"), ("microswitch_end", "microswitch_lever_end")]}
    hits = []
    for i in range(len(fixed)):
        for j in range(i + 1, len(fixed)):
            (an, a), (bn, b) = fixed[i], fixed[j]
            if frozenset((an, bn)) in allowed:
                continue
            ab, bb = a.BoundingBox(), b.BoundingBox()
            if ab.xmax < bb.xmin or bb.xmax < ab.xmin or ab.ymax < bb.ymin or bb.ymax < ab.ymin or ab.zmax < bb.zmin or bb.zmax < ab.zmin:
                continue
            v = a.intersect(b).Volume()
            if v > 1e-3:
                hits.append((an, bn, round(v, 3)))
    return hits


# --------------------------------------------------------------------------- main
def main(run_checks: bool = True):
    new_parts = {}
    for stem, (fn, *_rest) in NEW_PARTS.items():
        wp = fn()
        new_parts[stem] = wp.val()
        export_part(wp, stem, "machine")

    layout = build_layout(Layout(carriage_x=60.0, guide_angle_deg=0.0), new_parts)
    glb = CAD_ROOT / "glb"
    write_glb([(n, s, c) for n, s, c, _ in layout], glb / "phase1_core_cell.glb", tol=0.08, ang=0.25,
              extras={"status": "Layout reference. CAD-checked for interference; not physically validated."})
    # Mandrel close-up for the hero/mandrel renders.
    keep = {"W01_nema17_rotation_mount", "motor_rotation_NEMA17", "motor_rotation_shaft", "chuck_adapter_5mm",
            "mini_drill_chuck", "mandrel_0p8mm_steel", "W13_w05_axis_riser_11mm", "W05_mandrel_end_guide",
            "guide_tube_ptfe", "veneer_coil_wound"}
    write_glb([(n, s, c) for n, s, c, _ in layout if n in keep], glb / "rotation_train.glb", tol=0.03, ang=0.2)

    meta = {"parameters": {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple))},
            "categories": {n: cat for n, _, _, cat in layout},
            "new_parts": {k: {"module": v[1], "qty": v[2], "material": v[3], "notes": v[4]} for k, v in NEW_PARTS.items()}}
    if run_checks:
        meta["static_interference"] = static_interference(new_parts)
        sweep = interference_report(new_parts)
        meta["traverse_sweep"] = sweep
        windows = {}
        for ang in sorted({r["guide_angle_deg"] for r in sweep}):
            free = [r["carriage_x"] for r in sweep if r["guide_angle_deg"] == ang and not r["collisions"]]
            windows[str(ang)] = [min(free), max(free)] if free else None
            # report the largest contiguous run (5 mm sampling)
            runs, cur = [], []
            for x in free:
                if cur and x - cur[-1] > 5:
                    runs.append(cur); cur = []
                cur.append(x)
            if cur:
                runs.append(cur)
            best = max(runs, key=len) if runs else None
            windows[str(ang)] = [best[0], best[-1]] if best else None
        meta["collision_free_carriage_window_mm"] = windows
    out = CAD_ROOT / "source" / "core_cell_layout.json"
    if not run_checks and out.exists():          # keep the last sweep results; mark them as carried over
        prev = json.loads(out.read_text())
        for k in ("static_interference", "traverse_sweep", "collision_free_carriage_window_mm"):
            if k in prev:
                meta[k] = prev[k]
        meta["checks_note"] = "interference results carried over from the last full run (python tools/build_cad.py)"
    out.write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return meta


if __name__ == "__main__":
    m = main(run_checks="--no-checks" not in sys.argv)
    print(json.dumps({k: m.get(k) for k in ("static_interference", "collision_free_carriage_window_mm")}, indent=1, default=str))
