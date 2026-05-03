import bpy
import bmesh
import os
import json
import math
from mathutils import Vector

from .ai_client import AIClient


class TextureEngine:
    """Extracts textures from images and applies them to Blender meshes."""

    def __init__(self, config):
        self.config = config
        self.ai_client = AIClient(config) if config.get("api_key") or config.get("provider") == "OLLAMA" else None

    def extract_and_apply(self, obj, image_path):
        if not obj or obj.type != "MESH":
            return False

        if not image_path or not os.path.isfile(image_path):
            return False

        self._ensure_uv_map(obj)

        mat = self._create_textured_material(obj, image_path)
        if not mat:
            return False

        if self.ai_client:
            self._enhance_material_with_ai(mat, image_path)

        return True

    def _ensure_uv_map(self, obj):
        if not obj.data.uv_layers:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
            bpy.ops.object.mode_set(mode="OBJECT")

    def _create_textured_material(self, obj, image_path):
        mat_name = f"{obj.name}_texture_material"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (300, 0)

        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.location = (0, 0)

        try:
            img = bpy.data.images.load(image_path)
            tex_image.image = img
        except Exception as e:
            print(f"Auto Sculptor AI: Failed to load texture image: {e}")
            return None

        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-400, 0)

        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-200, 0)

        links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex_image.inputs["Vector"])
        links.new(tex_image.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        bump = nodes.new("ShaderNodeBump")
        bump.location = (100, -200)
        bump.inputs["Strength"].default_value = 0.3

        tex_image_bump = nodes.new("ShaderNodeTexImage")
        tex_image_bump.location = (-100, -200)
        tex_image_bump.image = img

        color_ramp = nodes.new("ShaderNodeValToRGB")
        color_ramp.location = (0, -400)

        rgb_to_bw = nodes.new("ShaderNodeRGBToBW")
        rgb_to_bw.location = (-100, -400)

        links.new(tex_image_bump.outputs["Color"], rgb_to_bw.inputs["Color"])
        links.new(rgb_to_bw.outputs["Val"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        links.new(tex_coord.outputs["UV"], tex_image_bump.inputs["Vector"])

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        return mat

    def _enhance_material_with_ai(self, mat, image_path):
        try:
            analysis_text = self.ai_client.analyze_texture(image_path)
            if not analysis_text:
                return

            text = analysis_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]

            analysis = json.loads(text)

            bsdf = None
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    bsdf = node
                    break

            if not bsdf:
                return

            if "roughness" in analysis:
                bsdf.inputs["Roughness"].default_value = float(analysis["roughness"])

            if "metallic" in analysis:
                bsdf.inputs["Metallic"].default_value = float(analysis["metallic"])

            if "specular" in analysis:
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = float(analysis["specular"])
                elif "Specular" in bsdf.inputs:
                    bsdf.inputs["Specular"].default_value = float(analysis["specular"])

            if "normal_strength" in analysis:
                for node in mat.node_tree.nodes:
                    if node.type == "BUMP":
                        node.inputs["Strength"].default_value = float(analysis["normal_strength"])
                        break

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Auto Sculptor AI: Material enhancement error: {e}")

    def apply_projection_texture(self, obj, image_path, projection="BOX"):
        if not obj or obj.type != "MESH":
            return False

        mat_name = f"{obj.name}_projected_texture"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (400, 0)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (200, 0)

        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.location = (0, 0)
        tex_image.projection = projection.upper()

        try:
            img = bpy.data.images.load(image_path)
            tex_image.image = img
        except Exception:
            return False

        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-200, 0)

        if projection.upper() == "BOX":
            links.new(tex_coord.outputs["Object"], tex_image.inputs["Vector"])
        else:
            links.new(tex_coord.outputs["UV"], tex_image.inputs["Vector"])

        links.new(tex_image.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        return True
