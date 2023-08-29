import requests

import matplotlib.pyplot as plt
from skimage import io

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