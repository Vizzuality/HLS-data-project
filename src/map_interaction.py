import warnings
from typing import List

import ipyleaflet as ipyl
from shapely.geometry import Polygon


class LeafletMap(ipyl.Map):
    """
    A custom Map class.

    Inherits from ipyl.Map class.
    """

    def __init__(self, center: List[float] = [28.3904, -16.4409], zoom: int = 10, **kwargs):
        """
        Constructor for MapGEE class.

        Parameters:
        center: list, default [25.0, 55.0]
            The current center of the map.
        zoom: int, default 3
            The current zoom value of the map.
        **kwargs: Additional arguments that are passed to the parent constructor.
        """
        self.center = center
        self.zoom = zoom
        super().__init__(
            basemap=ipyl.basemap_to_tiles(ipyl.basemaps.Esri.WorldImagery),
            center=tuple(self.center), zoom=self.zoom, **kwargs)

        self.add_draw_control()

    def add_draw_control(self):
        control = ipyl.LayersControl(position='topright')
        self.add_control(control)

        print('Draw a rectangle on map to select and area.')

        draw_control = ipyl.DrawControl()

        draw_control.rectangle = {
            "shapeOptions": {
                "color": "#2BA4A0",
                "fillOpacity": 0,
                "opacity": 1
            }
        }

        feature_collection = {
            'type': 'FeatureCollection',
            'features': []
        }

        def handle_draw(self, action, geo_json):
            """Do something with the GeoJSON when it's drawn on the map"""    
            #feature_collection['features'].append(geo_json)
            if 'pane' in list(geo_json['properties']['style'].keys()):
                feature_collection['features'] = []
            else:
                feature_collection['features'] = [geo_json]

        draw_control.on_draw(handle_draw)

        self.add_control(draw_control)

        self.geometry = feature_collection

    @property
    def polygon(self):
        if not self.geometry['features']:
            warnings.warn("Rectangle hasn't been drawn yet. Bounding box is not available.")
            return None

        coordinates = self.geometry['features'][0]['geometry']['coordinates']
        return Polygon(coordinates[0])

    @property
    def bbox(self):
        if not self.polygon:
            warnings.warn("Rectangle hasn't been drawn yet. Bounding box is not available.")
            return None
        
        return list(self.polygon.bounds)
