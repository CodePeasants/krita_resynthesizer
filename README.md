# Krita Resynthesizer Plugin

This plugin brings texture synthesis/inpainting capabilities to Krita using the Python resynthesizer package. It allows you to remove objects or fill gaps by selecting an area and generating new textures based on the surrounding pixels.

## DEV NOTES
- `.action` file installs to: `C:\Users\peter\AppData\Roaming\krita\actions`
- python files install to: `C:\Users\peter\AppData\Roaming\krita\pykrita`
- [plugin docs](https://docs.krita.org/en/user_manual/python_scripting/krita_python_plugin_howto.html#creating-configurable-keyboard-shortcuts)

## WIP NOTES
- currently the keyboard shortcut is not being recognized (`C:\Users\peter\AppData\Roaming\krita\actions`).
Possibly the `backspace` string I added is not the correct name?
- Need to update this README.md
- I am vendoring numpy, meaning this will only work on windows and for versions of pykrita that use `python-3.10`
    - I might be able to get rid of vendored `numpy`, `resynthesizer` doesn't use it, and I think it is an optional dependency of pillow.
    - if I don't need numpy, I might be able to vendor stuff with submodules, which would be much better.
    - I currently have the `libs` directory in the gitignore while I sort this out.
- Big feature to add is a way to paint the context region like in photoshop.

## Prerequisites
- Krita 5.0+
- Python Dependencies: You must install numpy and resynthesizer into the Python environment that Krita uses.

### How to install dependencies
#### Windows:
- Open the folder where Krita is installed (usually `C:\Program Files\Krita (x64)`).
- Navigate to bin.
- Open a terminal (PowerShell or CMD) in this folder.
- Run:
```
.\python.exe -m pip install numpy resynthesizer
```

## Installation
- Open Krita.
- Go to Settings -> Manage Resources -> Open Resource Folder.
- Navigate to the pykrita folder.
- Copy the resynthesizer_plugin folder (containing __init__.py and plugin.py) into pykrita.
- Copy the resynthesizer_plugin.desktop file into pykrita (right next to the folder, not inside it).
- Restart Krita.
- Go to Settings -> Configure Krita -> Python Plugin Manager.
- Find "Resynthesizer Plugin" in the list and enable it.
- Restart Krita one last time.

## Usage
- Open an image.
- Select the layer you want to modify.
- Use any Selection Tool (Rectangular, Lasso, etc.) to select the object you want to remove or the area you want to fill.
- Go to the top menu: Tools -> Scripts -> Resynthesize Selection.
- Wait for the process to complete.

## Troubleshooting
- "Missing Library" Error: Ensure you ran the pip install command using the specific python executable found inside Krita's installation folder, not your system-wide python.
- Crash/Freeze: Synthesis on large 4K+ images can be slow. Try selecting smaller areas.
