import json
import urllib.request
import urllib.error
import time
import os
import ssl


class MeshyClient:
    """Client for Meshy.ai text-to-3D API."""

    API_BASE = "https://api.meshy.ai/openapi/v2"

    def __init__(self, api_key):
        self.api_key = api_key
        self._ctx = ssl.create_default_context()

    def text_to_3d(self, prompt, model_type="standard", enable_pbr=True,
                   texture_prompt=None, target_format="glb",
                   on_progress=None):
        """Full pipeline: preview → poll → refine → poll → download GLB."""
        if on_progress:
            on_progress("Creating 3D preview...", 5)

        preview_id = self._create_preview(prompt, model_type, target_format)

        if on_progress:
            on_progress("Generating 3D mesh (this may take a minute)...", 10)

        self._poll_task(preview_id, on_progress, stage="preview",
                        progress_start=10, progress_end=50)

        if on_progress:
            on_progress("Applying textures...", 55)

        refine_id = self._create_refine(preview_id, enable_pbr,
                                        texture_prompt, target_format)

        if on_progress:
            on_progress("Refining textures (this may take a minute)...", 60)

        task_data = self._poll_task(refine_id, on_progress, stage="refine",
                                    progress_start=60, progress_end=90)

        if on_progress:
            on_progress("Downloading 3D model...", 92)

        download_url = None
        actual_format = target_format
        model_urls = task_data.get("model_urls", {})
        if isinstance(model_urls, dict):
            for fmt in [target_format, "glb", "obj", "fbx"]:
                if model_urls.get(fmt):
                    download_url = model_urls[fmt]
                    actual_format = fmt
                    break
        if not download_url:
            for fmt in ["glb", "obj", "fbx"]:
                url_key = f"model_url_{fmt}"
                if task_data.get(url_key):
                    download_url = task_data[url_key]
                    actual_format = fmt
                    break

        if not download_url:
            model_url = task_data.get("model_url")
            if model_url:
                download_url = model_url

        if not download_url:
            raise RuntimeError(
                f"No downloadable model URL in task response. Keys: {list(task_data.keys())}"
            )

        file_path = self._download_file(download_url, actual_format)

        if on_progress:
            on_progress("Model downloaded!", 95)

        texture_urls = {}
        tex = task_data.get("texture_urls")
        if isinstance(tex, list) and tex:
            tex = tex[0]
        if isinstance(tex, dict):
            for key in ["base_color", "metallic", "normal", "roughness", "emission"]:
                if tex.get(key):
                    texture_urls[key] = tex[key]

        return {
            "file_path": file_path,
            "format": actual_format,
            "task_data": task_data,
            "texture_urls": texture_urls,
        }

    def _create_preview(self, prompt, model_type, target_format):
        payload = {
            "mode": "preview",
            "prompt": prompt[:600],
            "model_type": model_type,
            "ai_model": "latest",
            "target_formats": [target_format],
        }
        resp = self._api_post("/text-to-3d", payload)
        task_id = resp.get("result")
        if not task_id:
            raise RuntimeError(f"Failed to create preview task: {resp}")
        return task_id

    def _create_refine(self, preview_id, enable_pbr, texture_prompt, target_format):
        payload = {
            "mode": "refine",
            "preview_task_id": preview_id,
            "enable_pbr": enable_pbr,
            "target_formats": [target_format],
        }
        if texture_prompt:
            payload["texture_prompt"] = texture_prompt[:600]
        resp = self._api_post("/text-to-3d", payload)
        task_id = resp.get("result")
        if not task_id:
            raise RuntimeError(f"Failed to create refine task: {resp}")
        return task_id

    def _poll_task(self, task_id, on_progress=None, stage="preview",
                   progress_start=0, progress_end=100, timeout=600):
        start_time = time.time()
        poll_interval = 5

        while time.time() - start_time < timeout:
            task = self._api_get(f"/text-to-3d/{task_id}")
            status = task.get("status", "UNKNOWN")
            progress = task.get("progress", 0)

            if on_progress and progress > 0:
                scaled = progress_start + (progress / 100) * (progress_end - progress_start)
                on_progress(f"{stage.title()}: {progress}%", scaled)

            if status == "SUCCEEDED":
                return task
            elif status in ("FAILED", "EXPIRED"):
                error = task.get("task_error", {})
                msg = error.get("message", "Unknown error") if isinstance(error, dict) else str(error)
                raise RuntimeError(f"Meshy {stage} failed: {msg}")

            time.sleep(poll_interval)

        raise RuntimeError(f"Meshy {stage} timed out after {timeout}s")

    def _download_file(self, url, fmt="glb"):
        download_dir = os.path.join(os.path.expanduser("~"), ".autosculptor_ai", "downloads")
        os.makedirs(download_dir, exist_ok=True)

        filename = f"meshy_model_{int(time.time())}.{fmt}"
        filepath = os.path.join(download_dir, filename)

        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=self._ctx, timeout=120) as resp:
            with open(filepath, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)

        return filepath

    def _api_post(self, endpoint, payload):
        url = f"{self.API_BASE}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Meshy API error {e.code}: {body}")

    def _api_get(self, endpoint):
        url = f"{self.API_BASE}{endpoint}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Meshy API error {e.code}: {body}")
