'''
Timezones are defined per RFC822 5.1 (plus GMT and UTC),
with values representing offsets from UTC in milliseconds.
'''
import types

import synapse.exc as s_exc

_onehour = 3600000

_timezones = types.MappingProxyType({
    'A': -1 * _onehour,
    'CDT': -5 * _onehour,
    'CST': -6 * _onehour,
    'EDT': -4 * _onehour,
    'EST': -5 * _onehour,
    'GMT': 0,
    'M': -12 * _onehour,
    'MDT': -6 * _onehour,
    'MST': -7 * _onehour,
    'N': 1 * _onehour,
    'PDT': -7 * _onehour,
    'PST': -8 * _onehour,
    'UT': 0,
    'UTC': 0,
    'Y': 12 * _onehour,
    'Z': 0,
})

def getTzNames():
    '''
    Return a tuple of all supported timezone names.
    '''
    return tuple(_timezones.keys())

def getTzOffset(name, defval=None):
    '''
    Return tuple of the UTC offset in milliseconds and an info dict.
    '''
    try:
        return _timezones.get(name.upper(), defval), {}
    except AttributeError:
        raise s_exc.BadArg(mesg=f'Timezone name must a string') from None
