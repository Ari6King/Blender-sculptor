# Auto Sculptor AI — Blender Addon

An AI-powered Blender addon that sculpts 3D models from text prompts, learns professional sculpting techniques by scraping Blender documentation, accepts reference images for shape guidance, and extracts textures from photos to apply onto generated models.

## Features

- **Prompt-Based Sculpting** — Describe any 3D model in natural language and the AI generates a fully sculpted mesh using Blender's bmesh API with deformations, sculpt strokes, modifiers, and materials
- **Reference Image Support** — Upload a reference photo and the AI Vision API analyzes it to extract shape, proportions, surface details, and symmetry information to guide the sculpting process
- **Texture Extraction** — Extract textures from any photo and automatically apply them to your sculpted model with proper UV mapping, bump mapping, and AI-analyzed material properties (roughness, metallic, specular)
- **Knowledge Base / Web Scraping** — Scrapes Blender's official documentation, API references, and tutorial sites to build a local knowledge base of professional sculpting techniques that the AI uses to produce better results
- **Multiple AI Providers** — Supports OpenAI (GPT-4/GPT-4o), Anthropic (Claude 3), and local Ollama models
- **Quick Presets** — One-click presets for Human Head, Dragon, Fantasy Sword, Tree Trunk, Skull, Creature, Rock Formation, and Armor Piece
- **Detail Levels** — Low, Medium, High, and Ultra detail settings that control subdivision depth, stroke density, and mesh complexity
- **Sculpting Tools** — Built-in Remesh, Smooth, Mirror/Symmetry, and Export (FBX/OBJ/glTF) tools
- **Non-Destructive Workflow** — All generated objects are tagged and can be cleared before regeneration
- **Symmetry Support** — Automatic X-axis mirror modifier for symmetric sculpts
- **Material Generation** — AI-generated Principled BSDF materials with physically accurate base color, roughness, metallic, and specular values
- **Async Generation** — Threaded AI calls with progress tracking so Blender stays responsive

## Requirements

