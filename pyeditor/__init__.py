"""
PyEditor
========
A Photoshop-style desktop image editor built with Tkinter (UI) and
NumPy / SciPy / scikit-image / scikit-learn / Pillow (image processing).

Package layout (see README.md for the full rationale):

    pyeditor/
        core/   -> pure image-processing logic, no UI imports at all
        ui/     -> Tkinter widgets/screens, depend on core, never the reverse
        assets/ -> logo and other static resources
"""

__version__ = "1.0.0"
