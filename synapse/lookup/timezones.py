'''
Timezones are defined per RFC822 5.1 (plus GMT and UTC),
with values representing offsets from UTC in milliseconds.
'''

onehour = 3600000

timezones = {
    'Y': 12 * onehour,
    'N': 1 * onehour,
    'Z': 0,
    'UT': 0,
    'UTC': 0,
    'GMT': 0,
    'A': -1 * onehour,
    'EDT': -4 * onehour,
    'EST': -5 * onehour,
    'CDT': -5 * onehour,
    'CST': -6 * onehour,
    'MDT': -6 * onehour,
    'MST': -7 * onehour,
    'PDT': -7 * onehour,
    'PST': -8 * onehour,
    'M': -12 * onehour,
}

def getTimezones():
    return tuple(timezones.keys())

def getTzOffset(name, defval=None):
    if isinstance(name, str):
        return timezones.get(name.upper(), defval)
    return defval
