# napari-sam2long
<!--A plugin for interactive 3D (volumetric or time-lapse) object segmentation with [Meta's Segment Anything Model 2](https://github.com/facebookresearch/sam2) (SAM 2) model.

This plugin is for researchers who need to sparsely segment 3D volumetric or time-lapse images. It supports tiffs in either ZYX or TYX format. User inputs can be either point clicks or manually drawn masks.

This tool uses the [SAM2Long](https://github.com/Mark12Ding/SAM2Long)  model, which is based on [Meta's SAM 2](https://github.com/facebookresearch/sam2) with adjustements to the memory module to improve performance on long videos. The plugin supports long videos but is still suitable for short videos. -->


A plugin for interactive 3D (volumetric or time-lapse) object segmentation using [Meta's Segment Anything Model 2](https://github.com/facebookresearch/sam2) (SAM 2). 

Designed for bioimaging researchers working with 3D volumetric or time-lapse images, this plugin supports TIFF files in ZYX or TYX format. Users can provide input and make corrections through point clicks or manually drawn masks.

The tool leverages the [SAM2Long](https://github.com/Mark12Ding/SAM2Long) model, an optimized version of [Meta's SAM 2](https://github.com/facebookresearch/sam2) with enhancements to the memory module for improved performance on long videos. It was built to support long videos, but it remains effective for shorter videos as well.


<!--The plugin supports long videos. User inputs can be either point clicks or manually drawn masks.-->

## Installation
Please see the official [SAM 2](https://github.com/facebookresearch/sam2) repo and the [INSTALL.md](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md) for notes and FAQs on potential installation issues.

1. Create a new conda environment and install napari:
    ```bash
    conda create -n napari-sam2long python==3.10
    conda activate napari-sam2long
    conda install -c conda-forge napari pyqt
    ```

2. Install PyTorch and TorchVision. Select preferences [here](https://pytorch.org/get-started/locally/) to find correct installation command.

    Example command can look like this:

    ```bash
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
    ```

3. Install SAM 2 using:
    ```bash
    git clone https://github.com/facebookresearch/sam2.git && cd sam2

    pip install -e .
    ```
4. Install napari-sam2long plugin via [pip]:
    ```bash
    pip install napari-sam2long
    ```

## Usage

### Segmenting & tracking first object
1. Open a 3D tiff in napari, make sure it is in TYX or ZYX format
2. Select the image in the drop-down menu of *Input*
3. Add a new [labels layer](https://napari.org/0.5.0/howtos/layers/labels.html) to the viewer and select it in the drop-down menu of *Labels* 
    Note: The labels layer should always be added to the viewer after the input image to match the dimensions.  
4. Select the *Model*
5. Click *Initialize* to load the image and initialize the inference state
6. Select an object on any frame and get an initial mask with
    - the *mouse middle click* to get the model's mask prediction
        (*mouse middle click* to add and *Ctrl+mouse middle click* to remove areas) and/or
    - napari's [labels layers tools](https://napari.org/0.5.0/howtos/layers/labels.html#gui-tools-for-the-labels-layer) (e.g. paintbrush, eraser etc.) to manually draw a mask

    Note: When the model fails to segment the desired object with the point prompts using *(Ctrl+) mouse middle click*, manually drawing/correcting the mask with napari's labels layer tools can be very useful
    
7. Once satisfied with the initial mask, click *Propagate from current frame* to obtain segmentations for all subsequent frames. The result will be added to the labels layer. 
    
    Note: *Propagate from current frame* computes the masklets only for the subsequent frames to reduce computation time and does not affect any masklets of the previous frames. Only the mask of the current frame propagation is started from is considered in the prediction, any prompts made in previous and subsequent frames are not regarded.
    
### Making corrections
8. Re-draw a new mask on any frame by using the *(Ctrl+) mouse middle click* to (remove) add regions and/or napari's labels layers tools.
9. *Propagate from current frame* to re-run the model's predictions with the new mask

Note: When making corrections and "re-defining" the masks, this plugin treats the corrected mask as a new initial mask and disregards any previous prompts on this frame. 

### Segmenting another object in the same image/video
10. Save labels layer with the segmentation result of previous object
11. Click *Reset* or add another labels layer to the viewer and select the new layer in the *Labels*-dropdown. Select new object as described in step 6.

###  Segment new image/video
12. *Reset* inference state
13. Load new image/video and follow instructions from step 1. *Initialize* is necessary to load the new image/video. 

## Issues
If you encounter any problems, please [file an issue] along with a detailed description.

[file an issue]: https://github.com/maihanhoang/napari-sam2long/issues

## License & Attribution

This project integrates code from:

- [SAM2](https://github.com/facebookresearch/sam2) by Meta ([`Apache 2.0 License`](LICENSE-Apache-2.0))
- [SAM2Long](https://github.com/Mark12Ding/SAM2Long) by Shuangrui Ding et al. ([`CC-BY-NC 4.0 License`](LICENSE-CC-BY-NC-4.0))
- [napari-samv2](https://github.com/Krishvraman/napari-SAMV2) by Krishnan Venkataraman ([`BSD-3 License`](LICENSE-BSD-3))


The following changes were made to SAM2Long:
- integrated SAM2Long into a napari plugin
- modified the video predictor to support the progress bar in the plugin


Since this project includes **SAM2Long**, it inherits the **CC-BY-NC 4.0 license**, meaning **commercial use is not allowed**.  

## Bibliography
[1]: Nikhila Ravi, Valentin Gabeur, Yuan-Ting Hu, Ronghang Hu, Chaitanya Ryali, Tengyu Ma, Haitham Khedr, Roman Rädle, Chloe Rolland, Laura Gustafson, Eric Mintun, Junting Pan, Kalyan Vasudev Alwala, Nicolas Carion, Chao-Yuan Wu, Ross Girshick, Piotr Dollár, & Christoph Feichtenhofer. (2024). SAM 2: Segment Anything in Images and Videos.
 
[2]: Ding, S., Qian, R., Dong, X., Zhang, P., Zang, Y., Cao, Y., Guo, Y., Lin, D., & Wang, J. (2024). SAM2Long: Enhancing SAM 2 for Long Video Segmentation with a Training-Free Memory Tree. arXiv preprint arXiv:2410.16268.

