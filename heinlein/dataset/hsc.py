from pathlib import Path
import numpy as np
from heinlein.locations import BASE_DATASET_CONFIG_DIR
from spherical_geometry.polygon import SingleSphericalPolygon
from heinlein.region import Region
import re
import math
import operator
import pickle


def setup(self, *args, **kwargs):
    reg = load_regions()
    self._regions = reg

def load_regions():
    support_location = Path(__file__).parents[0] / "configs" / "support"
    pickled_path = support_location / "hsc_regions.reg"
    if pickled_path.exists():
        with open(pickled_path, 'rb') as f:
            regions = pickle.load(f)
            return regions

    print("Nope!")
    support_location = BASE_DATASET_CONFIG_DIR / "support" / "hsc_tiles"
    files = [f for f in support_location.glob("*.txt") if not f.name.startswith(".")]
    regions = _load_region_data(files=files)
    return regions
    
def _load_region_data(files, *args, **kwargs):
    """
    Loads data about the tracts and patches for the given HSC field
    Used to split up data, making it easier to manage

    """
    output = np.empty(len(files), dtype=object)
    for i, file in enumerate(files):
        tracts = _parse_tractfile(file)
        tracts = _parse_tractdata(tracts, *args, **kwargs)
        field = np.hstack(np.array([np.array(t) for t in tracts.values()]))
        output[i] = field
    return np.hstack(output)


def _parse_tractfile(tractfile):
    tracts = {}
    with open(tractfile) as tf:
        for line in tf:
            if line.startswith('*'):
                continue

            nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
            tract_num = int(nums[0])
            patch = re.search("Patch", line)
            if patch is None:
                if tract_num not in tracts.keys():
                    tracts.update({tract_num: {'corners': [], 'type': 'tract', 'subregions': {} } } )
                if 'Corner' in line:
                    tracts[tract_num]['corners'].append((float(nums[-2]), float(nums[-1])))
                elif 'Center' in line:
                    tracts[tract_num].update({'center': (float(nums[-2]), float(nums[-1]))})

            else:
                patch = re.findall(r'\d,\d', line)
                patch_val = tuple(map(int, patch[0].split(',')))
                if patch_val not in tracts[tract_num]['subregions'].keys():
                    tracts[tract_num]['subregions'].update({patch_val: {'corners': [], 'type': 'patch'}})
                if 'Corner' in line:
                    tracts[tract_num]['subregions'][patch_val]['corners'].append((float(nums[-2]), float(nums[-1])))
                elif 'Center' in line:
                    tracts[tract_num]['subregions'][patch_val].update({'center': (float(nums[-2]), float(nums[-1]))})
    return tracts

def _parse_tractdata(tractdata, *args, **kwargs):
    output = {}
    try:
        wanted_tracts = kwargs['tracts']
    except:
        wanted_tracts = []
    for index, (name, tract) in enumerate(tractdata.items()):
        if wanted_tracts and name not in wanted_tracts:
                continue
        corners = tract['corners']
        center = tract['center']
        points = _parse_polygon_corners(center, corners)
        poly = SingleSphericalPolygon(points, center)
        region_obj = Region(poly, name=name)

        patches = {}
        for patchname, patch in tract['subregions'].items():
            patch_corners = patch['corners']
            patch_center = patch['center']
            patch_points = _parse_polygon_corners(patch_center, patch_corners)
            patch_name_parsed = _patch_tuple_to_int(patchname)
            patch_poly = SingleSphericalPolygon(patch_points, patch_center)
            patches.update({patch_name_parsed: Region(patch_poly, name=patch_name_parsed)})
        
        added = region_obj.add_subregions(patches, ignore_warnings = True)
        output.update({name: region_obj})
    return output

def _parse_polygon_corners(center, points):
    sorted_coords = sorted(points, key=lambda coord: (-135 - math.degrees(math.atan2(*tuple(map(operator.sub, coord, center))[::-1]))) % 360)

    #This ensures the points are ordered counter-clockwsie, to avoid twisted polygons
    #Shoutout to StackOverflow
    return sorted_coords


def _patch_tuple_to_int(patch_tuple):
    """
    Takes in a patch ID as a tuple and turns it into an int.
    This int can be used to look up objects in the catalof
    """
    if patch_tuple[0] == 0:
        return patch_tuple[1]
    else:
        return 100*patch_tuple[0] + patch_tuple[1]
