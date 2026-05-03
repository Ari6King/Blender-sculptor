import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, EnumProperty, IntProperty, BoolProperty


class AutoSculptorPreferences(AddonPreferences):
    bl_idname = "AutoSculptorAI"

    openai_api_key: StringProperty(
        name="OpenAI API Key",
        description="Your OpenAI API key (starts with sk-...)",
        default="",
        subtype="PASSWORD",
    )

    anthropic_api_key: StringProperty(
        name="Anthropic API Key",
        description="Your Anthropic API key",
        default="",
        subtype="PASSWORD",
    )

    ollama_url: StringProperty(
        name="Ollama URL",
        description="URL for local Ollama server",
        default="http://localhost:11434",
    )

    ollama_model: StringProperty(
        name="Ollama Model",
        description="Model name for Ollama",
        default="llama3",
    )

    openai_model: EnumProperty(
        name="OpenAI Model",
        description="OpenAI model to use for generation",
        items=[
            ("gpt-4", "GPT-4", "Most capable model"),
            ("gpt-4o", "GPT-4o", "Fast and capable multimodal model"),
            ("gpt-4o-mini", "GPT-4o Mini", "Fast and cost-effective"),
            ("gpt-4-turbo", "GPT-4 Turbo", "Fast GPT-4 variant"),
        ],
        default="gpt-4o",
    )

    anthropic_model: EnumProperty(
        name="Anthropic Model",
        description="Anthropic model to use",
        items=[
            ("claude-3-opus-20240229", "Claude 3 Opus", "Most capable"),
            ("claude-3-sonnet-20240229", "Claude 3 Sonnet", "Balanced"),
            ("claude-3-haiku-20240307", "Claude 3 Haiku", "Fastest"),
        ],
        default="claude-3-sonnet-20240229",
    )

    knowledge_db_path: StringProperty(
        name="Knowledge DB Path",
        description="Path to store the scraped knowledge database",
        default="",
        subtype="DIR_PATH",
    )

    max_scrape_pages: IntProperty(
        name="Max Scrape Pages",
        description="Maximum number of pages to scrape for knowledge",
        default=50,
        min=5,
        max=500,
    )

    auto_update_knowledge: BoolProperty(
        name="Auto-Update Knowledge",
        description="Automatically update knowledge base periodically",
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="OpenAI Settings", icon="WORLD")
        box.prop(self, "openai_api_key")
        box.prop(self, "openai_model")

        box = layout.box()
        box.label(text="Anthropic Settings", icon="WORLD")
        box.prop(self, "anthropic_api_key")
        box.prop(self, "anthropic_model")

        box = layout.box()
        box.label(text="Ollama Settings (Local)", icon="DESKTOP")
        box.prop(self, "ollama_url")
        box.prop(self, "ollama_model")

        box = layout.box()
        box.label(text="Knowledge Base", icon="FILE_FOLDER")
        box.prop(self, "knowledge_db_path")
        box.prop(self, "max_scrape_pages")
        box.prop(self, "auto_update_knowledge")


classes = (AutoSculptorPreferences,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
