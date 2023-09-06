import requests

import matplotlib.pyplot as plt
from skimage import io
import ee
import urllib.request
from PIL import Image
import numpy as np

from data_params import GEEData


class CMRSTACCatalog:
    # Class variables
    stac_endpoint = 'https://cmr.earthdata.nasa.gov/stac'
    catalog = 'LPCLOUD'
    collections = ["HLSS30.v2.0", "HLSL30.v2.0"]
    search_endpoint = f"{stac_endpoint}/{catalog}/search"
    
    def __init__(self):
        self.session = requests.Session()

    def create_search_params(self, bbox, start_date, end_date, limit):
        datetime_range = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

        params = {}
        params['limit'] = limit
        params['bbox'] = bbox
        params['datetime'] = datetime_range
        params["collections"] = self.collections
        return params
    
    def search(self, bbox, start_date, end_date, limit=12):
        params = self.create_search_params(bbox, start_date, end_date, limit)
        response = self.session.post(self.search_endpoint, json=params)
        if response.status_code == 200:
            return response.json()['features']
        else:
            response.raise_for_status()

    @staticmethod
    def display_rgb_images(items):
        num_items = len(items)
        max_images_per_row = 4
        num_rows = (num_items + max_images_per_row - 1) // max_images_per_row
        num_cols = min(num_items, max_images_per_row)
        
        fig, ax = plt.subplots(num_rows, num_cols, figsize=(num_cols * 4, num_rows * 4))
        ax = ax.ravel()  # Flatten the 2D array of axes
        
        for i, item in enumerate(items):
            image_url = item['assets']['browse']['href']
            image = io.imread(image_url)

            datetime = item['properties']['datetime']
            
            ax[i].imshow(image)
            ax[i].set_title(datetime)
            ax[i].axis('off')

        # Remove any remaining empty subplots
        for j in range(len(items), num_rows * num_cols):
            fig.delaxes(ax[j])
        
        plt.tight_layout()
        plt.show()


class GEECatalog:
    # Class variables
    instruments = ['Sentinel_2', 'Landsat_8', 'Landsat_9']
    
    def __init__(self):
        ee.Initialize()

    #def _add_date(self, image):
    #    """Function to add date property to an image"""
    #    return image.addBands(ee.Image.constant(ee.Date(image.get('system:time_start')).millis()).rename('date'))
    
    def _add_date(self, image):
        """Function to add date property to an image in 'YYYY-MM-dd' format"""
        date_format = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd')
        return image.set('date', date_format)
    
    def search_images(self, geometry, start_date, end_date):
        # Define the region of interest (ROI) as a polygon
        self.roi = ee.Geometry.Polygon(geometry['features'][0]['geometry']['coordinates'])

        # Get images
        images = {}
        for instrument in self.instruments:
            gee_data = GEEData(instrument)
            
            # Get collection
            collection = ee.ImageCollection(gee_data.collection_id)\
            .filterDate(start_date, end_date)\
            .filterBounds(self.roi)

            # Map the function over the collection
            collection = collection.map(self._add_date)

            # Get the list of images
            image_list = collection.toList(collection.size())

            date_images = {}
            pre_date = ''
            for i in range(collection.size().getInfo()):
                image = ee.Image(image_list.get(i))
                date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
                if date == pre_date:
                    images_list.append(image)
                    # Create an image collection from the list of images
                    image_collection = ee.ImageCollection.fromImages(images_list)
                    # Create a composite image from the image collection using mosaic
                    composite_image = image_collection.mosaic()
                    # Add composite image to dict
                    date_images[date] = composite_image
                else: 
                    # Add image to dict
                    date_images[date] = image

                    images_list = [image]
                    pre_date = date

            images[instrument] = date_images

        # Reorder images 
        images_dict = {}

        # Iterate through the original dictionary
        for instrument, date_image_dict in images.items():
            for date, image in date_image_dict.items():
                if date not in images_dict:
                    images_dict[date] = {}
                images_dict[date][instrument] = image


        # Sort the images by date
        images_dict = dict(sorted(images_dict.items()))

        return images_dict
    
    def display_thumbnails(self, images_dict):
        num_items = len(images_dict)
        max_images_per_row = 4
        num_rows = (num_items + max_images_per_row - 1) // max_images_per_row
        num_cols = min(num_items, max_images_per_row)

        fig, ax = plt.subplots(num_rows, num_cols, figsize=(num_cols * 4, num_rows * 4))
        ax = ax.ravel()  # Flatten the 2D array of axes

        for i, (date, image_dict) in enumerate(images_dict.items()):
            instrument, image = list(image_dict.items())[0]
            gee_data = GEEData(instrument)

            # Get the thumbnail URL
            thumbnail_url = image.visualize(**gee_data.swir_vis).getThumbURL({
                'dimensions': 500, 
                'format': 'png',
                'crs': 'EPSG:3857', 
                'region':self.roi     
            })

            # Open the URL and read the image using PIL
            with urllib.request.urlopen(thumbnail_url) as response:
                thumbnail =  np.array(Image.open(response))

            # display image
            ax[i].imshow(thumbnail)
            ax[i].set_title(f"{instrument}: {date}")
            ax[i].axis('off')

        # Remove any remaining empty subplots
        for j in range(len(images_dict), num_rows * num_cols):
            fig.delaxes(ax[j])
        
        plt.tight_layout()
        plt.show()

