import os, math, json, csv, shutil, zipfile
from pathlib import Path
import cadquery as cq
from cadquery import exporters
import trimesh
import numpy as np

SRC = Path('/mnt/data/SeedForge_R1_LowCost')
OUT = Path('/mnt/data/SeedForge_R2_LowCost_PaperReference')
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(SRC, OUT)
ref = OUT/'cad'/'paper_reference'
for sub in ['step','stl','3mf','source']:
    (ref/sub).mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def export_shape(shape, stem, note=None):
    sp = ref/'step'/f'{stem}.step'
    st = ref/'stl'/f'{stem}.stl'
    exporters.export(shape, str(sp))
    exporters.export(shape, str(st), tolerance=0.06, angularTolerance=0.15)
    mesh = trimesh.load_mesh(st, process=False)
    if isinstance(mesh, trimesh.Scene): mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    data = mesh.export(file_type='3mf')
    (ref/'3mf'/f'{stem}.3mf').write_bytes(data)
    return {'stem':stem,'step':str(sp),'stl':str(st),'3mf':str(ref/'3mf'/f'{stem}.3mf'),'note':note or ''}

def export_assembly(components, stem, colors=None):
    # components list of (name, cq.Workplane/Shape)
    assy = cq.Assembly(name=stem)
    colors = colors or {}
    for name,obj in components:
        col = colors.get(name)
        assy.add(obj, name=name, color=col)
    assy.save(str(ref/'step'/f'{stem}.step'))
    # compound STL
    solids=[]
    for _,obj in components:
        vals=obj.vals() if hasattr(obj,'vals') else [obj]
        solids.extend(vals)
    comp = cq.Compound.makeCompound(solids)
    exporters.export(comp, str(ref/'stl'/f'{stem}.stl'), tolerance=0.06, angularTolerance=0.15)
    # colored 3MF scene
    scene=trimesh.Scene()
    palette={
        'body':[184,134,78,255], 'tail1':[188,132,74,255], 'tail2':[205,154,87,255], 'tail3':[166,112,62,255],
        'tip':[208,180,124,255], 'seed':[100,63,40,255], 'hair_envelope':[120,100,80,90],
        'mandrel':[170,175,180,255], 'chuck':[70,75,80,255], 'stop':[90,95,100,255]
    }
    for name,obj in components:
        tmp = ref/'stl'/f'__tmp_{stem}_{name}.stl'
        exporters.export(obj, str(tmp), tolerance=0.06, angularTolerance=0.15)
        m=trimesh.load_mesh(tmp,process=False)
        if isinstance(m,trimesh.Scene): m=trimesh.util.concatenate(tuple(m.geometry.values()))
        try: m.visual.face_colors = palette.get(name,[160,160,160,255])
        except Exception: pass
        scene.add_geometry(m, node_name=name, geom_name=name)
        tmp.unlink(missing_ok=True)
    (ref/'3mf'/f'{stem}.3mf').write_bytes(scene.export(file_type='3mf'))
    return stem

def helix_ribbon(mandrel_d=0.8, thickness=0.5, width=2.5, turns=7, axial_length=35.0, z0=0):
    pitch=axial_length/turns
    r=mandrel_d/2 + thickness/2
    helix=cq.Wire.makeHelix(pitch, axial_length, r)
    # translate helix in Z if required
    if z0: helix=helix.translate(cq.Vector(0,0,z0))
    normal=cq.Vector(0,2*math.pi*r,pitch).normalized()
    xdir=cq.Vector(1,0,0)
    plane=cq.Plane(origin=(r,0,z0),xDir=xdir,normal=normal)
    return cq.Workplane(plane).rect(thickness,width).sweep(helix,isFrenet=True)

