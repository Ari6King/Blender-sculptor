import bpy
from bpy.types import Panel


class AUTOSCULPT_PT_MainPanel(Panel):
    bl_label = "Auto Sculptor AI"
    bl_idname = "AUTOSCULPT_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="AI Provider", icon="WORLD")
        box.prop(scene, "autosculpt_provider", text="")

        box = layout.box()
        box.label(text="Sculpt from Prompt", icon="SCULPTMODE_HLT")
        box.prop(scene, "autosculpt_prompt", text="", icon="TEXT")
        row = box.row(align=True)
        row.scale_y = 1.5
        row.operator("autosculpt.generate", text="Generate Sculpt", icon="PLAY")
        row.operator("autosculpt.cancel", text="", icon="CANCEL")

        if scene.autosculpt_progress > 0:
            box.prop(scene, "autosculpt_progress", text="Progress", slider=True)
        if scene.autosculpt_status != "Ready":
            box.label(text=scene.autosculpt_status, icon="INFO")


class AUTOSCULPT_PT_PresetsPanel(Panel):
    bl_label = "Quick Presets"
    bl_idname = "AUTOSCULPT_PT_presets"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        presets = [
            ("Human Head", "A detailed realistic human head with facial features"),
            ("Dragon", "A fierce dragon with scales, horns, wings, and claws"),
            ("Fantasy Sword", "An ornate fantasy sword with a jeweled hilt and rune engravings"),
            ("Tree Trunk", "A gnarled old tree trunk with bark texture and roots"),
            ("Skull", "A realistic human skull with anatomical detail"),
            ("Creature", "An alien creature with organic flowing forms and tentacles"),
            ("Rock Formation", "A natural rock formation with weathered surfaces"),
            ("Armor Piece", "A medieval chest armor piece with ornamental details"),
        ]

        grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
        for name, prompt in presets:
            op = grid.operator("autosculpt.set_preset", text=name)
            op.preset_prompt = prompt


class AUTOSCULPT_PT_ReferencePanel(Panel):
    bl_label = "Reference Image"
    bl_idname = "AUTOSCULPT_PT_reference"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "autosculpt_use_reference")
        if scene.autosculpt_use_reference:
            layout.prop(scene, "autosculpt_ref_image", text="Image")
            layout.operator("autosculpt.analyze_reference", text="Analyze Reference", icon="VIEWZOOM")
            layout.separator()
            layout.label(text="The AI will analyze this image and", icon="INFO")
            layout.label(text="use it to guide the sculpting process.")


class AUTOSCULPT_PT_TexturePanel(Panel):
    bl_label = "Texture Extraction"
    bl_idname = "AUTOSCULPT_PT_texture"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "autosculpt_use_texture")
        if scene.autosculpt_use_texture:
            layout.prop(scene, "autosculpt_texture_image", text="Source Image")
            layout.operator("autosculpt.extract_texture", text="Extract & Apply Texture", icon="TEXTURE")
            layout.separator()
            layout.label(text="Extracts texture from a photo and", icon="INFO")
            layout.label(text="applies it to the active sculpt.")


class AUTOSCULPT_PT_SettingsPanel(Panel):
    bl_label = "Sculpting Settings"
    bl_idname = "AUTOSCULPT_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "autosculpt_detail_level")
        layout.prop(scene, "autosculpt_subdivisions")
        layout.prop(scene, "autosculpt_smooth_iterations")
        layout.prop(scene, "autosculpt_symmetry")


class AUTOSCULPT_PT_KnowledgePanel(Panel):
    bl_label = "Knowledge Base"
    bl_idname = "AUTOSCULPT_PT_knowledge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "autosculpt_scrape_knowledge")

        row = layout.row(align=True)
        row.operator("autosculpt.scrape_knowledge", text="Build Knowledge Base", icon="URL")
        row.operator("autosculpt.clear_knowledge", text="", icon="TRASH")

        layout.separator()
        layout.label(text="Scrapes Blender docs and tutorials", icon="INFO")
        layout.label(text="to improve AI sculpting quality.")


class AUTOSCULPT_PT_ToolsPanel(Panel):
    bl_label = "Tools"
    bl_idname = "AUTOSCULPT_PT_tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Sculptor AI"
    bl_parent_id = "AUTOSCULPT_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        layout.operator("autosculpt.remesh", text="Remesh Active", icon="MOD_REMESH")
        layout.operator("autosculpt.smooth_sculpt", text="Smooth Active", icon="MOD_SMOOTH")
        layout.operator("autosculpt.apply_symmetry", text="Apply Symmetry", icon="MOD_MIRROR")
        layout.operator("autosculpt.export_model", text="Export Model", icon="EXPORT")
        layout.separator()
        layout.operator("autosculpt.clear_generated", text="Clear Generated", icon="TRASH")


classes = (
    AUTOSCULPT_PT_MainPanel,
    AUTOSCULPT_PT_PresetsPanel,
    AUTOSCULPT_PT_ReferencePanel,
    AUTOSCULPT_PT_TexturePanel,
    AUTOSCULPT_PT_SettingsPanel,
    AUTOSCULPT_PT_KnowledgePanel,
    AUTOSCULPT_PT_ToolsPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