- **Blender 3.6+** (tested on 3.6, 4.0, 4.1)
- **Python 3.10+** (bundled with Blender)
- **API Key** from one of:
  - [OpenAI](https://platform.openai.com/api-keys) (GPT-4o recommended for vision features)
  - [Anthropic](https://console.anthropic.com/) (Claude 3 Sonnet/Opus)
  - [Ollama](https://ollama.ai/) running locally (free, no API key needed)

No additional Python packages are required — the addon uses only Blender's built-in Python and standard library modules (`urllib`, `json`, `ssl`, `html`, etc.).

## Installation

1. Download or clone this repository
2. Copy the entire `AutoSculptorAI` folder into your Blender addons directory:

   **Windows:**
   ```
   %APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\AutoSculptorAI\
   ```

   **macOS:**
   ```
   ~/Library/Application Support/Blender/<version>/scripts/addons/AutoSculptorAI/
   ```

   **Linux:**
   ```
   ~/.config/blender/<version>/scripts/addons/AutoSculptorAI/
   ```

3. Open Blender and go to **Edit → Preferences → Add-ons**
4. Search for **"Auto Sculptor AI"** and enable it
5. Click the arrow to expand preferences and enter your API key

Alternatively, install via **Edit → Preferences → Add-ons → Install...** and select a zipped version of the `AutoSculptorAI` folder.

## Quick Start

### 1. Configure API Key
- Open **Edit → Preferences → Add-ons**
- Find **Auto Sculptor AI** and expand it
- Enter your OpenAI API key (starts with `sk-...`)
- Select your preferred model (GPT-4o recommended)

### 2. Open the Panel
- In the 3D Viewport, press **N** to open the sidebar
- Click the **Auto Sculptor AI** tab

### 3. Generate a Sculpt
- Type a description in the prompt field (e.g., "A fierce dragon with scales and horns")
- Or click a **Quick Preset** button
- Click **Generate Sculpt**
- Watch the progress bar as your model is built

### 4. Use Reference Images (Optional)
- Expand the **Reference Image** section
- Enable **Use Reference Image** and select an image file
- Click **Analyze Reference** to have the AI analyze the image
- The analysis is appended to your prompt for guided sculpting

### 5. Apply Textures (Optional)
- Expand the **Texture Extraction** section
- Enable **Extract Texture** and select a source photo
- Click **Extract & Apply Texture** on any mesh object
- The addon creates UV maps, applies the image as a texture, and uses AI to set material properties

### 6. Build Knowledge Base (Optional)
- Expand the **Knowledge Base** section
- Click **Build Knowledge Base** to scrape Blender documentation
- This improves the AI's sculpting output by providing professional techniques as context

## Example Prompts

```
A detailed realistic human head with defined cheekbones, a strong jaw,
pronounced brow ridge, and subtle skin surface detail
```

```
A fierce dragon head with layered scales, curved horns, sharp teeth,
and menacing eye sockets
```

```
An ornate fantasy sword with a cross-guard shaped like dragon wings,
a leather-wrapped grip, and rune engravings on the blade
```

```
A gnarled ancient tree trunk with deep bark crevices, exposed roots,
and a hollow opening in the side
```

```
Medieval chest armor with overlapping plates, riveted edges,
an engraved crest, and leather straps
```

## Architecture

```
AutoSculptorAI/
├── __init__.py              # Addon entry point and registration
├── preferences.py           # Addon preferences (API keys, settings)
├── README.md
├── ui/
│   ├── __init__.py
│   ├── panels.py            # Sidebar UI panels
│   └── operators.py         # Blender operators (generate, texture, scrape, tools)
├── core/
│   ├── __init__.py
│   ├── ai_client.py         # Unified AI client (OpenAI, Anthropic, Ollama)
│   ├── sculpt_engine.py     # Orchestrates AI sculpting pipeline
│   ├── mesh_generator.py    # Builds meshes from AI instructions using bmesh
│   ├── texture_engine.py    # Texture extraction and material creation
│   └── reference_analyzer.py # Reference image analysis via Vision API
├── knowledge/
│   ├── __init__.py
│   ├── scraper.py           # Web scraper for Blender docs/tutorials
│   └── knowledge_base.py    # Local JSON knowledge storage and retrieval
└── utils/
    ├── __init__.py
    └── helpers.py            # Math and file utility functions
```

## How It Works

### Sculpting Pipeline
1. **Prompt Enhancement** — Your text prompt is enriched with detail-level hints and symmetry instructions
2. **Knowledge Retrieval** — If enabled, relevant sculpting techniques are retrieved from the local knowledge base
3. **AI Generation** — The prompt (+ reference analysis + knowledge context) is sent to the AI, which returns a structured JSON with base shape, deformations, sculpt strokes, modifiers, and material data
4. **Mesh Building** — The `MeshGenerator` creates the base shape, applies deformations via Blender modifiers and bmesh vertex manipulation, simulates sculpt brush strokes, and sets up materials
5. **Post-Processing** — Smoothing passes and optional texture application

### Reference Image Analysis
The AI Vision API analyzes uploaded reference images and extracts:
- Overall shape and silhouette
- Key structural features and proportions
- Surface details and textures
- Symmetry patterns
- Suggested base shape for sculpting

### Texture Extraction
1. Smart UV projection is applied to the mesh
2. The source image is loaded as a texture node
3. A full Principled BSDF material is created with image texture, bump mapping, and UV coordinates
4. The AI analyzes the image to determine roughness, metallic, specular, and normal strength values

### Knowledge Base
The scraper collects information from:
- Blender official documentation (sculpting, modifiers, shader nodes, bmesh API)
- Blender tutorial sites
- Built-in professional sculpting techniques (base mesh selection, subdivision workflow, brush techniques, retopology, etc.)

All knowledge is stored as a local JSON file and retrieved via keyword matching against your prompts.

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| AI Provider | OpenAI, Anthropic, or Ollama | OpenAI |
| Detail Level | Low / Medium / High / Ultra | Medium |
| Subdivisions | Mesh subdivision levels (1-8) | 4 |
| Smooth Iterations | Post-sculpt smoothing passes (0-20) | 3 |
| Symmetry | Enable X-axis mirror | On |
| Use Reference | Enable reference image input | Off |
| Extract Texture | Enable texture extraction | Off |
| Build Knowledge | Enable knowledge base for generation | Off |

## License

MIT License — see the repository root for details.