def spiral_tail(phi_deg, target_length, width=2.5, thickness=0.5, z0=35.0, sweep_deg=205, rise=7.0, drop=7.0, r0=1.3):
    phi=math.radians(phi_deg); sweep=math.radians(sweep_deg); n=100
    def pts(rend):
        arr=[]
        for i in range(n+1):
            u=i/n
            th=phi+sweep*u
            r=r0+(rend-r0)*(u**0.82)
            z=z0 + rise*math.sin(math.pi*u) - drop*(u**1.15)
            arr.append((r*math.cos(th),r*math.sin(th),z))
        return arr
    def plen(a): return sum(math.dist(x,y) for x,y in zip(a,a[1:]))
    lo,hi=1.5,80.0
    for _ in range(70):
        mid=(lo+hi)/2
        if plen(pts(mid))<target_length: lo=mid
        else: hi=mid
    arr=pts((lo+hi)/2)
    tangent=cq.Vector(*(arr[1][j]-arr[0][j] for j in range(3))).normalized()
    xdir=cq.Vector(0,0,1).cross(tangent)
    if xdir.Length<1e-8: xdir=cq.Vector(1,0,0)
    xdir=xdir.normalized()
    plane=cq.Plane(origin=arr[0],xDir=xdir,normal=tangent)
    edge=cq.Edge.makeSpline([cq.Vector(*p) for p in arr])
    wire=cq.Wire.assembleEdges([edge])
    return cq.Workplane(plane).rect(width,thickness).sweep(wire,isFrenet=True), arr

def teardrop_tip(length=14.0, max_d=5.5, neck_d=2.4, z_top=0.4):
    # axis Z: point at -length, neck at z_top
    zs=[-length, -0.78*length, -0.45*length, -0.12*length, z_top]
    ds=[0.6, 2.8, max_d, max_d*0.72, neck_d]
    wires=[]
    for z,d in zip(zs,ds):
        wires.append(cq.Workplane('XY', origin=(0,0,z)).circle(d/2).wire().val())
    solid=cq.Solid.makeLoft(wires, ruled=False)
    return cq.Workplane(obj=solid)

def ellipsoid(rx,ry,rz, center=(0,0,0)):
    # scaled sphere via OCC transform is awkward; approximate by lofted ellipses
    cx,cy,cz=center
    zs=[-rz,-0.7*rz,0,0.7*rz,rz]
    scales=[0.05,0.72,1.0,0.72,0.05]
    wires=[]
    for z,s in zip(zs,scales):
        wp=cq.Workplane('XY', origin=(cx,cy,cz+z)).ellipse(rx*s,ry*s).wire().val()
        wires.append(wp)
    return cq.Workplane(obj=cq.Solid.makeLoft(wires,ruled=False))

def cylinder_rod(d=0.8,L=100):
    return cq.Workplane('XY').circle(d/2).extrude(L)

# ---------- paper standard reference ----------
std = dict(mandrel_d=0.8, thickness=0.5, width=2.5, turns=7, axial_length=35.0)
body = helix_ribbon(**std)
t1,_=spiral_tail(0,27.0,std['width'],std['thickness'],std['axial_length'])
t2,_=spiral_tail(120,29.5,std['width'],std['thickness'],std['axial_length'])
t3,_=spiral_tail(240,32.5,std['width'],std['thickness'],std['axial_length'])
tip = teardrop_tip(14,5.5,2.4,0.5)
seed = ellipsoid(1.8,1.25,2.4,(0,0,-6.0))
# Hair clearance envelope as a slightly enlarged tip shell, reference only
hair_env = teardrop_tip(16.0,9.2,4.0,0.7)

