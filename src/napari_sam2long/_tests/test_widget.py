import os

from napari_sam2long._widget import SAM2Long


def napari_viewer_widget(make_napari_viewer_proxy):
    viewer = make_napari_viewer_proxy()
    widget = SAM2Long(viewer)

    return viewer, widget


def test_ui_file_exists():
    assert os.path.exists("src/UI_files/SAM2Long.ui"), "UI file not found.)"


def test_default_settings(make_napari_viewer_proxy):
    _, widget = napari_viewer_widget(make_napari_viewer_proxy)
    assert widget.image_layers_combo.count() == 0
    assert widget.output_layers_combo.count() == 0
    assert widget.model_cbbox.currentText() == "sam2.1_hiera_base_plus"
    assert widget.video_propagation_progressBar.value() == 0
