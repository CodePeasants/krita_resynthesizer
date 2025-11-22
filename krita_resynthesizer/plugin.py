from krita import Extension, Krita, QMessageBox, DockWidget, DockWidgetFactory, DockWidgetFactoryBase
from PyQt5 import QtWidgets, QtCore

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import resynthesizer
    HAS_RESYNTH = True
except ImportError:
    HAS_RESYNTH = False


_SETTINGS = QtCore.QSettings("CodePeasants", "KritaResynthesizer")
_DEFAULT_SETTINGS = {
    "padding": 100,
    "new_layer": False
}


def perform_resynthesis(padding_pixels=100, new_layer=False):
    """Shared logic used by both the Docker and the Menu Extension.

    Args:
        padding_pixels (int, optional): The number of pixels to use as context. Defaults to 100.
        new_layer (bool, optional): Whether to create a new layer for the resynthesized image. Defaults to False.
    """
    if not HAS_PIL:
        QMessageBox.critical(None, "Missing Library", "Error: 'Pillow' is not installed.\nPlease run: pip install Pillow")
        return
    if not HAS_RESYNTH:
        QMessageBox.critical(None, "Missing Library", "Error: 'resynthesizer' package is not installed.")
        return

    app = Krita.instance()
    doc = app.activeDocument()
    
    if not doc:
        QMessageBox.warning(None, "No Document", "Please open a document first.")
        return

    node = doc.activeNode()
    selection = doc.selection()

    if not selection:
        QMessageBox.warning(None, "No Selection", "Please make a selection.")
        return

    # Get Selection Bounds
    sel_x = selection.x()
    sel_y = selection.y()
    sel_w = selection.width()
    sel_h = selection.height()

    # Calculate Context Padding
    doc_w = doc.width()
    doc_h = doc.height()

    # Input pixels
    final_x = max(0, sel_x - padding_pixels)
    final_y = max(0, sel_y - padding_pixels)
    
    final_w = min(doc_w, sel_x + sel_w + padding_pixels) - final_x
    final_h = min(doc_h, sel_y + sel_h + padding_pixels) - final_y

    # Safety check: If selection covers the WHOLE image
    if sel_w >= doc_w and sel_h >= doc_h:
         QMessageBox.warning(None, "Selection too big", 
             "You have selected the entire image.\n"
             "Resynthesizer needs unselected 'context' pixels to learn from.")
         return

    # Get Pixel Data for the PADDED area
    pixel_bytes = node.pixelData(final_x, final_y, final_w, final_h)
    mask_bytes = selection.pixelData(final_x, final_y, final_w, final_h)

    try:
        # Convert to PIL
        input_image = Image.frombytes("RGBA", (final_w, final_h), pixel_bytes)
        mask_image = Image.frombytes("L", (final_w, final_h), mask_bytes)

        # Ensure RGB (Remove alpha for synthesis engine stability)
        input_rgb = input_image.convert("RGB")
        
        # Run Resynthesis
        # Threshold mask: 255 = fill, 0 = source
        mask_binary = mask_image.point(lambda p: 255 if p > 0 else 0)

        output_rgb = resynthesizer.resynthesize(input_rgb, mask_binary)
        
        # Restore Alpha from original
        r, g, b = output_rgb.split()
        original_a = input_image.split()[3]
        output_rgba = Image.merge("RGBA", (r, g, b, original_a))

        # Write Data Back
        output_bytes = output_rgba.tobytes()

        if new_layer:
            new_node = doc.createNode("Resynthesize", "paintLayer")
            # Place the new layer under the same parent as the current layer.
            if node.parentNode():
                node.parentNode().addChildNode(new_node, node)
            doc.setActiveNode(new_node)
            node = new_node  # Set pixel data on new layer instead.
            
        node.setPixelData(output_bytes, final_x, final_y, final_w, final_h)
        
        doc.refreshProjection()

    except Exception as e:
        QMessageBox.critical(None, "Synthesis Error", f"An error occurred during synthesis:\n{str(e)}")
        return


class ResynthesizerDocker(DockWidget):
    def __init__(self):
        super().__init__()
        
        
        self.setWindowTitle("Resynthesizer")
        
        # Main Widget
        main_widget = QtWidgets.QWidget(self)
        self.setWidget(main_widget)
        
        # Layout
        layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(layout)
        
        # Controls Group
        group = QtWidgets.QGroupBox("Settings")
        form_layout = QtWidgets.QFormLayout()
        group.setLayout(form_layout)
        
        # Padding Control
        self.padding_spin = QtWidgets.QSpinBox()
        self.padding_spin.setRange(10, 2000)
        self.padding_spin.setValue(_SETTINGS.value("padding", _DEFAULT_SETTINGS["padding"], type=int))
        self.padding_spin.setSuffix(" px")
        self.padding_spin.setToolTip("How many pixels around the selection to use as context.")
        self.padding_spin.valueChanged.connect(self.save_padding)

        self.new_layer_check = QtWidgets.QCheckBox()
        self.new_layer_check.setToolTip("Create a new layer for the resynthesized image.")
        self.new_layer_check.setChecked(_SETTINGS.value("new_layer", _DEFAULT_SETTINGS["new_layer"], type=bool))
        self.new_layer_check.stateChanged.connect(self.save_new_layer)
        
        form_layout.addRow("Context Padding:", self.padding_spin)
        form_layout.addRow("Create New Layer:", self.new_layer_check)
        layout.addWidget(group)
        
        # Run Button
        self.btn_run = QtWidgets.QPushButton("Resynthesize Selection")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self.run_synthesis)
        layout.addWidget(self.btn_run)
        
        # Spacer to push items up
        layout.addStretch()

    def run_synthesis(self):
        padding = self.padding_spin.value()
        new_layer = self.new_layer_check.isChecked()
        perform_resynthesis(padding, new_layer)
        
    def canvasChanged(self, canvas):
        # Required abstract method for DockWidget
        pass

    def save_padding(self, value):
        _SETTINGS.setValue("padding", value)
        _SETTINGS.sync()

    def save_new_layer(self, state):
        _SETTINGS.setValue("new_layer", state == QtCore.Qt.CheckState.Checked)
        _SETTINGS.sync()


class ResynthesizerExtension(Extension):

    def __init__(self, parent):
        super(ResynthesizerExtension, self).__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("resynthesize_selection", "Resynthesize Selection", "tools/scripts")
        action.triggered.connect(self.resynthesize)
        action.setShortcut("Alt+Backspace")

    def resynthesize(self):
        perform_resynthesis(
            padding_pixels=_SETTINGS.value("padding", _DEFAULT_SETTINGS["padding"], type=int),
            new_layer=_SETTINGS.value("new_layer", _DEFAULT_SETTINGS["new_layer"], type=bool)
        )

Krita.instance().addExtension(ResynthesizerExtension(Krita.instance()))
factory = DockWidgetFactory("resynthesizer_docker", DockWidgetFactoryBase.DockRight, ResynthesizerDocker)
Krita.instance().addDockWidgetFactory(factory)