paper_parts=[]
for stem,shape,note in [
    ('PR01_standard_7coil_body_2p5x0p5_on_0p8',body,'Paper-reference body: 7 turns over 35 mm axial body length; 2.5 x 0.5 mm ribbon; 0.8 mm mandrel.'),
    ('PR02_standard_tail1_27mm',t1,'Tail 1 path length 27 mm; 2.5 x 0.5 mm.'),
    ('PR03_standard_tail2_29p5mm',t2,'Tail 2 path length 29.5 mm; 2.5 x 0.5 mm.'),
    ('PR04_standard_tail3_32p5mm',t3,'Tail 3 path length 32.5 mm; 2.5 x 0.5 mm.'),
    ('PR05_standard_tip_outer_reference',tip,'Tip outer envelope for assembly/fixture design. Outer geometry is an engineering approximation from paper figures, not original author CAD.'),
    ('PR06_standard_seed_payload_envelope',seed,'Small seed payload envelope for fixture visualization; not a biological seed replica.'),
    ('PR07_tip_hair_clearance_envelope',hair_env,'Clearance envelope representing flocked tip fibers; do not print as the production tip.'),
]:
    paper_parts.append(export_shape(shape,stem,note))

colors={'body':cq.Color(0.72,0.50,0.27),'tail1':cq.Color(0.75,0.48,0.25),'tail2':cq.Color(0.82,0.58,0.31),'tail3':cq.Color(0.65,0.40,0.20),'tip':cq.Color(0.82,0.68,0.42),'seed':cq.Color(0.35,0.18,0.08)}
export_assembly([('body',body),('tail1',t1),('tail2',t2),('tail3',t3),('tip',tip),('seed',seed)],'PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1',colors)

# exploded assembly: translate tails/tip for visual and fixture planning
exploded=[('body',body),
          ('tail1',t1.translate((26,0,8))),('tail2',t2.translate((-14,24,8))),('tail3',t3.translate((-14,-24,8))),
          ('tip',tip.translate((0,0,-22))),('seed',seed.translate((12,0,-22)))]
export_assembly(exploded,'PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1',colors)

# Flat stock references from supplementary simulation dimensions
blank_primary=cq.Workplane('XY').box(48.0,2.5,0.5,centered=(False,True,False))
blank_t2=cq.Workplane('XY').box(29.5,2.5,0.5,centered=(False,True,False))
blank_t3=cq.Workplane('XY').box(32.5,2.5,0.5,centered=(False,True,False))
for stem,shape,note in [
    ('PR10_primary_blank_48x2p5x0p5_reference',blank_primary,'Flat primary body/tail strip reference from supplementary simulation setup.'),
    ('PR11_aux_tail_blank_29p5x2p5x0p5_reference',blank_t2,'Flat auxiliary tail blank reference.'),
    ('PR12_aux_tail_blank_32p5x2p5x0p5_reference',blank_t3,'Flat auxiliary tail blank reference.'),
]: paper_parts.append(export_shape(shape,stem,note))

# ---------- mandrels and low-cost machine adapter ----------
mandrel08=cylinder_rod(0.8,100)
mandrel3=cylinder_rod(3.0,140)
# Split collet insert: 5 mm OD, 12 mm length, 0.9 mm bore, 0.7 mm split
collet=(cq.Workplane('XY').circle(2.5).circle(0.45).extrude(12)
        .cut(cq.Workplane('XZ').box(0.7,12,3.0,centered=(True,False,True)).translate((0,0,6))))
# Depth stop collar with M2 cross-hole
stop_base=cq.Workplane('XY').circle(4).circle(0.5).extrude(5)
stop_hole=cq.Workplane('YZ', origin=(0,0,2.5)).circle(1.1).extrude(10,both=True)
stop=stop_base.cut(stop_hole)
# Protective guide bushing with 1.0 mm bore
bushing=cq.Workplane('XY').circle(4).circle(0.5).extrude(10)
for stem,shape,note in [
    ('MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE',mandrel08,'ACTUAL PART SHOULD BE METAL, not FDM printed. Cut 0.8 mm straight stainless/spring-steel rod to 100 mm.'),
    ('MR02_0p8mm_to_5mm_split_collet_INSERT',collet,'Prototype printed collet insert for 0.8 mm rod; final machine is better with a small metal pin-vise/drill chuck.'),
    ('MR03_mandrel_depth_stop_M2',stop,'Depth stop collar; M2 cross-hole. Ream 1.0 mm bore after printing.'),
    ('MR04_0p8mm_guide_bushing',bushing,'Guide bushing reference; print in PETG/nylon and ream, or substitute PTFE/brass tube.'),
    ('MR05_3mm_x140mm_LARGE_PINE_MANDREL_REFERENCE',mandrel3,'Optional large whitebark-pine carrier mandrel reference; actual part should be metal.'),
]: paper_parts.append(export_shape(shape,stem,note))

