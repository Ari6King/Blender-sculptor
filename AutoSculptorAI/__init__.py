bl_info = {
    "name": "Auto Sculptor AI",
    "author": "Auto Sculptor AI Team",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > Auto Sculptor AI",
    "description": "AI-powered sculpting from text prompts and reference images with texture extraction",
    "category": "Sculpting",
}

import bpy
import importlib
import sys
import os

addon_dir = os.path.dirname(os.path.realpath(__file__))
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

from . import preferences
from .ui import panels, operators
from .core import ai_client, sculpt_engine, mesh_generator, texture_engine, reference_analyzer
from .knowledge import scraper, knowledge_base


modules = [
    preferences,
    ai_client,
    sculpt_engine,
    mesh_generator,
    texture_engine,
    reference_analyzer,
    scraper,
    knowledge_base,
    operators,
    panels,
]


def register():
    for mod in modules:
        importlib.reload(mod)

    preferences.register()
    operators.register()
    panels.register()

    bpy.types.Scene.autosculpt_prompt = bpy.props.StringProperty(
        name="Prompt",
        description="Describe the 3D model you want to sculpt",
        default="",
        maxlen=2048,
    )
    bpy.types.Scene.autosculpt_ref_image = bpy.props.StringProperty(
        name="Reference Image",
        description="Path to a reference image",
        default="",
        subtype="FILE_PATH",
    )
    bpy.types.Scene.autosculpt_texture_image = bpy.props.StringProperty(
        name="Texture Image",
        description="Path to an image to extract texture from",
        default="",
        subtype="FILE_PATH",
    )
    bpy.types.Scene.autosculpt_detail_level = bpy.props.EnumProperty(
        name="Detail Level",
        description="Level of sculpting detail",
        items=[
            ("LOW", "Low", "Fast generation with basic shapes"),
            ("MEDIUM", "Medium", "Balanced detail and speed"),
            ("HIGH", "High", "Maximum detail (slower)"),
            ("ULTRA", "Ultra", "Ultra-high detail (slowest)"),
        ],
        default="MEDIUM",
    )
    bpy.types.Scene.autosculpt_symmetry = bpy.props.BoolProperty(
        name="Symmetry",
        description="Enable symmetrical sculpting",
        default=True,
    )
    bpy.types.Scene.autosculpt_smooth_iterations = bpy.props.IntProperty(
        name="Smooth Iterations",
        description="Number of smoothing passes after sculpting",
        default=3,
        min=0,
        max=20,
    )
    bpy.types.Scene.autosculpt_subdivisions = bpy.props.IntProperty(
        name="Subdivisions",
        description="Number of subdivision levels for the mesh",
        default=4,
        min=1,
        max=8,
    )
    bpy.types.Scene.autosculpt_use_reference = bpy.props.BoolProperty(
        name="Use Reference Image",
        description="Use an uploaded reference image to guide sculpting",
        default=False,
    )
    bpy.types.Scene.autosculpt_use_texture = bpy.props.BoolProperty(
        name="Extract Texture",
        description="Extract and apply texture from an image",
        default=False,
    )
    bpy.types.Scene.autosculpt_progress = bpy.props.FloatProperty(
        name="Progress",
        description="Current generation progress",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE",
    )
    bpy.types.Scene.autosculpt_status = bpy.props.StringProperty(
        name="Status",
        description="Current status message",
        default="Ready",
    )
    bpy.types.Scene.autosculpt_provider = bpy.props.EnumProperty(
        name="AI Provider",
        description="AI service provider to use",
        items=[
            ("OPENAI", "OpenAI", "Use OpenAI GPT-4 and Vision API"),
            ("ANTHROPIC", "Anthropic", "Use Anthropic Claude"),
            ("OLLAMA", "Ollama (Local)", "Use local Ollama models"),
        ],
        default="OPENAI",
    )
    bpy.types.Scene.autosculpt_scrape_knowledge = bpy.props.BoolProperty(
        name="Build Knowledge Base",
        description="Scrape Blender docs and tutorials to improve AI sculpting",
        default=False,
    )

    print("Auto Sculptor AI: Registered successfully")


def unregister():
    panels.unregister()
    operators.unregister()
    preferences.unregister()

    props = [
        "autosculpt_prompt",
        "autosculpt_ref_image",
        "autosculpt_texture_image",
        "autosculpt_detail_level",
        "autosculpt_symmetry",
        "autosculpt_smooth_iterations",
        "autosculpt_subdivisions",
        "autosculpt_use_reference",
        "autosculpt_use_texture",
        "autosculpt_progress",
        "autosculpt_status",
        "autosculpt_provider",
        "autosculpt_scrape_knowledge",
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)

    print("Auto Sculptor AI: Unregistered successfully")


if __name__ == "__main__":
    register()
