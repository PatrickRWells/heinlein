from abc import abstractmethod, ABC
from . import region as reg
import numpy as np
from shapely import geometry

def Sampler(region):
    if type(region) == reg.PolygonRegion:
        return PolygonSampler(region)


class BaseSampler(ABC):

    def __init__(self, region, *args, **kwargs):
        self._region = region

    @abstractmethod
    def get_circular_sample(self, *args, **kwargs):
        pass


class PolygonSampler(BaseSampler):
    
    def __init__(self, region, *args, **kwargs):
        super().__init__(region)
        self.setup()

    def setup(self, *args, **kwargs):
        bounds = self._region.geometry.bounds
        ra1,ra2 = bounds[0], bounds[2]
        dec1, dec2 = bounds[1], bounds[3]
        ra_range = (min(ra1, ra2), max(ra1, ra2))
        dec_range = (min(dec1, dec2), max(dec1, dec2))
        phi_range = np.radians(ra_range)
        #Keeping everything in radians for simplicity
        #Convert from declination to standard spherical coordinates
        theta_range = (90. - dec_range[0], 90. - dec_range[1])
        #Area element on a sphere is dA = d(theta)d(cos[theta])
        #Sampling uniformly on the surface of a sphere means sampling uniformly
        #Over cos theta
        costheta_range = np.cos(np.radians(theta_range))
        self._low_sampler_range = [phi_range[0], costheta_range[0]]
        self._high_sampler_range = [phi_range[1], costheta_range[1]]
        self._sampler = np.random.default_rng()

        
    def get_circular_sample(self, radius, *args, **kwargs):
        vals = self._sampler.uniform(self._low_sampler_range, self._high_sampler_range)
        ra = np.degrees(vals[0])
        theta = np.degrees(np.arccos(vals[1]))
        dec = 90 - theta
        new_region = reg.Region.circle((ra,dec), radius)
        return new_region