# Mandrel subassembly with rod + generic 5mm chuck sleeve + stop (for fit planning)
# generic chuck body reference, not printable interface claim
chuck = (cq.Workplane('XY').circle(6).extrude(18).translate((0,0,-18))
         .union(cq.Workplane('XY').circle(3).extrude(8).translate((0,0,-26))))
mandrel_assy = mandrel08.translate((0,0,-2))
stop_assy = stop.translate((0,0,56))
export_assembly([('mandrel',mandrel_assy),('chuck',chuck),('stop',stop_assy)],'MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE',
                {'mandrel':cq.Color(0.75,0.78,0.82),'chuck':cq.Color(0.25,0.27,0.30),'stop':cq.Color(0.45,0.47,0.50)})

# ---------- large whitebark pine carrier body reference ----------
large_body=helix_ribbon(mandrel_d=3.0,thickness=0.8,width=12.0,turns=7,axial_length=85.0)
pine_seed=ellipsoid(4.5,2.8,5.5,(0,0,-10)) # 11 mm length envelope
large_tip=teardrop_tip(28,14,5.5,1.0)
for stem,shape,note in [
    ('PR20_LARGE_PINE_7COIL_BODY_12x0p8_on_3mm',large_body,'Paper-reported large carrier body: 12 mm width, 0.8 mm thickness, 3 mm mandrel, 7 coils, 85 mm body length.'),
    ('PR21_whitebark_pine_seed_11mm_ENVELOPE',pine_seed,'11 mm length seed clearance envelope based on the paper; not a botanical CAD replica.'),
    ('PR22_large_pine_tip_outer_ENVELOPE',large_tip,'Engineering tip envelope for large seed fixture design; exact author tip geometry unavailable.'),
]: paper_parts.append(export_shape(shape,stem,note))
# body + tip + seed only; tails intentionally absent because exact large-tail geometry is not provided
export_assembly([('body',large_body),('tip',large_tip),('seed',pine_seed)],'PR23_LARGE_PINE_BODY_TIP_SEED_REFERENCE_NO_TAILS',colors)

# 4x visual demonstration model of standard finished seed (not dimensional fixture reference)
def scaled_obj(obj, factor):
    # use OCC transform matrix via val().transformGeometry
    tr=cq.Matrix(); tr._wrapped.SetValues(factor,0,0,0, 0,factor,0,0, 0,0,factor,0)
    vals=[v.transformGeometry(tr) for v in obj.vals()]
    return cq.Workplane(obj=cq.Compound.makeCompound(vals) if len(vals)>1 else vals[0])
try:
    demo_components=[(n,scaled_obj(o,4.0)) for n,o in [('body',body),('tail1',t1),('tail2',t2),('tail3',t3),('tip',tip)]]
    export_assembly(demo_components,'PR24_STANDARD_FINISHED_CARRIER_4X_DEMO_PRINT',colors)
except Exception as e:
    print('4x demo generation skipped',e)

