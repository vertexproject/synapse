import math

import synapse.lib.syntax as s_syntax

'''
Synapse module with helpers for geo-spacial calculations.
'''

# base geo distances will be in mm
r_mm = 6371008800.0
r_km = 6371.0088

def haversine(px, py, r=r_km):
    '''
    Calculate the haversine distance between two points
    defined by (lat,lon) tuples.

    Args:
        px ((float,float)): lat/long position 1
        py ((float,float)): lat/long position 2
        r (float): Radius of sphere

    Returns:
        (int):  Distance in km.
    '''
    lat1, lon1 = px
    lat2, lon2 = py

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return c * r

def dms2dec(d, m, s):
    '''
    Convert degrees, minutes, seconds lat/long form to degrees float.

    Args:
        d (int): Degrees
        m (int): Minutes
        s (int): Seconds

    Returns:
        (float): Degrees
    '''
    return d + (m / 60.0) + (s / 3600.0)
