import os
import subprocess
import urllib.request
from netrc import netrc
from sys import platform

import ee
import matplotlib.pyplot as plt
import numpy as np
import pyproj
import rasterio as rio
from rasterio import mask
from ipywidgets import interact
from osgeo import gdal
from PIL import Image, ImageDraw, ImageFont
from shapely.ops import transform

from data_params import GEEData


class COGExtractor:
    def __init__(self, item, polygon):
        self.item = item
        self.polygon = polygon
        self.gdal_config()
        self.authenticate()

    def gdal_config(self):
        """GDAL configurations used to successfully access
        LP DAAC Cloud Assets via vsicurl"""
        try:
            # Set GDAL configurations
            gdal.SetConfigOption("GDAL_HTTP_COOKIEFILE", "~/cookies.txt")
            gdal.SetConfigOption("GDAL_HTTP_COOKIEJAR", "~/cookies.txt")
            gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
            gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "TIF")
            print("GDAL configurations set successfully.")
        except Exception as e:
            print("Failed to set GDAL configurations:", str(e))

    def authenticate(self):
        # Earthdata URL to call for authentication
        urs = "urs.earthdata.nasa.gov"

        # Determine if netrc file exists, and if it includes NASA Earthdata Login Credentials
        if "win" in platform:
            nrc = "../_netrc"
        else:
            nrc = "../.netrc"
        try:
            netrcDir = os.path.expanduser(f"{nrc}")
            netrc(netrcDir).authenticators(urs)[0]
            del netrcDir
            print("Authentication to NASA Earthdata Login credentials set successfully.")
        except FileNotFoundError:
            print(f"{nrc} file not found.")

    def polygon_utm(self, bands_crs):
        # Source coordinate system of the ROI
        geo_crs = pyproj.Proj("+proj=longlat +datum=WGS84 +no_defs", preserve_units=True)
        # Destination coordinate system
        utm = pyproj.Proj(bands_crs)  # Destination coordinate system
        project = pyproj.Transformer.from_proj(geo_crs, utm)  # Set up the transformation
        return transform(project.transform, self.polygon)

    def get_data(self, normalize=False):
        band_links = {}
        # Define which HLS product is being accessed
        if self.item["collection"] == "HLSS30.v2.0":
            bands = [
                "B12",
                "B11",
                "B8A",
                "B04",
                "B03",
                "B02",
            ]  # SWIR 2, SWIR 1, NIR, RED, GREEN, BLUE for S30
        else:
            bands = [
                "B07",
                "B06",
                "B05",
                "B04",
                "B03",
                "B02",
            ]  # SWIR 2, SWIR 1, NIR, RED, GREEN, BLUE for L30

        # Band names
        band_names = dict(zip(bands, ["swir_2", "swir_1", "nir", "red", "green", "blue"]))

        # Subset the assets in the item down to only the desired bands
        for a in self.item["assets"]:
            if any(b == a for b in bands):
                band_links[a] = self.item["assets"][a]["href"]

        # Use vsicurl to load the data directly into memory (be patient, may take a few seconds)
        band_metadata = {}
        for band_name, band_link in band_links.items():
            band_metadata[band_name] = rio.open(band_link)

        # Extract the data for the ROI and clip to that bbox
        band_data = {}
        bands_crs = band_metadata[bands[0]].crs
        for band_name, data in band_metadata.items():
            data, _transform = rio.mask.mask(data, [self.polygon_utm(bands_crs)], crop=True)
            band_data[band_name] = data.astype(float)

        # Set all nodata values to nan
        for band_name, data in band_data.items():
            band_data[band_name][band_data[band_name] == band_metadata[band_name].nodata] = np.nan

        # Grab scale factor from metadata and apply to each band
        self.band_scales = {}
        for band_name, data in band_data.items():
            if normalize:
                band_data[band_name] = band_data[band_name][0] * band_metadata[band_name].scales[0]
                self.band_scales[band_name] = 1
            else:
                band_data[band_name] = band_data[band_name][0]
                self.band_scales[band_name] = band_metadata[band_name].scales[0]

        # Rename bands
        band_data = {band_names[key]: value for key, value in band_data.items()}
        self.band_scales = {band_names[key]: value for key, value in self.band_scales.items()}

        return band_data

    @staticmethod
    def get_input_array(band_data):
        band_list = ["blue", "green", "red", "nir", "swir_1", "swir_2"]
        return np.stack(tuple([band_data[band] for band in band_list]), axis=-1)

    def display_composites(self, band_data):
        fig, ax = plt.subplots(1, 2, figsize=(16, 8))

        # Display the RGB image using the first axes
        rgb_image = np.stack((band_data["swir_2"] * self.band_scales["swir_2"], 
                              band_data["nir"] * self.band_scales["nir"], 
                              band_data["red"] * self.band_scales["red"]), axis=-1)

        ax[0].imshow(rgb_image)
        ax[0].set_title("Color composite (SWIR 2, Narrow NIR, Red)")
        ax[0].axis("off")

        # Display another image using the second axes
        rgb_image = np.stack((band_data["swir_1"] * self.band_scales["swir_1"], 
                              band_data["nir"] * self.band_scales["nir"], 
                              band_data["red"] * self.band_scales["red"]), axis=-1)

        ax[1].imshow(rgb_image)
        ax[1].set_title("Color composite (SWIR 1, Narrow NIR, Red)")
        ax[1].axis("off")

        plt.tight_layout()  # Ensure proper spacing between subplots
        plt.show()