# ---------- metadata / docs ----------
params={
 'paper_standard_reference':{
   'tails':3,'coil_layers':1,'coil_turns':7,'coil_axial_length_mm':35.0,'mandrel_diameter_mm':0.8,
   'ribbon_width_mm':2.5,'ribbon_thickness_mm':0.5,'tail_path_lengths_mm':[27.0,29.5,32.5],
   'resting_angle_paper_deg_range':[25,30],
   'notes':'Width/thickness/tail dimensions come from the paper/preprint supplementary simulation; the published protocol notes many standard three-tail samples used ~0.4 mm veneer, so 0.5 mm is retained here to match the EECS149 machine specification and the simulation geometry.'
 },
 'large_whitebark_pine_reference':{
   'tails':3,'coil_layers':1,'coil_turns':7,'coil_axial_length_mm':85.0,'mandrel_diameter_mm':3.0,
   'ribbon_width_mm':12.0,'ribbon_thickness_mm':0.8,'flat_veneer_length_mm':300.0,'seed_length_mm':11.0,
   'notes':'Exact large-tail lengths and exact tip mold geometry were not provided in the accessible article text, so PR23 omits the tails rather than inventing them.'
 },
 'ee149_machine':{'existing_project_strip_width_mm':4.0,'existing_project_strip_thickness_mm':0.5,'existing_project_mandrel_diameter_mm':0.8,'requested_angle_deg':45}
}
(ref/'paper_reference_parameters.json').write_text(json.dumps(params,indent=2))

readme=f'''# SeedForge R2 - Nature paper reference CAD additions\n\nThese files extend the R1 low-cost manufacturing package with dimensional reference models for the **forming mandrel** and the **fully assembled three-tailed seed carrier**.\n\n## Most important files\n- `step/MR01_0p8mm_x100mm_FORMING_MANDREL_REFERENCE.step` - exact 0.8 mm x 100 mm rod envelope. **Use a metal rod; do not print this as the working mandrel.**\n- `step/MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE.step` - fit-planning assembly for rod/chuck/stop.\n- `step/PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1.step` - assembled 1:1 carrier reference.\n- `step/PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1.step` - exploded view for assembly-station design.\n- `step/PR24_STANDARD_FINISHED_CARRIER_4X_DEMO_PRINT.step` - enlarged demonstration/inspection model if generated.\n- `step/PR20_LARGE_PINE_7COIL_BODY_12x0p8_on_3mm.step` - large whitebark-pine carrier body reference.\n- `step/PR21_whitebark_pine_seed_11mm_ENVELOPE.step` - 11 mm payload clearance reference.\n\nEach reference model is also supplied as STL and 3MF. STEP is the preferred format for CAD/fixture work.\n\n## Source-grounded dimensions used\n**Standard 3-tail reference:** 3 tails, 1 coil layer, 7 coils, 35 mm body length; 0.8 mm mandrel; 2.5 mm tail/body width and 0.5 mm thickness in the supplementary simulation; tail strip/path lengths 27, 29.5 and 32.5 mm; favorable landing/resting angle about 25-30 degrees.\n\n**Large whitebark-pine reference:** 12 mm wide, 0.8 mm thick, 300 mm-long wood veneer; 3 mm mandrel; 7-coil/85 mm body design; seed payload up to about 11 mm length.\n\n## What is exact vs approximate\n- Mandrel diameter, coil counts, body-length identifiers, standard tail widths/thicknesses and supplementary tail lengths are source-grounded.\n- The detailed 3D free-shape of the dry tails and the flour-based tip surface are **engineering approximations** reconstructed from published figures because the authors' original Rhino/Supplementary File 3 geometry is not publicly supplied in the accessible text.\n- `PR05`, `PR07`, `PR22`, and the spline curvature of PR02-PR04 are therefore for **machine clearance, cassette design and visualization**, not claims of author-identical geometry.\n- The actual carrier should be wood/dough/fiber material as described by the paper, not FDM plastic.\n\n## Machine integration\nFor the EECS149 winder, use the 0.8 mm metal mandrel with a miniature metal pin-vise/drill chuck or a precision collet. The printed MR02 insert is a low-cost prototype only. The winder should keep the guide angle and axial pitch adjustable: the course project's 4 mm-wide/45-degree/no-gap specification is not the same geometry as the paper-reference 2.5 mm/7-coil/35 mm carrier.\n'''
(ref/'README_PAPER_REFERENCE_MODELS.md').write_text(readme)

