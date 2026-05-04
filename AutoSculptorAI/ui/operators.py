import bpy
import os
import threading
from bpy.types import Operator
from bpy.props import StringProperty, FloatProperty


class AUTOSCULPT_OT_Generate(Operator):
    bl_idname = "autosculpt.generate"
    bl_label = "Generate Sculpt"
    bl_description = "Generate a 3D sculpt from the text prompt and optional reference image"
    bl_options = {"REGISTER", "UNDO"}

    _timer = None
    _thread = None
    _result = None
    _error = None
    _running = False
    _generation_id = 0

    @classmethod
    def poll(cls, context):
        return (
            context.scene.autosculpt_prompt.strip() != ""
            and not cls._running
        )

    def execute(self, context):
        scene = context.scene
        prompt = scene.autosculpt_prompt.strip()

        if not prompt:
            self.report({"WARNING"}, "Please enter a prompt")
            return {"CANCELLED"}

        prefs = context.preferences.addons.get("AutoSculptorAI")
        if not prefs:
            self.report({"ERROR"}, "Addon preferences not found")
            return {"CANCELLED"}

        provider = scene.autosculpt_provider
        prefs_data = prefs.preferences

        if provider == "OPENAI" and not prefs_data.openai_api_key:
            self.report({"ERROR"}, "OpenAI API key not set. Check addon preferences.")
            return {"CANCELLED"}
        elif provider == "ANTHROPIC" and not prefs_data.anthropic_api_key:
            self.report({"ERROR"}, "Anthropic API key not set. Check addon preferences.")
            return {"CANCELLED"}

        scene.autosculpt_status = "Initializing..."
        scene.autosculpt_progress = 0.0
        AUTOSCULPT_OT_Generate._result = None
        AUTOSCULPT_OT_Generate._error = None
        AUTOSCULPT_OT_Generate._generation_id += 1
        AUTOSCULPT_OT_Generate._running = True

        try:
            ref_image_path = None
            if scene.autosculpt_use_reference and scene.autosculpt_ref_image:
                ref_image_path = bpy.path.abspath(scene.autosculpt_ref_image)
                if not os.path.isfile(ref_image_path):
                    self.report({"WARNING"}, "Reference image not found, proceeding without it")
                    ref_image_path = None

            from ..core.sculpt_engine import SculptEngine

            config = {
                "provider": provider,
                "prompt": prompt,
                "detail_level": scene.autosculpt_detail_level,
                "subdivisions": scene.autosculpt_subdivisions,
                "smooth_iterations": scene.autosculpt_smooth_iterations,
                "symmetry": scene.autosculpt_symmetry,
                "ref_image_path": ref_image_path,
                "use_knowledge": scene.autosculpt_scrape_knowledge,
                "knowledge_db_path": bpy.path.abspath(prefs_data.knowledge_db_path) if prefs_data.knowledge_db_path else None,
            }

            if provider == "OPENAI":
                config["api_key"] = prefs_data.openai_api_key
                config["model"] = prefs_data.openai_model
            elif provider == "ANTHROPIC":
                config["api_key"] = prefs_data.anthropic_api_key
                config["model"] = prefs_data.anthropic_model
            elif provider == "OLLAMA":
                config["ollama_url"] = prefs_data.ollama_url
                config["model"] = prefs_data.ollama_model

            engine = SculptEngine(config)

            gen_id = AUTOSCULPT_OT_Generate._generation_id

            def run_generation():
                try:
                    result = engine.generate()
                    if AUTOSCULPT_OT_Generate._generation_id == gen_id:
                        AUTOSCULPT_OT_Generate._result = result
                except Exception as e:
                    if AUTOSCULPT_OT_Generate._generation_id == gen_id:
                        AUTOSCULPT_OT_Generate._error = str(e)

            AUTOSCULPT_OT_Generate._thread = threading.Thread(target=run_generation)
            AUTOSCULPT_OT_Generate._thread.start()

            self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
            context.window_manager.modal_handler_add(self)
            return {"RUNNING_MODAL"}

        except Exception as e:
            AUTOSCULPT_OT_Generate._running = False
            scene.autosculpt_status = f"Error: {e}"
            scene.autosculpt_progress = 0.0
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        if not AUTOSCULPT_OT_Generate._running:
            context.window_manager.event_timer_remove(self._timer)
            AUTOSCULPT_OT_Generate._thread = None
            AUTOSCULPT_OT_Generate._result = None
            AUTOSCULPT_OT_Generate._error = None
            return {"CANCELLED"}

        scene = context.scene

        if AUTOSCULPT_OT_Generate._error:
            error = AUTOSCULPT_OT_Generate._error
            AUTOSCULPT_OT_Generate._error = None
            AUTOSCULPT_OT_Generate._running = False
            scene.autosculpt_status = f"Error: {error}"
            scene.autosculpt_progress = 0.0
            context.window_manager.event_timer_remove(self._timer)
            self.report({"ERROR"}, error)
            return {"CANCELLED"}

        if AUTOSCULPT_OT_Generate._thread and not AUTOSCULPT_OT_Generate._thread.is_alive():
            AUTOSCULPT_OT_Generate._running = False
            context.window_manager.event_timer_remove(self._timer)

            result = AUTOSCULPT_OT_Generate._result
            AUTOSCULPT_OT_Generate._result = None

            if result and result.get("success"):
                from ..core.mesh_generator import MeshGenerator

                generator = MeshGenerator()
                mesh_data = result.get("mesh_data", {})
                obj = generator.build_mesh(
                    mesh_data,
                    subdivisions=scene.autosculpt_subdivisions,
                    smooth_iterations=scene.autosculpt_smooth_iterations,
                    symmetry=scene.autosculpt_symmetry,
                )

                if obj:
                    obj["autosculpt_generated"] = True
                    obj["autosculpt_prompt"] = scene.autosculpt_prompt

                    scene.autosculpt_status = "Generation complete!"
                    scene.autosculpt_progress = 100.0
                    self.report({"INFO"}, f"Sculpt generated: {obj.name}")

                    if scene.autosculpt_use_texture and scene.autosculpt_texture_image:
                        from ..core.texture_engine import TextureEngine

                        tex_config = {
                            "provider": scene.autosculpt_provider,
                            "api_key": result.get("api_key", ""),
                            "model": result.get("model", ""),
                        }
                        if scene.autosculpt_provider == "OLLAMA":
                            prefs = context.preferences.addons.get("AutoSculptorAI")
                            if prefs:
                                tex_config["ollama_url"] = prefs.preferences.ollama_url
                        tex_engine = TextureEngine(tex_config)
                        tex_path = bpy.path.abspath(scene.autosculpt_texture_image)
                        if os.path.isfile(tex_path):
                            tex_engine.extract_and_apply(obj, tex_path)
                            self.report({"INFO"}, "Texture applied successfully")

                    return {"FINISHED"}
                else:
                    scene.autosculpt_status = "Failed to build mesh"
                    self.report({"ERROR"}, "Failed to build mesh from AI response")
                    return {"CANCELLED"}
            else:
                error_msg = result.get("error", "Unknown error") if result else "No result"
                scene.autosculpt_status = f"Failed: {error_msg}"
                self.report({"ERROR"}, error_msg)
                return {"CANCELLED"}

        return {"PASS_THROUGH"}


