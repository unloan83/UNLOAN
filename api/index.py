import sys
import os
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
multibagger_dir = root_dir.parent / "Multibagger"
if str(multibagger_dir) not in sys.path and multibagger_dir.exists():
    sys.path.insert(0, str(multibagger_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import create_app

app = create_app()