# Save generator itself into package
shutil.copy('/mnt/data/build_seedforge_r2.py', ref/'source'/'generate_paper_reference_models.py')

# Append BOM rows
bom=OUT/'bom'/'SeedForge_R1_BOM.csv'
rows=list(csv.DictReader(bom.open()))
fieldnames=rows[0].keys()
add=[
 {'module':'M2 winder','qty':'5','item':'0.8 mm precision straight stainless/spring-steel rod','specification':'0.8 mm diameter; cut to ~100 mm working mandrels','status':'buy','target_unit_cost_usd':'1.5','target_total_usd':'7.5','notes':'Working mandrel corresponding to paper geometry. Buy metal rod; MR01 is CAD reference only.'},
 {'module':'M2 winder','qty':'1','item':'miniature drill chuck / pin-vise shaft adapter','specification':'grip range including 0.8 mm; shaft compatible with NEMA coupler','status':'buy','target_unit_cost_usd':'8.0','target_total_usd':'8.0','notes':'Preferred over relying on a printed 0.8 mm collet.'},
 {'module':'M2 winder','qty':'1','item':'PTFE or brass guide tube','specification':'~1.0 mm ID; short low-friction mandrel support sleeve','status':'buy','target_unit_cost_usd':'4.0','target_total_usd':'4.0','notes':'Supports the 0.8 mm rod without using a printed surface directly.'},
 {'module':'Paper large-carrier option','qty':'2','item':'3 mm smooth stainless rod','specification':'3 mm diameter x 140 mm or longer','status':'optional','target_unit_cost_usd':'4.0','target_total_usd':'8.0','notes':'Only for large whitebark-pine carrier experiments; MR05 is CAD reference.'},
]
rows.extend(add)
newbom=OUT/'bom'/'SeedForge_R2_BOM.csv'
with newbom.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)

# reference manifest
manifest=[]
for p in sorted((ref/'step').glob('*.step')):
    stem=p.stem
    stl=ref/'stl'/f'{stem}.stl'
    size=''
    try:
      m=trimesh.load_mesh(stl,process=False)
      if isinstance(m,trimesh.Scene): m=trimesh.util.concatenate(tuple(m.geometry.values()))
      ext=m.bounds[1]-m.bounds[0]
      size=' x '.join(f'{v:.2f}' for v in ext)
    except: pass
    manifest.append({'name':stem,'bbox_mm':size,'step':p.name,'stl':stl.name,'3mf':f'{stem}.3mf'})
