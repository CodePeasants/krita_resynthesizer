from krita import Extension, Krita, QMessageBox, DockWidget, DockWidgetFactory, DockWidgetFactoryBase
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSpinBox, QLabel, QFormLayout, QGroupBox

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


def perform_resynthesis(padding_pixels=100):
    """Shared logic used by both the Docker and the Menu Extension.
    """
    # Library checks
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

    # 1. Get Selection Bounds
    sel_x = selection.x()
    sel_y = selection.y()
    sel_w = selection.width()
    sel_h = selection.height()

    # 2. Calculate Context Padding
    doc_w = doc.width()
    doc_h = doc.height()

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

    # 3. Get Pixel Data for the PADDED area
    pixel_bytes = node.pixelData(final_x, final_y, final_w, final_h)
    mask_bytes = selection.pixelData(final_x, final_y, final_w, final_h)

    try:
        # Convert to PIL
        input_image = Image.frombytes("RGBA", (final_w, final_h), pixel_bytes)
        mask_image = Image.frombytes("L", (final_w, final_h), mask_bytes)

        # 4. Ensure RGB (Remove alpha for synthesis engine stability)
        input_rgb = input_image.convert("RGB")
        
        # 5. Run Resynthesis
        # Threshold mask: 255 = fill, 0 = source
        mask_binary = mask_image.point(lambda p: 255 if p > 0 else 0)

        output_rgb = resynthesizer.resynthesize(input_rgb, mask_binary)
        
        # 6. Restore Alpha from original
        r, g, b = output_rgb.split()
        original_a = input_image.split()[3]
        output_rgba = Image.merge("RGBA", (r, g, b, original_a))

        # 7. Write Data Back
        output_bytes = output_rgba.tobytes()
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
        main_widget = QWidget(self)
        self.setWidget(main_widget)
        
        # Layout
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # Controls Group
        group = QGroupBox("Settings")
        form_layout = QFormLayout()
        group.setLayout(form_layout)
        
        # Padding Control
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(10, 2000)
        self.padding_spin.setValue(100) # Default
        self.padding_spin.setSuffix(" px")
        self.padding_spin.setToolTip("How many pixels around the selection to use as context.")
        
        form_layout.addRow("Context Padding:", self.padding_spin)
        layout.addWidget(group)
        
        # Run Button
        self.btn_run = QPushButton("Resynthesize Selection")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self.run_synthesis)
        layout.addWidget(self.btn_run)
        
        # Spacer to push items up
        layout.addStretch()

    def run_synthesis(self):
        padding = self.padding_spin.value()
        perform_resynthesis(padding)
        
    def canvasChanged(self, canvas):
        # Required abstract method for DockWidget
        pass


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
        # The menu action uses a default padding of 100
        perform_resynthesis(100)

Krita.instance().addExtension(ResynthesizerExtension(Krita.instance()))
factory = DockWidgetFactory("resynthesizer_docker", DockWidgetFactoryBase.DockRight, ResynthesizerDocker)
Krita.instance().addDockWidgetFactory(factory)