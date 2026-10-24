"""Original native Blender scene: orbital sculpture, procedural nodes, studio lights."""
import bpy
from mathutils import Vector


def material(name, color, metallic=0, roughness=.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def build_scene(ctx):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    # Leave cores available for browser/FFmpeg and the host while rendering.
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.world = bpy.data.worlds.new("Deep ink studio")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.025, .045, .085, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = .45
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    aqua = material("Aqua enamel", (.12, .65, .60), .55, .24)
    coral = material("Coral ceramic", (.95, .20, .10), .15, .28)
    paper = material("Warm ivory", (.80, .72, .55), .2, .33)
    ink = material("Ink pedestal", (.022, .035, .055), .1, .4)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(.55, 0, .4))
    root = bpy.context.object
    root.name = "Editable orbital choreography"
    for index in range(3):
        bpy.ops.mesh.primitive_torus_add(major_segments=72, minor_segments=12, location=(0, 0, 0),
                                       major_radius=1.1 + index * .34, minor_radius=.07)
        torus = bpy.context.object
        torus.name = f"Orbit {index + 1}"
        torus.parent = root
        torus.rotation_euler = (.6 + index * .5, index * .5, .2)
        torus.data.materials.append([aqua, paper, aqua][index])
        for poly in torus.data.polygons:
            poly.use_smooth = True
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=.43, location=(0, 0, 0))
    core = bpy.context.object
    core.name = "Coral core"
    core.parent = root
    core.data.materials.append(coral)
    for poly in core.data.polygons:
        poly.use_smooth = True
    # Native Geometry Nodes distributes small beads on a curve circle.
    bpy.ops.mesh.primitive_cube_add(size=.1)
    beads = bpy.context.object
    beads.name = "Geometry Nodes orbital beads"
    beads.parent = root
    node_group = bpy.data.node_groups.new("Editable orbital bead generator", "GeometryNodeTree")
    node_group.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    node_group.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    output = node_group.nodes.new("NodeGroupOutput")
    circle = node_group.nodes.new("GeometryNodeCurvePrimitiveCircle")
    circle.inputs["Resolution"].default_value = 12
    circle.inputs["Radius"].default_value = 1.85
    ico = node_group.nodes.new("GeometryNodeMeshIcoSphere")
    ico.inputs["Radius"].default_value = .075
    ico.inputs["Subdivisions"].default_value = 2
    set_mat = node_group.nodes.new("GeometryNodeSetMaterial")
    set_mat.inputs["Material"].default_value = coral
    instances = node_group.nodes.new("GeometryNodeInstanceOnPoints")
    node_group.links.new(ico.outputs["Mesh"], set_mat.inputs["Geometry"])
    node_group.links.new(circle.outputs["Curve"], instances.inputs["Points"])
    node_group.links.new(set_mat.outputs["Geometry"], instances.inputs["Instance"])
    node_group.links.new(instances.outputs["Instances"], output.inputs["Geometry"])
    beads.modifiers.new("Procedural beads", "NODES").node_group = node_group
    beads.rotation_euler = (.5, .3, .1)
    root.rotation_euler = (.15, -.35, -.2)
    root.keyframe_insert(data_path="rotation_euler", frame=0)
    root.rotation_euler = (.35, .4, .5)
    root.keyframe_insert(data_path="rotation_euler", frame=ctx["duration_frames"] - 1)
    for curve in root.animation_data.action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -1.8))
    bpy.context.object.data.materials.append(ink)
    for location, power, color, size in [((-3, -4, 6), 850, (1, .87, .66), 5),
                                          ((4, 1, 4), 1100, (.35, 1, .9), 4),
                                          ((0, 4, 2), 650, (1, .3, .15), 3)]:
        bpy.ops.object.light_add(type="AREA", location=location)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.color, lamp.data.shape, lamp.data.size = power, color, "DISK", size
        lamp.rotation_euler = (Vector((0, 0, 0)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(location=(5.8, -8.7, 4.7))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, .1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 7.3
    scene.camera = camera
    # Native editable 3D text with Blender's bundled Bfont, no external font asset.
    text_material = bpy.data.materials.new("Camera typography ivory")
    text_material.use_nodes = True
    nodes = text_material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (.88, .79, .62, 1)
    emission.inputs["Strength"].default_value = 1
    text_material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    for title, y in [("06 / CRAFT IN EVERY DIMENSION", 1.67),
                     ("BLENDER / CINEMATIC 3D + GEOMETRY NODES", -1.75)]:
        bpy.ops.object.text_add()
        text = bpy.context.object
        text.name = "Editable camera typography / " + title
        text.parent = camera
        text.location = (-3.25, y, -6)
        text.rotation_euler = (0, 0, 0)
        text.data.body, text.data.size = title, .12
        text.data.materials.append(text_material)
