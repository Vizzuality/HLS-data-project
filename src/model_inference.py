import os
import subprocess

import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from mmcv import Config
from mmcv.parallel import collate, scatter
from mmseg.apis import init_segmentor
from mmseg.datasets.pipelines import Compose



class ModelProcessor:
    def __init__(self, config_path, ckpt, bands=None):
        self.config_path = config_path
        self.ckpt = ckpt
        self.bands = bands
        self._load_model()

    def _load_model(self):
        # Load model
        config = Config.fromfile(self.config_path)
        config.model.backbone.pretrained = None
        self.model = init_segmentor(config, self.ckpt)

        # Set model device
        self.device = next(self.model.parameters()).device
        self.cfg = self.model.cfg

        # Modify test pipeline if necessary
        self._modify_test_pipeline()

    def _modify_test_pipeline(self):
        custom_test_pipeline = self.cfg.data.test.pipeline

        if self.bands is not None:
            extract_index = [
                i for i, x in enumerate(custom_test_pipeline) if x["type"] == "BandsExtract"
            ]


            if len(extract_index) > 0:
                custom_test_pipeline[extract_index[0]]["bands"] = eval(self.bands)

            collect_index = [
                i for i, x in enumerate(custom_test_pipeline) if x["type"].find("Collect") > -1
            ]
            if len(collect_index) > 0:
                keys = [
                    "img_info",
                    "img",
                    "img_shape",
                    "ori_shape",
                    "pad_shape",
                    "scale_factor",
                    "img_norm_cfg",
                ]
                custom_test_pipeline[collect_index[0]]["meta_keys"] = keys

            # build the data pipeline
            self.test_pipeline = Compose(custom_test_pipeline)

    def predict(self, array):
        data = []
        img_data = {"img_info": {"array": array}}
        img_data = self.test_pipeline(img_data)
        data.append(img_data)

        data = collate(data, samples_per_gpu=1)
        if next(self.model.parameters()).is_cuda:
            data = scatter(data, [self.device])[0]
        else:
            img_metas = data["img_metas"].data[0]
            img = data["img"]
            data = {"img": img, "img_metas": img_metas}

        with torch.no_grad():
            result = self.model(return_loss=False, rescale=True, **data)

        self.mask = result[0]
        return self.mask
    
    @staticmethod
    def display_io(array, mask):
        rgb_image = np.stack((array[:, :, 5], array[:, :, 3], array[:, :, 2]), axis=-1)

        fig, ax = plt.subplots(1, 2, figsize=(16, 8))

        ax[0].imshow(rgb_image)
        ax[0].set_title("Input color composite (SWIR 2, Narrow NIR, Red)")
        ax[0].axis('off')

        ax[1].imshow(mask, cmap='gray')
        ax[1].set_title("Model prediction (Black: No burn scar; White: Burn scar)")
        ax[1].axis('off')

    @staticmethod
    def save_io_as_png(array, mask, folder_path, region_name):
        region_dir = os.path.join(folder_path, region_name)

        # Check if the folder exists
        if not os.path.exists(region_dir):
            # If the folder doesn't exist, create it
            os.makedirs(region_dir)
            print(f"Folder '{region_dir}' created.")
        else:
            print(f"Folder '{region_dir}' already exists.")

        # Save composite
        # Select bands
        rgb_image = array[..., [5, 3, 2]]

        # Saturate image
        rgb_image = rgb_image*2
        rgb_image = np.clip(rgb_image, 0, 1)

        # Scale the values to the range [0, 255]
        rgb_image = (rgb_image * 255).astype(np.uint8)

        # Convert the NumPy array to a PIL Image
        image = Image.fromarray(rgb_image)

        # Save the image as a PNG file 
        image.save(os.path.join(region_dir, f"{region_name}_001.png"))

        # Save mask
        # Create a copy of the RGB array to preserve the original data
        rgb_mask = np.copy(rgb_image)

        # Set RGB values to white where the mask is equal to 1
        mask_array = mask[..., np.newaxis]  # Add a new axis to match the RGB shape
        mask_array = np.repeat(mask_array, 3, axis=-1)  # Repeat the mask along the new axis to match RGB shape

        # Make the mask oixels white
        rgb_mask[mask_array == 1] = 255

        # Convert the NumPy array to a PIL Image for saving
        image = Image.fromarray(rgb_mask)

        # Save the image as a PNG file 
        image.save(os.path.join(region_dir, f"{region_name}_002.png"))


    @staticmethod
    def create_animation(folder_path, region_name, output_format = 'mp4'):
        region_dir = os.path.join(folder_path, region_name)

        if output_format == 'mp4':
            cmd = f"ffmpeg -framerate 1 -stream_loop 5 -i {region_dir}/{region_name}_%03d.png -c:v libx264 -crf 0 -y {region_dir}/{region_name}.mp4"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == 'apng':
            cmd = f"ffmpeg -framerate 3 -i {region_dir}/{region_name}_%03d.png -plays 0 -y {region_dir}/{region_name}.apng"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == 'gif':
            cmd = f"ffmpeg -framerate 1 -i {region_dir}/{region_name}_%03d.png -y {region_dir}/{region_name}.gif"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == 'webm':
            cmd = f"ffmpeg -framerate 1 -f image2 -i {region_dir}/{region_name}_%03d.png -c:v libvpx-vp9 -pix_fmt yuva420p -y {region_dir}/{region_name}.webm"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")



        
            

