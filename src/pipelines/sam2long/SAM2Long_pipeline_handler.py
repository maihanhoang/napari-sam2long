import os
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytest
from napari.utils.notifications import show_info
from qtpy.QtWidgets import QWidget


# Sam2Long pipeline class
class SAM2Long_pipeline(QWidget):
    def __init__(
        self,
        napari_viewer,
        main_window_object,
        checkpoint_path,
        model_cfg_name,
    ):

        build_sam2_video_predictor = pytest.importorskip(
            "sam2.build_sam.build_sam2_video_predictor"
        )
        torch = pytest.importorskip("torch")

        super().__init__()
        self.viewer = napari_viewer
        self.mwo = main_window_object

        self.source_frame_dir = (
            None  # Will be set inside process volume function
        )

        ### Allow cpu and mps as well
        # select the device for computation
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
        print(f"Using device: {device}")

        if device.type == "cuda":
            # use bfloat16 for the entire notebook
            torch.autocast("cuda", dtype=torch.bfloat16).__enter__()
            # turn on tfloat32 for Ampere GPUs (https://pytorch.org/docs/stable/notes/cuda.html#tensorfloat-32-tf32-on-ampere-devices)
            if torch.cuda.get_device_properties(0).major >= 8:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
        elif device.type == "mps":
            print(
                "\nSupport for MPS devices is preliminary. SAM 2 is trained with CUDA and might "
                "give numerically different outputs and sometimes degraded performance on MPS. "
                "See e.g. https://github.com/pytorch/pytorch/issues/84936 for a discussion."
            )

        sam2_checkpoint = checkpoint_path
        model_cfg = model_cfg_name

        self.predictor = build_sam2_video_predictor(
            model_cfg, sam2_checkpoint, device=device
        )
        # per_obj_png_file = True
        # self.predictor = build_sam2_video_predictor(
        #     model_cfg,
        #     sam2_checkpoint,
        #     device=device,
        #     # hydra_overrides_extra=[
        #     #     "++model.sam_mask_decoder_extra_args.dynamic_multimask_via_stability=true",
        #     # ],
        #     # hydra_overrides_extra = [
        #     # "++model.non_overlap_masks=" + ("false" if per_obj_png_file else "true")
        #     # ]
        # )

        self.preprocess_volume()

        self.inference_state = self.predictor.init_state(
            video_path=self.source_frame_dir.as_posix()
        )

        ### Additional parameters for SAM2Long
        self.inference_state["num_pathway"] = 3
        self.inference_state["iou_thre"] = 0.3
        self.inference_state["uncertainty"] = 1

        self.prompts = {}

    def preprocess_volume(self):
        """Save each frame as jpeg to a temp dir"""
        layer_name = self.mwo.image_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        volume = layer.data

        self.source_frame_dir = Path(
            tempfile.mkdtemp(suffix="_naparisam2long")
        )
        # Save each slice as a separate image
        for i in range(volume.shape[0]):
            slice_path = os.path.join(self.source_frame_dir, f"{i:04d}.jpeg")

            if os.path.exists(slice_path):
                continue

            img_slice = volume[i]
            cv2.imwrite(slice_path, img_slice.squeeze())

        print("Frames generated.")

    def add_point(self, point_array, label_id, neg_or_pos=1):
        ann_frame_idx = point_array[0]
        ann_obj_id = label_id
        new_point = [point_array[2], point_array[1]]
        new_label = neg_or_pos
        check_if_our_z_is_new = True
        check_if_our_annotation_is_new = True

        # Check if in dict else add it

        # Object has been annotated before
        if ann_obj_id in self.prompts:
            all_list = []
            for existing_list in self.prompts[ann_obj_id]:

                # this frame has been annotated/prompted before
                if existing_list[0] == ann_frame_idx:
                    points = existing_list[1]
                    labels = list(existing_list[2])
                    points = np.append(points, [new_point], axis=0)
                    labels.append(new_label)
                    new_list = [
                        ann_frame_idx,
                        points,
                        np.array(labels, np.int32),
                    ]
                    all_list.append(new_list)
                    check_if_our_z_is_new = False
                # frame has not been annotated before
                else:
                    all_list.append(existing_list)

            self.prompts[ann_obj_id] = all_list
            check_if_our_annotation_is_new = False

        # Object has NOT been annotated before
        else:
            points = np.array(
                [[point_array[2], point_array[1]]], dtype=np.float32
            )
            labels = np.array([neg_or_pos], np.int32)
            self.prompts[ann_obj_id] = [[ann_frame_idx, points, labels]]

        # Object has been annotated but not in this frame
        if check_if_our_z_is_new and not (check_if_our_annotation_is_new):
            points = np.array(
                [[point_array[2], point_array[1]]], dtype=np.float32
            )
            labels = np.array([neg_or_pos], np.int32)
            existing_val = self.prompts[ann_obj_id]
            existing_val.append([ann_frame_idx, points, labels])
            self.prompts[ann_obj_id] = existing_val

        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data

        self.predictor.reset_state(self.inference_state)
        _, out_obj_ids, out_mask_logits = self.predictor.add_new_points_or_box(
            inference_state=self.inference_state,
            frame_idx=ann_frame_idx,
            obj_id=ann_obj_id,
            points=points,
            labels=labels,
        )

        # if image and label layer dimensions do not match, show info
        if (
            label_layer_data[0].shape
            != out_mask_logits[0][0].cpu().numpy().shape
        ):
            print("label", label_layer_data.shape)
            print("outmask", out_mask_logits[0][0].cpu().numpy().shape)
            show_info("Reset & initialize before processing new data.")
            return

        mask_for_this_frame = np.zeros(
            (label_layer_data.shape[1], label_layer_data.shape[2]),
            dtype=np.int32,
        )

        for i, out_obj_id in enumerate(out_obj_ids):
            out_mask = (out_mask_logits[i] > 0.0).cpu().numpy()
            mask_for_this_frame[out_mask[0]] = out_obj_id

        label_layer_data[ann_frame_idx, :, :] = mask_for_this_frame
        layer.data = label_layer_data

    def video_propagate(self, per_obj_png_file=True):

        torch = pytest.importorskip("torch")

        # run propagation throughout the video and collect the results in a dict
        layer_name = self.mwo.output_layers_combo.currentText()
        layer = self.viewer.layers[layer_name]
        label_layer_data = layer.data
        label_no = (
            label_layer_data.max()
        )  # label_number for different colors in napari

        # Check that only one label was provided
        if len(np.unique(label_layer_data)) != 2:
            if len(np.unique(label_layer_data)) == 1:
                show_info("No label for this label layer.")
                return
            else:
                show_info("Only one object label per label layer allowed.")
                return

        # Check that number of images in viewer and in temporary directory match
        if len(list(self.source_frame_dir.glob("*"))) != len(label_layer_data):
            show_info("Reset & initialize before processing new data.")
            return

        ### SAM2Long Parameters
        object_ids = [
            0
        ]  # currently this only allows segmenting one object at a time
        object_idx = 0
        score_thresh = 0.0
        output_scores_per_object = defaultdict(dict)

        ### Use mask on currently viewed frame; enables using point prompts and/or manually drawn masks using napari's tools
        self.predictor.reset_state(self.inference_state)
        self.predictor.add_new_mask(
            inference_state=self.inference_state,
            frame_idx=self.viewer.dims.current_step[0],
            obj_id=0,
            mask=label_layer_data[self.viewer.dims.current_step[0]],
        )

        print("Get per-frame segmentations.")
        for frame_idx in self.predictor.propagate_in_video(
            self.inference_state,
            reverse=False,
        ):
            progress = int((frame_idx * 100) / label_layer_data.shape[0])
            self.mwo.video_propagation_progressBar.setValue(progress)

        out_mask_logits = self.predictor.get_propagated_masks(
            self.inference_state
        )
        input_frame_idx = next(
            iter(
                self.inference_state["consolidated_frame_inds"][
                    "cond_frame_outputs"
                ]
            )
        )
        for frame_idx in range(
            input_frame_idx, self.inference_state["num_frames"]
        ):
            output_scores_per_object[object_idx][frame_idx] = (
                out_mask_logits[frame_idx - input_frame_idx].cpu().numpy()
            )

        video_segments = (
            {}
        )  # video_segments contains the per-frame segmentation results

        for frame_idx in range(
            input_frame_idx, self.inference_state["num_frames"]
        ):
            scores = torch.full(
                size=(
                    len(object_ids),
                    1,
                    self.inference_state["video_height"],
                    self.inference_state["video_width"],
                ),
                fill_value=-1024.0,
                dtype=torch.float32,
            )
            for i, object_id in enumerate(object_ids):
                if frame_idx in output_scores_per_object[object_id]:
                    scores[i] = torch.from_numpy(
                        output_scores_per_object[object_id][frame_idx]
                    )

            if not per_obj_png_file:
                scores = self.predictor._apply_non_overlapping_constraints(
                    scores
                )
            per_obj_output_mask = {
                object_id: (scores[i] > score_thresh).cpu().numpy()
                for i, object_id in enumerate(object_ids)
            }
            video_segments[frame_idx] = per_obj_output_mask

            for _, out_mask in video_segments[frame_idx].items():
                label_layer_data[frame_idx, :, :] = out_mask * label_no

        layer.data = label_layer_data
        self.mwo.video_propagation_progressBar.setValue(100)

    def reset(self):
        self.predictor.reset_state(self.inference_state)
        label_layer_name = self.mwo.output_layers_combo.currentText()
        if (
            label_layer_name is not None and label_layer_name != ""
        ):  ### Reset label layer if label is not empty
            label_layer = self.viewer.layers[label_layer_name]
            label_layer_data = label_layer.data
            zero_mask = np.zeros(label_layer_data.shape, dtype=np.int32)
            label_layer.data = zero_mask

        self.prompts = {}  ### Empty prompts when resetting
        self.mwo.video_propagation_progressBar.setValue(0)

    def delete_source_frame_dir(self):
        """Deletes the temporary source frame directory"""
        if self.source_frame_dir:
            shutil.rmtree(self.source_frame_dir, ignore_errors=True)
