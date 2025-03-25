# Imports
import os

import napari
import requests
from pipelines.samv2.Samv2_pipeline_handler import SamV2_pipeline
from qtpy import uic
from qtpy.QtWidgets import (
    QComboBox,
    QFileDialog,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QWidget,
    QApplication,
)
# Imported by Mai
from napari.utils.notifications import show_info

# Main Plugin class that is connected from outside at napari plugin entry point
class SAMV2_min(QWidget):
    def __init__(self, napari_viewer):
        # Initializing
        super().__init__()
        self.viewer = napari_viewer
        self.appInstance = QApplication.instance() # Mai, for deleting tmp dir

        # Load the UI file - Main window
        script_dir = os.path.dirname(__file__)
        ui_file_name = "SAM_V2.ui"
        abs_file_path = os.path.join(
            script_dir, "..", "UI_files", ui_file_name
        )
        uic.loadUi(abs_file_path, self)

        # Get required children for functionality addition
        self.image_layers_combo = self.findChild(
            QComboBox, "Image_layer_combo"
        )
        # self.interdir_lineedt = self.findChild(QLineEdit, "inter_lineedt")
        # self.interdir_browse_btn = self.findChild(
        #     QPushButton, "inter_browse_btn"
        # )
        self.output_layers_combo = self.findChild(
            QComboBox, "output_layer_combo"
        )
        self.model_cbbox = self.findChild(QComboBox, "model_cbbox")

        self.initialize_btn = self.findChild(QPushButton, "Initialize_btn")
        self.video_propagation_progressBar = self.findChild(
            QProgressBar, "Propagation_progress"
        )
        self.video_propagate_btn = self.findChild(QPushButton, "Propagate_btn")
        self.reset_btn = self.findChild(QPushButton, "reset_btn")

        # Populate combo box - call
        self.populate_combo_box(self.image_layers_combo, "image")
        self.populate_combo_box(self.output_layers_combo, "label")
        self.populate_model_combo()

        # Connect events to functions
        self.viewer.layers.events.inserted.connect(self.layer_changed)
        self.viewer.layers.events.removed.connect(self.layer_changed)
        self.viewer.layers.events.changed.connect(self.layer_changed)
        self.viewer.mouse_drag_callbacks.append(self.on_mouse_click)
        # self.viewer.events.closed.connect(self.cleanup_temp_dir_upon_close)
        self.appInstance.lastWindowClosed.connect(self.cleanup_temp_dir) 

        # Connect button to functions
        # self.interdir_browse_btn.clicked.connect(self.choose_inter_frame_dir)
        self.initialize_btn.clicked.connect(self.initialize_pipeline)
        self.video_propagate_btn.clicked.connect(self.video_propagate)
        self.reset_btn.clicked.connect(self.reset_everything)

    # Function to populate combo boxes based on layers
    def populate_combo_box(self, combobx, layer_type="image"):
        ### Changed by Mai to remember last selected layer
        # Save current selection,
        if combobx is not None:
            current_text = combobx.currentText()
        else:
            current_text = None

        # Clear the combo box first
        combobx.clear()
        
        if layer_type == "image":
            # Get all existing image layers from the napari viewer
            layers = [
                layer.name
                for layer in self.viewer.layers
                if isinstance(layer, napari.layers.Image)
            ]
        elif layer_type == "label":
            # Get all existing label layers from the napari viewer
            layers = [
                layer.name
                for layer in self.viewer.layers
                if isinstance(layer, napari.layers.Labels)
            ]
        else:
            raise ValueError(
                "Invalid layer_type. Expected 'image' or 'label'."
            )

        combobx.addItems(layers)
        # Keep last selected item
        if current_text is not None:
            combobx.setCurrentText(current_text)


    # Function to handle combobox state change
    def layer_changed(self):
        # Populate combo box - call
        self.populate_combo_box(self.image_layers_combo, "image")
        self.populate_combo_box(self.output_layers_combo, "label")

    def populate_model_combo(self):
        self.model_cbbox.clear()
        self.model_cbbox.addItems(
            ["sam2.1_hiera_base_plus", "sam2.1_hiera_tiny", "sam2.1_hiera_small", "sam2.1_hiera_large"]
        )

    # # Choose inter frame dir
    # def choose_inter_frame_dir(self):
    #     dname = QFileDialog.getExistingDirectory()
    #     print(dname)
    #     self.interdir_lineedt.setText(str(dname))

    # # Initialize pipeline
    # BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/072824/"
    # CHECKPOINTS = {
    #     "sam2_hiera_tiny": "sam2_hiera_tiny.pt",
    #     "sam2_hiera_small": "sam2_hiera_small.pt",
    #     "sam2_hiera_base_plus": "sam2_hiera_base_plus.pt",
    #     "sam2_hiera_large": "sam2_hiera_large.pt",
    # }

        # Initialize pipeline
    BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/"
    CHECKPOINTS = {
        "sam2.1_hiera_tiny": "sam2.1_hiera_tiny.pt",
        "sam2.1_hiera_small": "sam2.1_hiera_small.pt",
        "sam2.1_hiera_base_plus": "sam2.1_hiera_base_plus.pt",
        "sam2.1_hiera_large": "sam2.1_hiera_large.pt",
    }

    def initialize_pipeline(self):
        # Reset everything 
        if hasattr(self, 'pipeline_object'):
            self.reset_everything()
            self.cleanup_temp_dir()

        script_dir = os.path.dirname(__file__)
        model_map = {
            "sam2.1_hiera_large": ("configs/sam2.1/sam2.1_hiera_l.yaml", "sam2.1_hiera_large.pt"),
            "sam2.1_hiera_small": ("configs/sam2.1/sam2.1_hiera_s.yaml", "sam2.1_hiera_small.pt"),
            "sam2.1_hiera_tiny": ("configs/sam2.1/sam2.1_hiera_t.yaml", "sam2.1_hiera_tiny.pt"),
            "sam2.1_hiera_base_plus": ("configs/sam2.1/sam2.1_hiera_b+.yaml", "sam2.1_hiera_base_plus.pt"),
        }

        selected_model = self.model_cbbox.currentText()

        if selected_model in model_map:
            model_cfg, checkpoint_name = model_map[selected_model]
            ## Added by Mai
            model_cfg_path = os.path.join(
                # script_dir, "..", "configs", model_cfg
                "configs", "sam2.1", model_cfg
            )
            ##
            checkpoint_path = os.path.join(
                script_dir, "..", "model", checkpoint_name
            )

            # Check if the checkpoint file exists
            if not os.path.exists(checkpoint_path):
                print(
                    f"Checkpoint {checkpoint_name} not found. Downloading..."
                )
                self.download_checkpoint(checkpoint_name, checkpoint_path)
            print("Model_cfg ", model_cfg_path)
            self.pipeline_object = SamV2_pipeline(
                self.viewer, self, checkpoint_path, model_cfg # _path # model_cfg, Changed by Mai
            )
        else:
            print("Model not recognized.")

    def download_checkpoint(self, checkpoint_name, checkpoint_path):
        url = self.BASE_URL + checkpoint_name

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Check if the download was successful

            with open(checkpoint_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"{checkpoint_name} downloaded successfully.")

        except requests.exceptions.RequestException as e:
            print(
                f"Failed to download {checkpoint_name} from {url}. Error: {e}"
            )

    def on_mouse_click(self, layer, event):
        # Check if it is a middle mouse click event
        if event.button == 3:  # 3 represents the middle mouse button
            # Mai: Check if pipeline has been initialized
            ##TODO: check if pipeline_object attribute exists
            if not hasattr(self, 'pipeline_object'):
                show_info("Please initialize first.")
                return
            
            # Mai: have to define labels layer first
            if self.output_layers_combo.count() == 0:
                show_info("Set output layer first.")
                return

            if "Control" in event.modifiers:
                # print(f'Ctrl + Middle mouse click at {event.position}')
                point = [
                    int(event.position[0]),
                    int(event.position[1]),
                    int(event.position[2]),
                ]
                layer_name = self.output_layers_combo.currentText()
                layer = self.viewer.layers[layer_name]
                active_label = layer.selected_label
                # Negative point
                self.pipeline_object.add_point(
                    point, active_label, neg_or_pos=0
                )

            else:
                # print(f'Middle mouse click at {event.position}')
                point = [
                    int(event.position[0]),
                    int(event.position[1]),
                    int(event.position[2]),
                ]
                layer_name = self.output_layers_combo.currentText()
                layer = self.viewer.layers[layer_name]
                active_label = layer.selected_label
                # positive point
                self.pipeline_object.add_point(
                    point, active_label, neg_or_pos=1
                )

    def video_propagate(self):
        self.pipeline_object.video_propagate()

    def reset_everything(self):
        if hasattr(self, "pipeline_object"):
            self.pipeline_object.reset()

    def cleanup_temp_dir(self):
        """Deletes the temporary source frame directory when Napari closes."""
        self.pipeline_object.cleanup_temp_dir()
