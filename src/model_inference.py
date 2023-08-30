import torch
import numpy as np
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
    
    def display_io(self, array):
        rgb_image = np.stack((array[:, :, 5], array[:, :, 3], array[:, :, 2]), axis=-1)

        fig, ax = plt.subplots(1, 2, figsize=(16, 8))

        ax[0].imshow(rgb_image)
        ax[0].set_title("Input color composite (SWIR 2, Narrow NIR, Red)")
        ax[0].axis('off')

        ax[1].imshow(self.mask, cmap='gray')
        ax[1].set_title("Model prediction (Black: No burn scar; White: Burn scar)")
        ax[1].axis('off')
    

