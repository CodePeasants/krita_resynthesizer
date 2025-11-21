import sys
import os

# Setup vendored dependencies.
plugin_path = os.path.dirname(os.path.abspath(__file__))
libs_path = os.path.join(plugin_path, "libs")

# Check if 'libs' exists and add it to the start of sys.path
# We insert at 0 to ensure our bundled versions take precedence or are found first
if os.path.exists(libs_path):
    if libs_path not in sys.path:
        sys.path.insert(0, libs_path)

# Now that sys.path includes 'libs', we can import the module that uses them
from .plugin import ResynthesizerExtension

def initialize(krita_instance):
    return ResynthesizerExtension(krita_instance)
