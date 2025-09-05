import importlib
import subprocess
import sys
import site
import os
from typing import Optional

def _refresh_sys_path():
    # include both global and user site-packages
    site_paths = []
    try:
        site_paths.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        site_paths.append(site.getusersitepackages())
    except Exception:
        pass

    for p in site_paths:
        if p and os.path.exists(p) and p not in sys.path:
            sys.path.append(p)

def ensure_package(pip_name: str, import_name: Optional[str] = None) -> bool:
    """
    Ensure a package is importable. If not, pip-install it and refresh import caches/paths.
    - pip_name: name used with pip (e.g. 'opencv-python')
    - import_name: module name to import (e.g. 'cv2'); defaults to pip_name with '-' removed
    """
    mod_name = import_name or pip_name.replace("-", "_")

    try:
        importlib.import_module(mod_name)
        return True
    except ImportError:
        print(f"[neuronav] '{pip_name}' not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            _refresh_sys_path()
            importlib.invalidate_caches()
            importlib.import_module(mod_name)
            print(f"[neuronav] Installed and loaded '{pip_name}' successfully.")
            return True
        except Exception as e:
            print(f"[neuronav] Failed to install or import '{pip_name}': {e}")
            return False
