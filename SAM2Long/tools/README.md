# Semi-supervised VOS Inference

The `vos_inference.py` script can be used to generate predictions for semi-supervised video object segmentation (VOS) evaluation on datasets such as [DAVIS](https://davischallenge.org/index.html),  [LVOS](https://lingyihongfd.github.io/lvos.github.io/), [MOSE](https://henghuiding.github.io/MOSE/) or the SA-V dataset.

After installing SAM 2 and its dependencies, it can be used as follows ([DAVIS 2017 dataset](https://davischallenge.org/davis2017/code.html) as an example). This script saves the prediction PNG files to the `--output_mask_dir`.
```bash
python ./tools/vos_inference.py \
  --sam2_cfg configs/sam2.1/sam2.1_hiera_b+.yaml \
  --sam2_checkpoint ./checkpoints/sam2.1_hiera_base_plus.pt \
  --base_video_dir /path-to-davis-2017/JPEGImages/480p \
  --input_mask_dir /path-to-davis-2017/Annotations/480p \
  --video_list_file /path-to-davis-2017/ImageSets/2017/val.txt \
  --output_mask_dir ./outputs/davis_2017_pred_pngs \
  --num_pathway 3 \
  --iou_thre 0.1 \
  --uncertainty 2 \
```
(replace `/path-to-davis-2017` with the path to DAVIS 2017 dataset)

<code>--num_pathway</code>: Defines the number of segmentation pathways to maintain.

<code>--iou_thre</code>: Sets the IoU threshold, filtering out low-confidence masks.

<code>--uncertainty</code>: Set the uncertainty threshold when selecting masks.


To evaluate on the SA-V dataset with per-object PNG files for the object masks, we need to **add the `--per_obj_png_file` flag** as follows (using SA-V val as an example). This script will also save per-object PNG files for the output masks under the `--per_obj_png_file` flag.
```bash
python ./tools/vos_inference.py \
  --sam2_cfg configs/sam2.1/sam2.1_hiera_b+.yaml \
  --sam2_checkpoint ./checkpoints/sam2.1_hiera_base_plus.pt \
  --base_video_dir /path-to-sav-val/JPEGImages_24fps \
  --input_mask_dir /path-to-sav-val/Annotations_6fps \
  --video_list_file /path-to-sav-val/sav_val.txt \
  --per_obj_png_file \
  --output_mask_dir ./outputs/sav_val_pred_pngs
  --num_pathway 3 \
  --iou_thre 0.1 \
  --uncertainty 2 \
```
(replace `/path-to-sav-val` with the path to SA-V val)

Then, we can use the evaluation tools or servers for each dataset to get the performance of the prediction PNG files above.

Note: by default, the `vos_inference.py` script above assumes that all objects to track already appear on frame 0 in each video (as is the case in DAVIS, MOSE or SA-V). **For VOS datasets that don't have all objects to track appearing in the first frame (such as LVOS or YouTube-VOS), please add the `--track_object_appearing_later_in_video` flag when using `vos_inference.py`**.


## Multi-Node Inference for Accelerated Processing
In default, you can run the above command to perform the inference on a single GPU. 
Also, we provide multi-node inference to speed up the process.

The following SLURM script runs inference in parallel across multiple GPUs. It assumes each node has 8 GPUs and evenly distributes video processing tasks across these GPUs. You can adjust the number of GPUs per node by specifying the `--num_nodes` argument.

```bash
set -x

gpu_list="${CUDA_VISIBLE_DEVICES:-0}"
IFS=',' read -ra GPULIST <<< "$gpu_list"
NODE_ID=${SLURM_PROCID}
echo "NODE ID: $NODE_ID"
CHUNKS=8

for IDX in $(seq 0 $((CHUNKS-1))); do
    CUDA_VISIBLE_DEVICES=${GPULIST[$IDX]} python ./tools/vos_inference.py \
        --sam2_cfg configs/sam2.1/sam2.1_hiera_b+.yaml \
        --sam2_checkpoint ./checkpoints/sam2.1_hiera_base_plus.pt \
        --base_video_dir /path-to-sav-val/JPEGImages_24fps \
        --input_mask_dir /path-to-sav-val/Annotations_6fps \
        --video_list_file /path-to-sav-val/sav_val.txt \
        --per_obj_png_file \
        --output_mask_dir ./outputs/sav_val_pred_pngs \
        --num_pathway 3 \
        --iou_thre 0.1 \
        --uncertainty 2 \
        --num_nodes $1 \
        --node_id $NODE_ID \
        --num_chunks $CHUNKS \
        --chunk_id $IDX &
done

wait
```

To launch the inference, run the following command:
```bash
srun  -p $PARTITION --cpus-per-task=8 --nodes=2 --ntasks-per-node=1 --gres=gpu:8 bash inference.sh 2
```
In this example, we initialize 2 nodes with a total of 16 GPUs for inference. Each node processes a portion of the video sequences in parallel, which significantly accelerates the overall inference process.