with (ref/'reference_manifest.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['name','bbox_mm','step','stl','3mf']); w.writeheader(); w.writerows(manifest)

# QA all new STLs
qa=[]
for stl in sorted((ref/'stl').glob('*.stl')):
    m=trimesh.load_mesh(stl,process=False)
    if isinstance(m,trimesh.Scene):
        meshes=list(m.geometry.values()); wat=all(x.is_watertight for x in meshes); ncomp=len(meshes); bounds=np.vstack([x.bounds for x in meshes])
        ext=bounds.max(0)-bounds.min(0)
    else:
        wat=m.is_watertight; ncomp=len(m.split(only_watertight=False)); ext=m.bounds[1]-m.bounds[0]
    qa.append((stl.name,wat,ncomp,ext.tolist()))
with (ref/'QA_reference_models.txt').open('w') as f:
    for name,wat,ncomp,ext in qa: f.write(f'{name}: watertight={wat}, components={ncomp}, bbox_mm={[round(x,3) for x in ext]}\n')

# ---------- render previews using trimesh + matplotlib ----------
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

def render_scene(stl_path, outpng, title, elev=22, azim=35, max_faces=18000):
    loaded=trimesh.load(stl_path,force='scene',process=False)
    geoms=list(loaded.geometry.values()) if isinstance(loaded,trimesh.Scene) else [loaded]
    fig=plt.figure(figsize=(10,7),dpi=170)
    ax=fig.add_subplot(111,projection='3d')
    allv=[]
    cols=['#b7834f','#c8965e','#d3aa73','#a96f3c','#d6bf8d','#6f4e37','#a8acb1']
    for gi,g in enumerate(geoms):
        if len(g.faces)>max_faces:
            try: g=g.simplify_quadric_decimation(max_faces)
            except: pass
        v=g.vertices; faces=g.faces
        allv.append(v)
        poly=Poly3DCollection(v[faces],alpha=1.0,linewidths=0.08)
        poly.set_facecolor(cols[gi%len(cols)]); poly.set_edgecolor((0.18,0.18,0.18,0.16))
        ax.add_collection3d(poly)
    vv=np.vstack(allv); mn=vv.min(0); mx=vv.max(0); ctr=(mn+mx)/2; span=max(mx-mn)*0.62
    ax.set_xlim(ctr[0]-span,ctr[0]+span); ax.set_ylim(ctr[1]-span,ctr[1]+span); ax.set_zlim(ctr[2]-span,ctr[2]+span)
    ax.set_box_aspect((1,1,1)); ax.view_init(elev=elev,azim=azim); ax.set_axis_off()
    ax.set_title(title,fontsize=16,fontweight='bold',pad=16)
    fig.text(0.5,0.035,'Actual generated CAD preview • dimensions in packaged STEP/3MF models',ha='center',fontsize=9)
    fig.tight_layout()
    fig.savefig(outpng,bbox_inches='tight',facecolor='white'); plt.close(fig)

render_scene(ref/'stl'/'PR08_STANDARD_FINISHED_3TAIL_SEED_CARRIER_1TO1.stl', OUT/'previews'/'PAPER_STANDARD_FINISHED_SEED_ACTUAL_CAD.png','Nature-paper reference: finished three-tailed carrier (1:1)',25,40)
render_scene(ref/'stl'/'MR06_COMPLETE_0p8mm_MANDREL_SUBASSEMBLY_REFERENCE.stl', OUT/'previews'/'MANDREL_SUBASSEMBLY_ACTUAL_CAD.png','0.8 mm forming mandrel subassembly (CAD reference)',18,30)
render_scene(ref/'stl'/'PR09_STANDARD_SEED_CARRIER_EXPLODED_1TO1.stl', OUT/'previews'/'PAPER_STANDARD_EXPLODED_ACTUAL_CAD.png','Nature-paper reference carrier: exploded assembly',25,35)
render_scene(ref/'stl'/'PR23_LARGE_PINE_BODY_TIP_SEED_REFERENCE_NO_TAILS.stl', OUT/'previews'/'LARGE_PINE_BODY_REFERENCE_ACTUAL_CAD.png','Large whitebark-pine carrier: source-grounded body + payload envelope',18,35)

# package-level README
(OUT/'README_R2_ADDITIONS.md').write_text('''# SeedForge R2 low-cost package\n\nR2 retains every R1 low-cost factory/drone file and adds `cad/paper_reference/` with mandrel, flat blanks, the fully assembled standard three-tail carrier, exploded assembly, and the large whitebark-pine body/payload reference. See `cad/paper_reference/README_PAPER_REFERENCE_MODELS.md` first.\n''')

# zip complete and reference-only
for zpath,base,paths in [
    (Path('/mnt/data/SeedForge_R2_LowCost_PaperReference_COMPLETE.zip'),OUT,[OUT]),
    (Path('/mnt/data/SeedForge_R2_PaperReference_CAD_ONLY.zip'),ref,[ref]),
]:
    if zpath.exists(): zpath.unlink()
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for rootpath in paths:
            for p in rootpath.rglob('*'):
                if p.is_file(): z.write(p,p.relative_to(rootpath.parent))

print('OUT',OUT)
print('reference step files',len(list((ref/'step').glob('*.step'))))
print('zip complete MB',Path('/mnt/data/SeedForge_R2_LowCost_PaperReference_COMPLETE.zip').stat().st_size/1e6)
