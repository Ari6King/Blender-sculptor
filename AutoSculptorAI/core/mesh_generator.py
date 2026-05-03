import bpy
import bmesh
import math
from mathutils import Vector, Matrix


class MeshGenerator:
    """Generates and sculpts Blender meshes from AI-produced mesh data."""

    BASE_SHAPE_CREATORS = {
        "sphere": "_create_uv_sphere",
        "cube": "_create_cube",
        "cylinder": "_create_cylinder",
        "cone": "_create_cone",
        "torus": "_create_torus",
        "icosphere": "_create_icosphere",
        "monkey": "_create_monkey",
        "plane": "_create_plane",
    }

    def build_mesh(self, mesh_data, subdivisions=4, smooth_iterations=3, symmetry=True):
        if not mesh_data:
            return None

        name = mesh_data.get("name", "AutoSculpt_Object")
        base_shape = mesh_data.get("base_shape", "sphere").lower()
        scale = mesh_data.get("scale", [1.0, 1.0, 1.0])

        obj = self._create_base_shape(base_shape, name)
        if not obj:
            return None

        obj.scale = Vector(scale)
        bpy.ops.object.transform_apply(scale=True)

        self._apply_deformations(obj, mesh_data.get("deformations", []))
        self._apply_modifiers(obj, mesh_data.get("modifiers", []))
        self._apply_sculpt_strokes(obj, mesh_data.get("sculpt_strokes", []))
        self._apply_vertex_groups(obj, mesh_data.get("vertex_groups", []))

        if smooth_iterations > 0:
            self._smooth_mesh(obj, smooth_iterations)

        material_data = mesh_data.get("material")
        if material_data:
            self._apply_material(obj, material_data, name)

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        return obj

    def _create_base_shape(self, shape_type, name):
        bpy.ops.object.select_all(action="DESELECT")

        creator = self.BASE_SHAPE_CREATORS.get(shape_type)
        if creator:
            getattr(self, creator)()
        else:
            self._create_uv_sphere()

        obj = bpy.context.active_object
        obj.name = name
        obj.data.name = f"{name}_mesh"
        return obj

    def _create_uv_sphere(self):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0)

    def _create_cube(self):
        bpy.ops.mesh.primitive_cube_add(size=2.0)

    def _create_cylinder(self):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=2.0)

    def _create_cone(self):
        bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=1.0, depth=2.0)

    def _create_torus(self):
        bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=32)

    def _create_icosphere(self):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0)

    def _create_monkey(self):
        bpy.ops.mesh.primitive_monkey_add(size=1.0)

    def _create_plane(self):
        bpy.ops.mesh.primitive_plane_add(size=2.0)

    def _apply_deformations(self, obj, deformations):
        for deform in deformations:
            deform_type = deform.get("type", "")
            axis = deform.get("axis", "X")
            strength = deform.get("strength", 1.0)
            falloff = deform.get("falloff", 1.0)
            offset = deform.get("offset", [0.0, 0.0, 0.0])
            params = deform.get("params", {})

            if deform_type == "displace":
                self._apply_displace(obj, axis, strength, params)
            elif deform_type == "wave":
                self._apply_wave(obj, axis, strength, params)
            elif deform_type == "twist":
                self._apply_twist(obj, axis, strength)
            elif deform_type == "bend":
                self._apply_bend(obj, axis, strength)
            elif deform_type == "taper":
                self._apply_taper(obj, axis, strength)
            elif deform_type == "stretch":
                self._apply_stretch(obj, axis, strength)
            elif deform_type == "inflate":
                self._apply_inflate_deform(obj, strength)
            elif deform_type == "proportional_edit":
                self._apply_proportional_edit(obj, offset, strength, falloff)

    def _apply_displace(self, obj, axis, strength, params):
        mod = obj.modifiers.new(name="AS_Displace", type="DISPLACE")
        mod.strength = strength
        axis_map = {"X": "X", "Y": "Y", "Z": "Z"}
        mod.direction = axis_map.get(axis, "NORMAL")

        tex_type = params.get("texture_type", "CLOUDS")
        tex = bpy.data.textures.new("AS_DisplaceTex", type=tex_type)
        if hasattr(tex, "noise_scale"):
            tex.noise_scale = params.get("noise_scale", 0.5)
        mod.texture = tex

    def _apply_wave(self, obj, axis, strength, params):
        mod = obj.modifiers.new(name="AS_Wave", type="WAVE")
        mod.height = strength
        mod.width = params.get("width", 1.0)
        mod.narrowness = params.get("narrowness", 1.5)
        if axis == "X":
            mod.use_x = True
            mod.use_y = False
        elif axis == "Y":
            mod.use_x = False
            mod.use_y = True

    def _apply_twist(self, obj, axis, strength):
        mod = obj.modifiers.new(name="AS_SimpleDeform_Twist", type="SIMPLE_DEFORM")
        mod.deform_method = "TWIST"
        mod.angle = strength * math.pi
        axis_map = {"X": "X", "Y": "Y", "Z": "Z"}
        mod.deform_axis = axis_map.get(axis, "Z")

    def _apply_bend(self, obj, axis, strength):
        mod = obj.modifiers.new(name="AS_SimpleDeform_Bend", type="SIMPLE_DEFORM")
        mod.deform_method = "BEND"
        mod.angle = strength * math.pi
        axis_map = {"X": "X", "Y": "Y", "Z": "Z"}
        mod.deform_axis = axis_map.get(axis, "Z")

    def _apply_taper(self, obj, axis, strength):
        mod = obj.modifiers.new(name="AS_SimpleDeform_Taper", type="SIMPLE_DEFORM")
        mod.deform_method = "TAPER"
        mod.factor = strength
        axis_map = {"X": "X", "Y": "Y", "Z": "Z"}
        mod.deform_axis = axis_map.get(axis, "Z")

    def _apply_stretch(self, obj, axis, strength):
        mod = obj.modifiers.new(name="AS_SimpleDeform_Stretch", type="SIMPLE_DEFORM")
        mod.deform_method = "STRETCH"
        mod.factor = strength
        axis_map = {"X": "X", "Y": "Y", "Z": "Z"}
        mod.deform_axis = axis_map.get(axis, "Z")

    def _apply_inflate_deform(self, obj, strength):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        for v in bm.verts:
            v.co += v.normal * strength * 0.1
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    def _apply_proportional_edit(self, obj, offset, strength, falloff):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        center = Vector(offset)

        for v in bm.verts:
            dist = (v.co - center).length
            if dist < falloff:
                influence = (1.0 - dist / falloff) ** 2
                direction = (v.co - center).normalized()
                v.co += direction * influence * strength * 0.1

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    def _apply_modifiers(self, obj, modifiers):
        bpy.context.view_layer.objects.active = obj

        for mod_data in modifiers:
            mod_type = mod_data.get("type", "")
            params = mod_data.get("params", {})

            if mod_type == "SUBSURF":
                mod = obj.modifiers.new(name="AS_Subsurf", type="SUBSURF")
                mod.levels = params.get("levels", 2)
                mod.render_levels = params.get("render_levels", 3)
            elif mod_type == "MIRROR":
                mod = obj.modifiers.new(name="AS_Mirror", type="MIRROR")
                use_axis = params.get("use_axis", [True, False, False])
                for i, val in enumerate(use_axis[:3]):
                    mod.use_axis[i] = val
                mod.use_clip = params.get("use_clip", True)
            elif mod_type == "SOLIDIFY":
                mod = obj.modifiers.new(name="AS_Solidify", type="SOLIDIFY")
                mod.thickness = params.get("thickness", 0.02)
            elif mod_type == "BEVEL":
                mod = obj.modifiers.new(name="AS_Bevel", type="BEVEL")
                mod.width = params.get("width", 0.02)
                mod.segments = params.get("segments", 3)
            elif mod_type == "SMOOTH":
                mod = obj.modifiers.new(name="AS_Smooth", type="SMOOTH")
                mod.iterations = params.get("iterations", 5)
                mod.factor = params.get("factor", 0.5)
            elif mod_type == "DISPLACE":
                self._apply_displace(obj, params.get("axis", "Z"), params.get("strength", 0.1), params)
            elif mod_type == "DECIMATE":
                mod = obj.modifiers.new(name="AS_Decimate", type="DECIMATE")
                mod.ratio = params.get("ratio", 0.5)
            elif mod_type == "REMESH":
                mod = obj.modifiers.new(name="AS_Remesh", type="REMESH")
                mod.mode = params.get("mode", "VOXEL")
                mod.voxel_size = params.get("voxel_size", 0.05)

    def _apply_sculpt_strokes(self, obj, strokes):
        if not strokes:
            return

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        bbox = self._get_bbox(bm)
        size = max(bbox[1][i] - bbox[0][i] for i in range(3))
        if size == 0:
            size = 1.0

        for stroke in strokes:
            brush = stroke.get("brush", "draw")
            points = stroke.get("points", [])
            strength = stroke.get("strength", 0.5)
            radius = stroke.get("radius", 0.1) * size
            direction = stroke.get("direction", "add")
            sign = 1.0 if direction == "add" else -1.0

            for point in points:
                if len(point) < 3:
                    continue
                center = Vector([point[0] * size * 0.5, point[1] * size * 0.5, point[2] * size * 0.5])

                for v in bm.verts:
                    dist = (v.co - center).length
                    if dist < radius:
                        falloff = (1.0 - dist / radius) ** 2
                        self._apply_brush_effect(v, brush, center, strength * falloff * sign, radius)

            bm.normal_update()

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

    def _apply_brush_effect(self, vertex, brush, center, strength, radius):
        if brush == "draw" or brush == "clay" or brush == "clay_strips":
            vertex.co += vertex.normal * strength * 0.05
        elif brush == "inflate":
            direction = (vertex.co - center).normalized()
            vertex.co += direction * strength * 0.05
        elif brush == "grab":
            vertex.co.z += strength * 0.05
        elif brush == "smooth":
            pass
        elif brush == "crease":
            direction = (vertex.co - center).normalized()
            vertex.co -= direction * strength * 0.02
            vertex.co += vertex.normal * abs(strength) * 0.01
        elif brush == "pinch":
            direction = (vertex.co - center)
            vertex.co -= direction * strength * 0.02
        elif brush == "flatten":
            vertex.co += vertex.normal * strength * 0.01
        elif brush == "scrape":
            vertex.co -= vertex.normal * abs(strength) * 0.03
        elif brush == "snake_hook":
            vertex.co += Vector((strength * 0.03, 0, strength * 0.03))
        else:
            vertex.co += vertex.normal * strength * 0.05

    def _get_bbox(self, bm):
        if not bm.verts:
            return (Vector((0, 0, 0)), Vector((1, 1, 1)))

        min_co = Vector(bm.verts[0].co)
        max_co = Vector(bm.verts[0].co)

        for v in bm.verts:
            for i in range(3):
                min_co[i] = min(min_co[i], v.co[i])
                max_co[i] = max(max_co[i], v.co[i])

        return (min_co, max_co)

    def _apply_vertex_groups(self, obj, vertex_groups):
        if not vertex_groups:
            return

        for vg_data in vertex_groups:
            name = vg_data.get("name", "Group")
            obj.vertex_groups.new(name=name)

    def _smooth_mesh(self, obj, iterations):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        mod = obj.modifiers.new(name="AS_FinalSmooth", type="SMOOTH")
        mod.iterations = iterations
        mod.factor = 0.5
        bpy.ops.object.modifier_apply(modifier=mod.name)

    def _apply_material(self, obj, material_data, name):
        mat = bpy.data.materials.new(name=f"{name}_material")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (300, 0)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (0, 0)

        base_color = list(material_data.get("base_color", [0.8, 0.8, 0.8, 1.0]))
        if len(base_color) == 3:
            base_color.append(1.0)
        bsdf.inputs["Base Color"].default_value = base_color

        roughness = material_data.get("roughness", 0.5)
        bsdf.inputs["Roughness"].default_value = roughness

        metallic = material_data.get("metallic", 0.0)
        bsdf.inputs["Metallic"].default_value = metallic

        if "specular" in material_data:
            specular = material_data["specular"]
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = specular
            elif "Specular" in bsdf.inputs:
                bsdf.inputs["Specular"].default_value = specular

        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
