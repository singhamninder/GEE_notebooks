import ee


# --- inspired by awesome-spectral-indices and eemont---
# Extend Decorator
def extend(cls, static=False):
    """Extends the cls class."""
    if static:
        return lambda f: (setattr(cls, f.__name__, staticmethod(f)) or f)
    else:
        return lambda f: (setattr(cls, f.__name__, f) or f)


# Spectral Index Calculator Class ---
class SpectralIndexCalculator:
    """Universal spectral index processor for GEE"""

    INDEX_CATALOG = {
        "NDVI": {
            "formula": "(NIR - RED) / (NIR + RED)",
            "bands": {"NIR": "B8", "RED": "B4"},
            "reference": "https://doi.org/10.1016/S0176-1617(11)81633-0",
        },
        "EVI": {
            "formula": "2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)",
            "bands": {"NIR": "B8", "RED": "B4", "BLUE": "B2"},
            "reference": "https://doi.org/10.1016/S0034-4257(96)00112-5",
        },
        "kNDVI": {
            "formula": "tanh(((NIR - RED) / (2 * sigma)) ** 2)",
            "bands": {"NIR": "B8", "RED": "B4"},
            "params": {"sigma": 0.5},
            "reference": "https://doi.org/10.1126/sciadv.abc7447",
        },
    }

    def __init__(self, band_map=None):
        """
        Parameters
        ----------
        band_map : dict, optional
            Mapping from generic band names to sensor-specific names.
            Example: {'NIR': 'B8', 'RED': 'B4', 'SWIR': 'B11', 'BLUE': 'B2'}
        """
        self.band_map = band_map or {}

    def get_band(self, image, band):
        """Resolve band name using band_map or default."""
        return image.select(self.band_map.get(band, band))

    def compute_index(self, image, index_name, params=None):
        """Compute a single spectral index and add as band."""
        spec = self.INDEX_CATALOG[index_name]
        # Merge default and user params
        index_params = dict(spec.get("params", {}))
        if params:
            index_params.update(params)
        # Resolve bands
        bands = {k: self.get_band(image, v) for k, v in spec["bands"].items()}
        # Merge bands and params for expression
        expr_dict = {**bands, **index_params}
        # Compute and add band
        return image.addBands(
            image.expression(spec["formula"], expr_dict).rename(index_name)
        )

    def add_indices(self, image, indices, params=None):
        """Add multiple indices to a single image."""
        for idx in indices:
            image = self.compute_index(image, idx, params)
        return image


# Attach spectralIndices method to ee.ImageCollection
@extend(ee.ImageCollection)
def spectralIndices(self, indices, band_map=None, params=None):
    """
    Add spectral indices as bands to each image in the collection.
    Parameters
    ----------
    indices: list
        list of str (e.g., ['NDVI', 'EVI'])
    band_map: dict, optional.
        Map standard names to sensor bands.
    params: dict, optional.
        Extra parameters for indices (e.g., {'sigma': 0.7})
    Returns:
        ee.ImageCollection with new index bands.
    """
    calculator = SpectralIndexCalculator(band_map)
    return self.map(lambda img: calculator.add_indices(img, indices, params))
