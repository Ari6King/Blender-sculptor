import urllib.request
import urllib.error
import urllib.parse
import json
import re
import os
import ssl
import html
from html.parser import HTMLParser
from .knowledge_base import KnowledgeBase


class _HTMLTextExtractor(HTMLParser):
    """Extracts visible text content from HTML."""

    def __init__(self):
        super().__init__()
        self._result = []
        self._skip_tags = {"script", "style", "noscript", "svg", "path"}
        self._current_skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag):
        if tag in self._skip_tags and self._current_skip > 0:
            self._current_skip -= 1

    def handle_data(self, data):
        if self._current_skip == 0:
            text = data.strip()
            if text:
                self._result.append(text)

    def get_text(self):
        return " ".join(self._result)


class BlenderKnowledgeScraper:
    """Scrapes Blender documentation, tutorials, YouTube videos, and sculpting guides to build a knowledge base."""

    YOUTUBE_SEARCH_QUERIES = [
        "blender sculpting tutorial beginner",
        "blender sculpt character head",
        "blender sculpt organic forms",
        "blender sculpting techniques professional",
        "blender hard surface sculpting",
        "blender creature sculpt workflow",
        "blender texture painting sculpt",
        "blender bmesh python scripting",
    ]

    BLENDER_DOCS_URLS = [
        "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/index.html",
        "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/tools/index.html",
        "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/tool_settings/brush_settings.html",
        "https://docs.blender.org/manual/en/latest/modeling/meshes/editing/mesh/index.html",
        "https://docs.blender.org/manual/en/latest/modeling/modifiers/index.html",
        "https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/index.html",
        "https://docs.blender.org/manual/en/latest/render/shader_nodes/index.html",
        "https://docs.blender.org/manual/en/latest/sculpt_paint/texture_paint/index.html",
        "https://docs.blender.org/api/current/bmesh.html",
        "https://docs.blender.org/api/current/bpy.ops.sculpt.html",
        "https://docs.blender.org/api/current/bpy.ops.mesh.html",
    ]

    TUTORIAL_SOURCES = [
        {
            "url": "https://www.blenderguru.com/tutorials",
            "name": "Blender Guru",
            "category": "tutorials",
        },
        {
            "url": "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/introduction.html",
            "name": "Blender Manual - Sculpt Intro",
            "category": "documentation",
        },
        {
            "url": "https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/adaptive.html",
            "name": "Blender Manual - Adaptive Sculpting",
            "category": "documentation",
        },
        {
            "url": "https://wiki.blender.org/wiki/Reference/Release_Notes",
            "name": "Blender Release Notes",
            "category": "reference",
        },
    ]

    SCULPTING_KNOWLEDGE = [
        {
            "topic": "Base Mesh Selection",
            "content": (
                "Choosing the right base mesh is crucial for sculpting. Use a sphere for heads "
                "and organic round forms. Use a cube for hard-surface objects and architectural "
                "elements. Use a cylinder for limbs, columns, and elongated forms. Use an "
                "icosphere for uniform topology distribution. Use the Monkey (Suzanne) as a "
                "starting point for character heads."
            ),
            "category": "technique",
        },
        {
            "topic": "Subdivision Workflow",
            "content": (
                "Start with low subdivision for blocking out the major forms (levels 1-2). "
                "Increase subdivision for adding secondary forms (levels 3-4). Use high "
                "subdivision for fine details like pores and wrinkles (levels 5-6). Use "
                "Multires modifier for non-destructive subdivision sculpting."
            ),
            "category": "workflow",
        },
        {
            "topic": "Brush Techniques",
            "content": (
                "Draw brush: Build up form by adding/removing volume. Clay Strips: Add broad "
                "flat strokes for muscle/form definition. Inflate: Push vertices outward along "
                "normals for puffing up areas. Crease: Create sharp creases and wrinkles. "
                "Grab: Move vertices freely for major form adjustments. Smooth: Blend and "
                "soften surface details. Pinch: Sharpen edges and creases. Flatten: Level "
                "surfaces to a uniform height. Snake Hook: Drag and pull surface for tentacles, "
                "horns, and flowing shapes."
            ),
            "category": "technique",
        },
        {
            "topic": "Symmetry in Sculpting",
            "content": (
                "Enable X-axis symmetry for character and creature sculpting. Use the Mirror "
                "modifier for perfect symmetry. Break symmetry only after main forms are "
                "established. Use Radial symmetry for flowers, eyes, and circular patterns."
            ),
            "category": "technique",
        },
        {
            "topic": "Retopology",
            "content": (
                "After sculpting, create a clean topology mesh using Remesh or manual retopo. "
                "Voxel Remesh creates uniform quads. QuadriFlow Remesh creates flow-following "
                "quads. Use Shrinkwrap modifier to project retopo mesh onto sculpt."
            ),
            "category": "workflow",
        },
        {
            "topic": "Texture Painting",
            "content": (
                "UV unwrap the model before texture painting. Use Smart UV Project for quick "
                "unwrapping. Projection painting allows painting from multiple angles. Use "
                "stencil mapping to project reference images onto the surface. Bake high-poly "
                "details to normal maps for low-poly meshes."
            ),
            "category": "technique",
        },
        {
            "topic": "Material Setup for Sculpts",
            "content": (
                "Use Principled BSDF for physically-based materials. Set base color from "
                "reference images. Use roughness maps for surface variation. Add normal maps "
                "for micro-detail. Use subsurface scattering for skin and organic materials. "
                "Use metallic for armors, weapons, and metal objects."
            ),
            "category": "materials",
        },
        {
            "topic": "Procedural Deformation",
            "content": (
                "Simple Deform modifier types: Twist rotates mesh around an axis, Bend curves "
                "mesh around a point, Taper scales along an axis, Stretch elongates along an "
                "axis. Displace modifier pushes vertices along normals using a texture. Lattice "
                "provides broad deformation control. Use these for major shape adjustments "
                "before fine sculpting."
            ),
            "category": "technique",
        },
    ]

    def __init__(self, db_path=None, max_pages=50, scrape_youtube=True, youtube_queries=None):
        self.kb = KnowledgeBase(db_path=db_path)
        self.max_pages = max_pages
        self.scrape_youtube = scrape_youtube
        self.youtube_queries = youtube_queries or self.YOUTUBE_SEARCH_QUERIES
        self._ctx = ssl.create_default_context()
        self._pages_scraped = 0
        self._videos_scraped = 0

    def scrape_all(self):
        self._store_builtin_knowledge()
        self._scrape_documentation()
        self._scrape_tutorials()
        if self.scrape_youtube:
            self._scrape_youtube_tutorials()
        print(
            f"Auto Sculptor AI: Knowledge base built with {self._pages_scraped} pages "
            f"and {self._videos_scraped} YouTube videos scraped"
        )

    def _store_builtin_knowledge(self):
        for entry in self.SCULPTING_KNOWLEDGE:
            self.kb.store(
                topic=entry["topic"],
                content=entry["content"],
                category=entry["category"],
                source="builtin",
            )

    def _scrape_documentation(self):
        for url in self.BLENDER_DOCS_URLS:
            if self._pages_scraped >= self.max_pages:
                break
            try:
                content = self._fetch_page(url)
                if content:
                    text = self._extract_text(content)
                    if text and len(text) > 100:
                        topic = self._extract_title(content) or url.split("/")[-1].replace(".html", "")
                        self.kb.store(
                            topic=topic,
                            content=text[:5000],
                            category="documentation",
                            source=url,
                        )
                        self._pages_scraped += 1

                        links = self._extract_links(content, url)
                        for link in links[:5]:
                            if self._pages_scraped >= self.max_pages:
                                break
                            self._scrape_subpage(link)

            except Exception as e:
                print(f"Auto Sculptor AI: Error scraping {url}: {e}")

    def _scrape_tutorials(self):
        for source in self.TUTORIAL_SOURCES:
            if self._pages_scraped >= self.max_pages:
                break
            try:
                content = self._fetch_page(source["url"])
                if content:
                    text = self._extract_text(content)
                    if text and len(text) > 50:
                        self.kb.store(
                            topic=source["name"],
                            content=text[:5000],
                            category=source["category"],
                            source=source["url"],
                        )
                        self._pages_scraped += 1
            except Exception as e:
                print(f"Auto Sculptor AI: Error scraping tutorial {source['url']}: {e}")

    def _scrape_subpage(self, url):
        try:
            content = self._fetch_page(url)
            if content:
                text = self._extract_text(content)
                if text and len(text) > 100:
                    topic = self._extract_title(content) or url.split("/")[-1].replace(".html", "")
                    self.kb.store(
                        topic=topic,
                        content=text[:5000],
                        category="documentation",
                        source=url,
                    )
                    self._pages_scraped += 1
        except Exception as e:
            print(f"Auto Sculptor AI: Error scraping subpage {url}: {e}")

    def _fetch_page(self, url):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return None

    def _extract_text(self, html_content):
        parser = _HTMLTextExtractor()
        try:
            parser.feed(html_content)
            return parser.get_text()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = html.unescape(text)
            return re.sub(r"\s+", " ", text).strip()

    def _extract_title(self, html_content):
        match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
        if match:
            title = html.unescape(match.group(1)).strip()
            title = title.split(" — ")[0].split(" - ")[0].strip()
            return title
        return None

    def _extract_links(self, html_content, base_url):
        links = []
        base_parts = base_url.rsplit("/", 1)
        base_path = base_parts[0] + "/" if len(base_parts) > 1 else base_url

        pattern = r'href=["\']([^"\']+\.html)["\']'
        for match in re.finditer(pattern, html_content):
            href = match.group(1)
            if href.startswith("http"):
                if "blender.org" in href:
                    links.append(href)
            elif not href.startswith("#") and not href.startswith("mailto:"):
                full_url = base_path + href
                links.append(full_url)

        return links[:10]

    def _scrape_youtube_tutorials(self):
        max_videos = min(self.max_pages, 30)
        for query in self.youtube_queries:
            if self._videos_scraped >= max_videos:
                break
            try:
                video_ids = self._youtube_search(query)
                for vid_id in video_ids:
                    if self._videos_scraped >= max_videos:
                        break
                    self._scrape_youtube_video(vid_id)
            except Exception as e:
                print(f"Auto Sculptor AI: Error searching YouTube for '{query}': {e}")

    def _youtube_search(self, query):
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        content = self._fetch_page(url)
        if not content:
            return []

        video_ids = []
        pattern = r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"'
        seen = set()
        for match in re.finditer(pattern, content):
            vid_id = match.group(1)
            if vid_id not in seen:
                seen.add(vid_id)
                video_ids.append(vid_id)
            if len(video_ids) >= 5:
                break

        return video_ids

    def _scrape_youtube_video(self, video_id):
        try:
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            page_content = self._fetch_page(watch_url)
            if not page_content:
                return

            title = self._extract_youtube_title(page_content)
            if not title:
                title = f"YouTube Video {video_id}"

            transcript = self._extract_youtube_captions(video_id, page_content)
            if not transcript or len(transcript) < 100:
                description = self._extract_youtube_description(page_content)
                if description and len(description) > 100:
                    transcript = description

            if not transcript or len(transcript) < 100:
                return

            self.kb.store(
                topic=title,
                content=transcript[:8000],
                category="youtube_tutorial",
                source=watch_url,
            )
            self._videos_scraped += 1
            print(f"Auto Sculptor AI: Scraped YouTube video: {title}")

        except Exception as e:
            print(f"Auto Sculptor AI: Error scraping video {video_id}: {e}")

    def _extract_youtube_title(self, page_content):
        match = re.search(r'<title>(.*?)</title>', page_content, re.IGNORECASE | re.DOTALL)
        if match:
            title = html.unescape(match.group(1)).strip()
            title = title.replace(" - YouTube", "").strip()
            return title
        match = re.search(r'"title"\s*:\s*\{"runs"\s*:\s*\[\{"text"\s*:\s*"(.*?)"', page_content)
        if match:
            return html.unescape(match.group(1))
        return None

    def _extract_youtube_captions(self, video_id, page_content):
        caption_track_url = self._find_caption_track(page_content)
        if not caption_track_url:
            return None

        caption_url = html.unescape(caption_track_url)
        caption_content = self._fetch_page(caption_url)
        if not caption_content:
            return None

        texts = re.findall(r'<text[^>]*>(.*?)</text>', caption_content, re.DOTALL)
        if not texts:
            return None

        transcript_parts = []
        for text in texts:
            decoded = html.unescape(text).strip()
            decoded = re.sub(r'<[^>]+>', '', decoded)
            if decoded:
                transcript_parts.append(decoded)

        return " ".join(transcript_parts)

    def _find_caption_track(self, page_content):
        match = re.search(
            r'"captionTracks"\s*:\s*\[(.*?)\]',
            page_content,
            re.DOTALL,
        )
        if not match:
            return None

        tracks_json = match.group(1)

        en_match = re.search(
            r'"baseUrl"\s*:\s*"(.*?)"[^}]*"languageCode"\s*:\s*"en',
            tracks_json,
        )
        if en_match:
            return en_match.group(1).replace("\\u0026", "&")

        any_match = re.search(r'"baseUrl"\s*:\s*"(.*?)"', tracks_json)
        if any_match:
            return any_match.group(1).replace("\\u0026", "&")

        return None

    def _extract_youtube_description(self, page_content):
        match = re.search(
            r'"shortDescription"\s*:\s*"(.*?)"(?:,|\})',
            page_content,
            re.DOTALL,
        )
        if match:
            desc = match.group(1)
            desc = desc.replace("\\n", "\n").replace('\\"', '"')
            return desc.strip()
        return None