class AUTOSCULPT_OT_Cancel(Operator):
    bl_idname = "autosculpt.cancel"
    bl_label = "Cancel Generation"
    bl_description = "Cancel the current generation"

    def execute(self, context):
        AUTOSCULPT_OT_Generate._running = False
        context.scene.autosculpt_status = "Cancelled"
        context.scene.autosculpt_progress = 0.0
        self.report({"INFO"}, "Generation cancelled")
        return {"FINISHED"}


class AUTOSCULPT_OT_SetPreset(Operator):
    bl_idname = "autosculpt.set_preset"
    bl_label = "Set Preset"
    bl_description = "Load a preset prompt"

    preset_prompt: StringProperty()

    def execute(self, context):
        context.scene.autosculpt_prompt = self.preset_prompt
        return {"FINISHED"}


class AUTOSCULPT_OT_AnalyzeReference(Operator):
    bl_idname = "autosculpt.analyze_reference"
    bl_label = "Analyze Reference"
    bl_description = "Analyze the reference image using AI vision"
    bl_options = {"REGISTER"}

    def execute(self, context):
        scene = context.scene
        ref_path = bpy.path.abspath(scene.autosculpt_ref_image)

        if not ref_path or not os.path.isfile(ref_path):
            self.report({"ERROR"}, "Reference image file not found")
            return {"CANCELLED"}

        prefs = context.preferences.addons.get("AutoSculptorAI")
        if not prefs:
            self.report({"ERROR"}, "Addon preferences not found")
            return {"CANCELLED"}

        provider = scene.autosculpt_provider
        prefs_data = prefs.preferences

        config = {"provider": provider}
        if provider == "OPENAI":
            config["api_key"] = prefs_data.openai_api_key
            config["model"] = prefs_data.openai_model
        elif provider == "ANTHROPIC":
            config["api_key"] = prefs_data.anthropic_api_key
            config["model"] = prefs_data.anthropic_model
        elif provider == "OLLAMA":
            config["ollama_url"] = prefs_data.ollama_url
            config["model"] = prefs_data.ollama_model

        from ..core.reference_analyzer import ReferenceAnalyzer

        analyzer = ReferenceAnalyzer(config)
        analysis = analyzer.analyze(ref_path)

        if analysis:
            if scene.autosculpt_prompt:
                scene.autosculpt_prompt += f"\n\n[Reference Analysis]: {analysis}"
            else:
                scene.autosculpt_prompt = analysis
            self.report({"INFO"}, "Reference image analyzed and prompt updated")
        else:
            self.report({"WARNING"}, "Could not analyze reference image")

        return {"FINISHED"}


