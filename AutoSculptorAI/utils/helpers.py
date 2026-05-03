import os
import math
from mathutils import Vector


def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))


def lerp(a, b, t):
    return a + (b - a) * clamp(t, 0.0, 1.0)


def smooth_step(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def distance_3d(p1, p2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


def normalize_vector(v):
    length = math.sqrt(sum(x * x for x in v))
    if length == 0:
        return [0.0] * len(v)
    return [x / length for x in v]


def map_range(value, in_min, in_max, out_min, out_max):
    if in_max == in_min:
        return out_min
    return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))


def calculate_mesh_bounds(vertices):
    if not vertices:
        return None

    min_co = list(vertices[0])
    max_co = list(vertices[0])

    for v in vertices:
        for i in range(3):
            min_co[i] = min(min_co[i], v[i])
            max_co[i] = max(max_co[i], v[i])

    return {
        "min": min_co,
        "max": max_co,
        "center": [(min_co[i] + max_co[i]) / 2 for i in range(3)],
        "size": [max_co[i] - min_co[i] for i in range(3)],
    }


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def get_addon_directory():
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def format_file_size(size_bytes):
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def validate_image_path(path):
    if not path:
        return False
    if not os.path.isfile(path):
        return False
    valid_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}
    ext = os.path.splitext(path)[1].lower()
    return ext in valid_extensions


def spherical_to_cartesian(radius, theta, phi):
    x = radius * math.sin(theta) * math.cos(phi)
    y = radius * math.sin(theta) * math.sin(phi)
    z = radius * math.cos(theta)
    return (x, y, z)


def cartesian_to_spherical(x, y, z):
    radius = math.sqrt(x * x + y * y + z * z)
    if radius == 0:
        return (0, 0, 0)
    theta = math.acos(clamp(z / radius, -1.0, 1.0))
    phi = math.atan2(y, x)
    return (radius, theta, phi)
