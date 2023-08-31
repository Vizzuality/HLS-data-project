import os
from sys import platform

import pyproj
import numpy as np
from osgeo import gdal
from netrc import netrc
import rasterio as rio
from rasterio.mask import mask
from shapely.ops import transform
import matplotlib.pyplot as plt


class COGExtractor:
    def __init__(self, item, polygon):
        self.item = item
        self.polygon = polygon
        self.gdal_config()
        self.authenticate()

    def gdal_config(self):
        """GDAL configurations used to successfully access LP DAAC Cloud Assets via vsicurl"""
        try:
            # Set GDAL configurations
            gdal.SetConfigOption('GDAL_HTTP_COOKIEFILE', '~/cookies.txt')
            gdal.SetConfigOption('GDAL_HTTP_COOKIEJAR', '~/cookies.txt')
            gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
            gdal.SetConfigOption('CPL_VSIL_CURL_ALLOWED_EXTENSIONS', 'TIF')
            print("GDAL configurations set successfully.")
        except Exception as e:
            print("Failed to set GDAL configurations:", str(e))

    def authenticate(self):
        # Earthdata URL to call for authentication
        urs = 'urs.earthdata.nasa.gov'   

        # Determine if netrc file exists, and if it includes NASA Earthdata Login Credentials
        if 'win' in platform:
            nrc = '../_netrc'
        else:
            nrc = '../.netrc'
        try:
            netrcDir = os.path.expanduser(f"{nrc}")
            netrc(netrcDir).authenticators(urs)[0]
            del netrcDir
            print("Authentication to NASA Earthdata Login credentials set successfully.")
        except FileNotFoundError:
            print(f"{nrc} file not found.")


    def polygon_utm(self, bands_crs):
        # Source coordinate system of the ROI
        geo_crs = pyproj.Proj('+proj=longlat +datum=WGS84 +no_defs', preserve_units=True)  
        # Destination coordinate system
        utm = pyproj.Proj(bands_crs)                                                  # Destination coordinate system
        project = pyproj.Transformer.from_proj(geo_crs, utm)                        # Set up the transformation
        return transform(project.transform, self.polygon)  

    def get_data(self):
        band_links = {}
        # Define which HLS product is being accessed
        if self.item['collection'] == 'HLSS30.v2.0':
            bands = ['B12', 'B11', 'B8A', 'B04', 'B03', 'B02'] # SWIR 2, SWIR 1, NIR, RED, GREEN, BLUE for S30
        else:
            bands = ['B07', 'B06', 'B05', 'B04' 'B03', 'B02'] # SWIR 2, SWIR 1, NIR, RED, GREEN, BLUE for L30

        # Band names
        band_names = dict(zip(bands, ["swir_2", "swir_1", "nir", "red", "green", "blue"]))


        # Subset the assets in the item down to only the desired bands
        for a in self.item['assets']: 
            if any(b == a for b in bands):
                band_links[a] = self.item['assets'][a]['href']

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
        for band_name, data in band_data.items():
            band_data[band_name] = band_data[band_name][0] * band_metadata[band_name].scales[0]

        # Rename bands
        band_data = {band_names[key]: value for key, value in band_data.items()}
                
        return band_data
    
    @staticmethod
    def get_input_array(band_data):
        band_list = ['blue', 'green', 'red', 'nir', 'swir_1', 'swir_2']
        return np.stack(tuple([band_data[band] for band in band_list]), axis=-1)

 
    @staticmethod
    def display_composites(band_data):
        fig, ax = plt.subplots(1, 2, figsize=(16, 8))

        # Display the RGB image using the first axes
        rgb_image = np.stack((band_data['swir_2'], band_data['nir'], band_data['red']), axis=-1)

        ax[0].imshow(rgb_image)
        ax[0].set_title("Color composite (SWIR 2, Narrow NIR, Red)")
        ax[0].axis('off')

        # Display another image using the second axes
        rgb_image = np.stack((band_data['swir_1'], band_data['nir'], band_data['red']), axis=-1)

        ax[1].imshow(rgb_image)
        ax[1].set_title("Color composite (SWIR 1, Narrow NIR, Red)")
        ax[1].axis('off')

        plt.tight_layout()  # Ensure proper spacing between subplots
        plt.show()



