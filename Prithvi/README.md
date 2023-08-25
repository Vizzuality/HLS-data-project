# Image segmentation by [Prithvi](https://huggingface.co/ibm-nasa-geospatial/Prithvi-100M) model

This contains a example of the [Prithvi](https://huggingface.co/ibm-nasa-geospatial/Prithvi-100M) model. For the original repository check this [link](https://github.com/NASA-IMPACT/hls-foundation-os/tree/main). The example shows burn scars detection using the [NASA HLS fire scars dataset](https://huggingface.co/datasets/nasa-impact/hls_burn_scars).

## Setup
### Dependencies
1. Install torch (tested for >=1.7.1 and <=1.13.1) and torchvision (tested for >=0.8.2 and <=0.12). May vary with your system. Please check at: https://pytorch.org/get-started/previous-versions/.
    1. e.g.: `pip install torch==2.0.0+cu117 torchvision==0.15.1+cu117 torchaudio==2.0.1 --index-url https://download.pytorch.org/whl/cu117`
2. `pip install -e .`
3. `pip install -U openmim`
4. `mim install mmcv-full==1.6.2 -f https://download.openmmlab.com/mmcv/dist/{cuda_version}/{torch_version}/index.html`. Note that pre-built wheels (fast installs without needing to build) only exist for some versions of torch and CUDA. Check compatibilities here: https://mmcv.readthedocs.io/en/v1.6.2/get_started/installation.html
    1. e.g.: `pip install mmcv-full -f https://download.openmmlab.com/mmcv/dist/cu117/torch2.0.0/index.html`

### Data

The [NASA HLS fire scars dataset](https://huggingface.co/datasets/nasa-impact/hls_burn_scars) can be downloaded from Hugging Face.

## Checkpoints on Hugging Face
Checkpoints  can be also downloaded from Hugging Face for the [burn scars detection](https://huggingface.co/ibm-nasa-geospatial/Prithvi-100M-burn-scar).

## Running the inference
A script is provided to run inference on new data in GeoTIFF format. The data can be of any shape (e.g. height and width) as long as it follows the bands/channels of the original dataset. An example is shown below.

```
python burn_scar_model_inference.py -config ./configs/burn_scars_Prithvi_100M.py -ckpt ./checkpoints/burn_scars_Prithvi_100M.pth -input ../data/raw/burn_scars/ -output ../data/processed/burn_scars/ -input_type tif -bands "[0,1,2,3,4,5]"
```

The `bands` parameter is useful in case the files used to run inference have the data in different orders/indexes than the original dataset.

## Additional documentation
This model builds on [MMSegmentation](https://mmsegmentation.readthedocs.io/en/0.x/) and [MMCV](https://mmcv.readthedocs.io/en/v1.5.0/). For additional documentation, consult their docs.