class GEEExtractor:
    def __init__(self, images, geometry):
        ee.Initialize()
        self.images = images
        self.geometry = geometry
        # Area of Interest
        self.region = self.geometry.get("features")[0].get("geometry").get("coordinates")

    def get_composites(self, scale=30, dimensions=None, alpha_channel=False):
        """
        Create Numpy array with 1 composite per year.
        ----------
        dimensions : int
            A number or pair of numbers in format WIDTHxHEIGHT Maximum dimensions of the thumbnail to render, in pixels. If only one number is passed, it is used as the maximum, and the other dimension is computed by proportional scaling.
        alpha_channel : Boolean
            If True adds transparency
        """

        self.dates = []
        self.instruments = []
        for n, (date, image_dict) in enumerate(self.images.items()):
            self.dates.append(date)
            instrument, image = list(image_dict.items())[0]
            self.instruments.append(instrument)

            gee_data = GEEData(instrument)

            if dimensions:
                image = image.reproject(crs="EPSG:4326", scale=self.scale)
                visSave = {
                    "dimensions": dimensions,
                    "format": "png",
                    "crs": "EPSG:3857",
                    "region": self.region,
                }
            else:
                visSave = {"scale": scale, "region": self.region, "crs": "EPSG:3857"}

            # Get thumbnail url
            thumbnail_url = image.visualize(**gee_data.swir_vis).getThumbURL(visSave)

            # Open the URL and read the image using PIL
            with urllib.request.urlopen(thumbnail_url) as response:
                array = np.array(Image.open(response))

            array = array.reshape((1,) + array.shape)

            # Add alpha channel if needed
            if alpha_channel and array.shape[3] == 3:
                array = np.append(
                    array, np.full((array.shape[0], array.shape[1], array.shape[2], 1), 255), axis=3
                )
                if n == 0:
                    composites = array[:, :, :, :4]
                else:
                    composites = np.append(composites, array[:, :, :, :4], axis=0)
            else:
                if n == 0:
                    composites = array[:, :, :, :3]
                else:
                    composites = np.append(composites, array[:, :, :, :3], axis=0)

        return composites

    def _add_text(self, img, text, y_pixels=40, y_offset=40):
        np_img = np.array(img)
        img = Image.fromarray(np_img.astype(np.uint8))

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype("../data/raw/Roboto-Regular.ttf", y_pixels + 10)
        draw.text((int(y_pixels / 5), y_offset), str(text), (255, 255, 255), font=font)

        return np.array(img)

    def add_text(self, composites):
        for n, image in enumerate(composites):
            img = Image.fromarray(image.astype(np.uint8))
            # Add instrument
            instrument = self.instruments[n]
            gee_data = GEEData(instrument)
            img = self._add_text(img, text=gee_data.title, y_pixels=40, y_offset=10)

            # Add date
            date = self.dates[n].replace("-", "/")
            img = self._add_text(img, text=date, y_pixels=40, y_offset=80)

            composites[n, :] = np.array(img)

        return composites

    @staticmethod
    def display_composites(video):
        @interact(frame=(0, video.shape[0] - 1))
        def show_frame(frame=0):
            fig, ax = plt.subplots(1, 1, figsize=(10, 10))

            ax.imshow(video[frame, :, :, :])
            ax.set_title("Color composite (SWIR 2, Narrow NIR, Red)")
            ax.axis("off")

        plt.tight_layout()  # Ensure proper spacing between subplots
        plt.show()

    @staticmethod
    def save_frames_as_pngs(video, folder_path, region_name):
        region_dir = os.path.join(folder_path, region_name)

        # Check if the folder exists
        if not os.path.exists(region_dir):
            # If the folder doesn't exist, create it
            os.makedirs(region_dir)
            print(f"Folder '{region_dir}' created.")
        else:
            print(f"Folder '{region_dir}' already exists.")

        # Iterate through the frames and save each as a PNG image
        for frame_index in range(video.shape[0]):
            # Extract the frame as a 3D array (height x width x channels)
            frame = video[frame_index, :, :, :]

            # Create a PIL Image from the frame
            image = Image.fromarray(frame)

            # Define the file name for the PNG image (e.g., "frame_0.png", "frame_1.png", etc.)
            file_name = f"frame_{frame_index}.png"

            # Save the image as a PNG
            image.save(os.path.join(region_dir, region_name + f"_{frame_index:03d}.png"))

            print(f"Saved {file_name}")

        print("All frames saved as PNG images.")

    @staticmethod
    def create_animation(folder_path, region_name, output_format="mp4"):
        region_dir = os.path.join(folder_path, region_name)

        if output_format == "mp4":
            cmd = f"ffmpeg -framerate 1 -i {region_dir}/{region_name}_%03d.png -c:v libx264 -crf 0 -y {region_dir}/{region_name}.mp4"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == "apng":
            cmd = f"ffmpeg -framerate 3 -i {region_dir}/{region_name}_%03d.png -plays 0 -y {region_dir}/{region_name}.apng"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == "gif":
            cmd = f"ffmpeg -framerate 1 -i {region_dir}/{region_name}_%03d.png -y {region_dir}/{region_name}.gif"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
        if output_format == "webm":
            cmd = f"ffmpeg -framerate 1 -f image2 -i {region_dir}/{region_name}_%03d.png -c:v libvpx-vp9 -pix_fmt yuva420p -y {region_dir}/{region_name}.webm"
            print(f"Processing: {cmd}")
            r = subprocess.call(cmd, shell=True)
            if r == 0:
                print("Task created")
            else:
                print("Task failed")
            print("Finished processing")
