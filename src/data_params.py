from dataclasses import dataclass


@dataclass
class GEEData:
    dataset: str

    @property
    def collection_id(self):
        return {'Sentinel_2': 'COPERNICUS/S2_SR_HARMONIZED',
                'Landsat_8': 'LANDSAT/LC08/C02/T1_L2',
                'Landsat_9': 'LANDSAT/LC09/C02/T1_L2'}[self.dataset]
    
    @property
    def swir_bands(self):
        return {'Sentinel_2': ['B12', 'B8', 'B4'],
                'Landsat_8': ['SR_B7', 'SR_B5', 'SR_B4'],
                'Landsat_9': ['SR_B7', 'SR_B5', 'SR_B4']}[self.dataset]
    
    @property
    def swir_vis(self):
        return {'Sentinel_2':{"min": 0.0, "max": 6000, "bands": self.swir_bands},
                'Landsat_8': {"min": 5000, "max": 30000, "bands": self.swir_bands},
                'Landsat_9': {"min": 5000, "max": 30000, "bands": self.swir_bands}}[self.dataset]