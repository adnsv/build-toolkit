import os
from pathlib import Path

def normalize_path(path: str) -> str:
    """Convert path to use forward slashes and remove trailing /, handle ../ with abspath"""
    path = os.path.abspath(path)  # Handle ../ and ./ in paths
    path = path.replace('\\', '/')
    if path.endswith('/.'):
        path = path[:-2]
    elif path.endswith('/'):
        path = path[:-1]
    return path

def ensure_dir(directory: str):
    """Create directory if it doesn't exist"""
    Path(directory).mkdir(parents=True, exist_ok=True) 