class AUTOSCULPT_OT_ExtractTexture(Operator):
    bl_idname = "autosculpt.extract_texture"
    bl_label = "Extract & Apply Texture"
    bl_description = "Extract texture from an image and apply it to the active object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "No active mesh object selected")
            return {"CANCELLED"}

        tex_path = bpy.path.abspath(scene.autosculpt_texture_image)
        if not tex_path or not os.path.isfile(tex_path):
            self.report({"ERROR"}, "Texture source image not found")
            return {"CANCELLED"}

        prefs = context.preferences.addons.get("AutoSculptorAI")
        if not prefs:
            self.report({"ERROR"}, "Addon preferences not found")
            return {"CANCELLED"}

        provider = scene.autosculpt_provider
        prefs_data = prefs.preferences
        config = {"provider": provider}

        if provider == "OPENAI":
            config["api_key"] = prefs_data.openai_api_key
            config["model"] = prefs_data.openai_model
        elif provider == "ANTHROPIC":
            config["api_key"] = prefs_data.anthropic_api_key
            config["model"] = prefs_data.anthropic_model
        elif provider == "OLLAMA":
            config["ollama_url"] = prefs_data.ollama_url
            config["model"] = prefs_data.ollama_model

        from ..core.texture_engine import TextureEngine

        engine = TextureEngine(config)
        success = engine.extract_and_apply(obj, tex_path)

        if success:
            self.report({"INFO"}, "Texture extracted and applied successfully")
        else:
            self.report({"WARNING"}, "Texture application completed with warnings")

        return {"FINISHED"}


class AUTOSCULPT_OT_ScrapeKnowledge(Operator):
    bl_idname = "autosculpt.scrape_knowledge"
    bl_label = "Build Knowledge Base"
    bl_description = "Scrape Blender documentation and tutorials to build AI knowledge"
    bl_options = {"REGISTER"}

    _timer = None
    _thread = None
    _done = False
    _error = None
    _running = False

    @classmethod
    def poll(cls, context):
        return not cls._running

    def execute(self, context):
        prefs = context.preferences.addons.get("AutoSculptorAI")
        if not prefs:
            self.report({"ERROR"}, "Addon preferences not found")
            return {"CANCELLED"}

        prefs_data = prefs.preferences
        db_path = bpy.path.abspath(prefs_data.knowledge_db_path) if prefs_data.knowledge_db_path else None
        max_pages = prefs_data.max_scrape_pages
        scrape_youtube = prefs_data.scrape_youtube
        youtube_queries = None
        if prefs_data.youtube_search_query.strip():
            youtube_queries = [q.strip() for q in prefs_data.youtube_search_query.split(",") if q.strip()]

        from ..knowledge.scraper import BlenderKnowledgeScraper

        scraper_inst = BlenderKnowledgeScraper(
            db_path=db_path,
            max_pages=max_pages,
            scrape_youtube=scrape_youtube,
            youtube_queries=youtube_queries,
        )

        context.scene.autosculpt_status = "Building knowledge base..."

        def run_scrape():
            try:
                scraper_inst.scrape_all()
                AUTOSCULPT_OT_ScrapeKnowledge._done = True
            except Exception as e:
                AUTOSCULPT_OT_ScrapeKnowledge._error = str(e)

        AUTOSCULPT_OT_ScrapeKnowledge._done = False
        AUTOSCULPT_OT_ScrapeKnowledge._error = None
        AUTOSCULPT_OT_ScrapeKnowledge._running = True
        AUTOSCULPT_OT_ScrapeKnowledge._thread = threading.Thread(target=run_scrape)
        AUTOSCULPT_OT_ScrapeKnowledge._thread.start()

        self._timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        if AUTOSCULPT_OT_ScrapeKnowledge._error:
            error = AUTOSCULPT_OT_ScrapeKnowledge._error
            AUTOSCULPT_OT_ScrapeKnowledge._error = None
            AUTOSCULPT_OT_ScrapeKnowledge._running = False
            context.scene.autosculpt_status = f"Scrape error: {error}"
            context.window_manager.event_timer_remove(self._timer)
            self.report({"ERROR"}, error)
            return {"CANCELLED"}

        if AUTOSCULPT_OT_ScrapeKnowledge._done:
            AUTOSCULPT_OT_ScrapeKnowledge._running = False
            context.scene.autosculpt_status = "Knowledge base built successfully!"
            context.window_manager.event_timer_remove(self._timer)
            self.report({"INFO"}, "Knowledge base built successfully")
            return {"FINISHED"}

        return {"PASS_THROUGH"}


