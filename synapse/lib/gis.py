import math
import regex

'''
Synapse module with helpers for earth based geospatial calculations.
'''

# DMS (degrees/minutes/seconds) coordinate pattern.
# Supports degree symbol (\u00b0), letter d, or implicit space separation.
# Supports apostrophe/prime chars (\u2032/\u2019) or letter m for minutes.
# Supports double-quote/double-prime chars (\u2033/\u201d) for seconds.
# Handles optional N/S/E/W direction prefix or suffix, and negative sign.
_dmsre = regex.compile(
    r'''^\s*
    (?P<dirpre>[NSEWnsew])?
    \s*
    (?P<neg>-)?
    \s*
    (?P<degs>\d+(?:\.\d+)?)
    \s*
    [\u00b0d]?
    \s*
    (?:
        (?P<mins>\d+(?:\.\d+)?)
        \s*
        ['\u2032\u2019m]?
        \s*
        (?:
            (?P<secs>\d+(?:\.\d+)?)
            \s*
            ["\u2033\u201d]?
            \s*
        )?
    )?
    (?P<dirsuf>[NSEWnsew])?
    \s*$''',
    regex.VERBOSE
)

# base earth geo distances will be in mm
r_mm = 6371008800.0
r_km = 6371.0088

# investigate perf impact of using WGS-84 ellipsoid for dist calc

def latlong(text):
    '''
    Chop a latlong string and return (float,float).
    Does not perform validation on the coordinates.

    Args:
        text (str):  A longitude,latitude string.

    Returns:
        (float,float): A longitude, latitude float tuple.
    '''
    nlat, nlon = text.split(',')
    return (float(nlat), float(nlon))

def near(point, dist, points):
    '''
    Determine if the given point is within dist of any of points.

    Args:
        point ((float,float)): A latitude, longitude float tuple.
        dist (int): A distance in mm ( base units )
        points (list): A list of latitude, longitude float tuples to compare against.
    '''
    for cmpt in points:
        if haversine(point, cmpt) <= dist:
            return True
    return False

def haversine(px, py, r=r_mm):
    '''
    Calculate the haversine distance between two points
    defined by (lat,lon) tuples.

    Args:
        px ((float,float)): lat/long position 1
        py ((float,float)): lat/long position 2
        r (float): Radius of sphere

    Returns:
        (int):  Distance in mm.
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

def bbox(lat, lon, dist):
    '''
    Calculate a min/max bounding box for the circle defined by lat/lon/dist.

    Args:
        lat (float): The latitude in degrees
        lon (float): The longitude in degrees
        dist (int): A distance in geo:dist base units (mm)

    Returns:
        (float,float,float,float): (latmin, latmax, lonmin, lonmax)
    '''
    latr = math.radians(lat)
    lonr = math.radians(lon)

    rad = r_mm
    prad = rad * math.cos(latr)

    latd = dist / rad
    lond = dist / prad

    latmin = math.degrees(latr - latd)
    latmax = math.degrees(latr + latd)
    lonmin = math.degrees(lonr - lond)
    lonmax = math.degrees(lonr + lond)

    return (latmin, latmax, lonmin, lonmax)

def dms2dec(degs, mins, secs):
    '''
    Convert degrees, minutes, seconds lat/long form to degrees float.

    Args:
        degs (int): Degrees
        mins (int): Minutes
        secs (int): Seconds

    Returns:
        (float): Degrees
    '''
    return degs + (mins / 60.0) + (secs / 3600.0)

def parseDMS(text):
    '''
    Parse a degrees/minutes/seconds coordinate string to decimal degrees.

    Supported formats include:
        45\u00b046\'52"N   (degree symbol, apostrophe, double-quote with direction)
        45d46m52N          (letter separators)
        45 46 52 N         (space separated)
        N45\u00b046\'52"   (direction prefix)
        -45\u00b046\'52"   (negative sign instead of direction)
        45\u00b046\'N      (degrees and minutes only)

    Args:
        text (str): A DMS coordinate string.

    Returns:
        (float): Decimal degrees.

    Raises:
        ValueError: If the string cannot be parsed as a DMS coordinate.
    '''
    m = _dmsre.match(text)
    if m is None:
        raise ValueError(f'Unable to parse DMS string: {text!r}')

    dirpre = m.group('dirpre')
    neg = m.group('neg')
    degs = float(m.group('degs'))
    mins = float(m.group('mins') or 0)
    secs = float(m.group('secs') or 0)
    dirsuf = m.group('dirsuf')

    direction = (dirpre or dirsuf or '').upper()

    if neg and direction in ('S', 'W'):
        raise ValueError(f'Conflicting negative sign and S/W direction in: {text!r}')

    if mins >= 60.0:
        raise ValueError(f'Invalid minutes value {mins} in: {text!r}')

    if secs >= 60.0:
        raise ValueError(f'Invalid seconds value {secs} in: {text!r}')

    result = dms2dec(degs, mins, secs)

    if neg or direction in ('S', 'W'):
        result = -result

    return result

def parseLatLong(text):
    '''
    Parse a DMS lat/long coordinate pair string into a (lat, lon) float tuple.

    Supports comma or semicolon as delimiter between lat and lon, or splits
    on a N/S direction indicator when no delimiter is present.

    Args:
        text (str): A DMS lat/long pair string (e.g. "45\u00b046\'52"N, 13\u00b030\'45"E").

    Returns:
        ((float, float)): A (latitude, longitude) decimal degrees tuple.

    Raises:
        ValueError: If the string cannot be parsed as a DMS lat/long pair.
    '''
    text = text.strip()

    for sep in (',', ';'):
        if sep in text:
            parts = text.split(sep, 1)
            return parseDMS(parts[0].strip()), parseDMS(parts[1].strip())

    # No delimiter: scan for N/S direction as the split boundary
    upper = text.upper()
    for i, c in enumerate(upper):
        if c in ('N', 'S') and i > 0:
            rest = text[i + 1:].strip()
            if rest:
                try:
                    lat = parseDMS(text[:i + 1].strip())
                    lon = parseDMS(rest)
                    return lat, lon
                except ValueError:
                    continue

    raise ValueError(f'Unable to parse DMS lat/long pair: {text!r}')