class AUTOSCULPT_OT_ClearKnowledge(Operator):
    bl_idname = "autosculpt.clear_knowledge"
    bl_label = "Clear Knowledge Base"
    bl_description = "Clear the scraped knowledge database"
    bl_options = {"REGISTER"}

    def execute(self, context):
        from ..knowledge.knowledge_base import KnowledgeBase

        prefs = context.preferences.addons.get("AutoSculptorAI")
        db_path = None
        if prefs:
            db_path = bpy.path.abspath(prefs.preferences.knowledge_db_path) if prefs.preferences.knowledge_db_path else None

        kb = KnowledgeBase(db_path=db_path)
        kb.clear()
        self.report({"INFO"}, "Knowledge base cleared")
        return {"FINISHED"}


class AUTOSCULPT_OT_Remesh(Operator):
    bl_idname = "autosculpt.remesh"
    bl_label = "Remesh Active"
    bl_description = "Apply voxel remesh to the active object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "No active mesh object")
            return {"CANCELLED"}

        mod = obj.modifiers.new(name="AutoSculpt_Remesh", type="REMESH")
        mod.mode = "VOXEL"
        mod.voxel_size = 0.05
        bpy.ops.object.modifier_apply(modifier=mod.name)
        self.report({"INFO"}, "Remesh applied")
        return {"FINISHED"}


class AUTOSCULPT_OT_SmoothSculpt(Operator):
    bl_idname = "autosculpt.smooth_sculpt"
    bl_label = "Smooth Active"
    bl_description = "Apply smooth modifier to the active object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "No active mesh object")
            return {"CANCELLED"}

        mod = obj.modifiers.new(name="AutoSculpt_Smooth", type="SMOOTH")
        mod.iterations = context.scene.autosculpt_smooth_iterations
        bpy.ops.object.modifier_apply(modifier=mod.name)
        self.report({"INFO"}, "Smoothing applied")
        return {"FINISHED"}


class AUTOSCULPT_OT_ApplySymmetry(Operator):
    bl_idname = "autosculpt.apply_symmetry"
    bl_label = "Apply Symmetry"
    bl_description = "Apply mirror modifier for symmetry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "No active mesh object")
            return {"CANCELLED"}

        mod = obj.modifiers.new(name="AutoSculpt_Mirror", type="MIRROR")
        mod.use_axis[0] = True
        mod.use_clip = True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        self.report({"INFO"}, "Symmetry applied")
        return {"FINISHED"}


class AUTOSCULPT_OT_ExportModel(Operator):
    bl_idname = "autosculpt.export_model"
    bl_label = "Export Model"
    bl_description = "Export the active model as FBX/OBJ"
    bl_options = {"REGISTER"}

    filepath: StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, "No active mesh object")
            return {"CANCELLED"}

        filepath = self.filepath
        if not filepath:
            self.report({"ERROR"}, "No file path specified")
            return {"CANCELLED"}

        if filepath.lower().endswith(".fbx"):
            bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True)
        elif filepath.lower().endswith(".obj"):
            bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=True)
        elif filepath.lower().endswith(".glb") or filepath.lower().endswith(".gltf"):
            bpy.ops.export_scene.gltf(filepath=filepath, use_selection=True)
        else:
            filepath += ".fbx"
            bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True)

        self.report({"INFO"}, f"Model exported to {filepath}")
        return {"FINISHED"}


class AUTOSCULPT_OT_ClearGenerated(Operator):
    bl_idname = "autosculpt.clear_generated"
    bl_label = "Clear Generated Objects"
    bl_description = "Remove all Auto Sculptor generated objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        removed = 0
        for obj in list(bpy.data.objects):
            if obj.get("autosculpt_generated"):
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1

        context.scene.autosculpt_status = "Ready"
        context.scene.autosculpt_progress = 0.0
        self.report({"INFO"}, f"Removed {removed} generated objects")
        return {"FINISHED"}


classes = (
    AUTOSCULPT_OT_Generate,
    AUTOSCULPT_OT_Cancel,
    AUTOSCULPT_OT_SetPreset,
    AUTOSCULPT_OT_AnalyzeReference,
    AUTOSCULPT_OT_ExtractTexture,
    AUTOSCULPT_OT_ScrapeKnowledge,
    AUTOSCULPT_OT_ClearKnowledge,
    AUTOSCULPT_OT_Remesh,
    AUTOSCULPT_OT_SmoothSculpt,
    AUTOSCULPT_OT_ApplySymmetry,
    AUTOSCULPT_OT_ExportModel,
    AUTOSCULPT_OT_ClearGenerated,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
