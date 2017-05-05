import datetime

import synapse.compat as s_compat

from synapse.lib.types import DataType

def getDataModel():
    return {
        'prefix':'time',
        'version':201611251045,

        'types':(
            ('time',{'ctor':'synapse.models.temporal.TimeType','doc':'Timestamp in milliseconds since epoch','ex':'20161216084632'}),
            ('time:epoch',{'ctor':'synapse.models.temporal.EpochType','doc':'Timestamp in seconds since epoch (deprecated)','ex':'20161216084632'}),

            ('time:min',{'subof':'time', 'ismin':1, 'doc':'Minimum time in millis since epoch'}),
            ('time:max',{'subof':'time', 'ismax':1, 'doc':'Maximum time in millis since epoch'}),
            ('time:epoch:min',{'subof':'time:epoch', 'ismin':1,'doc':'Minimum time in seconds (depricated)'}),
            ('time:epoch:max',{'subof':'time:epoch', 'ismax':1,'doc':'Maximum time in seconds (depricated)'}),
        ),
    }

class TimeType(DataType):

    # FIXME subfields for various time parts (year,month,etc)

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.ismin = info.get('ismin',False)
        self.ismax = info.get('ismax',False)

        self.minmax = None

        if self.ismin:
            self.minmax = min

        elif self.ismax:
            self.minmax = max

    def norm(self, valu, oldval=None):

        subs = {}

        # make the string into int form then apply our min/max
        if s_compat.isstr(valu):
            valu,subs = self._norm_str(valu,oldval=oldval)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu,subs

    def _norm_str(self, text, oldval=None):

        text = text.strip().lower()
        text = (''.join([ c for c in text if c.isdigit() ]))

        tlen = len(text)
        if tlen == 4:
            dt = datetime.datetime.strptime(text, '%Y')

        elif tlen == 6:
            dt = datetime.datetime.strptime(text, '%Y%m')

        elif tlen == 8:
            dt = datetime.datetime.strptime(text, '%Y%m%d')

        elif tlen == 10:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S')

        elif tlen in (15,16,17):
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S%f')

        else:
            self._raiseBadValu(text, mesg='Unknown time format')

        epoch = datetime.datetime(1970,1,1)
        return int((dt - epoch).total_seconds() * 1000),{}

    def repr(self, valu):
        dt = datetime.datetime(1970,1,1) + datetime.timedelta(milliseconds=valu)
        millis = dt.microsecond / 1000
        return '%d/%.2d/%.2d %.2d:%.2d:%.2d.%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,millis)

class EpochType(DataType):

    def __init__(self, tlib, name, **info):
        DataType.__init__(self, tlib, name, **info)

        self.ismin = self.get('ismin',0)
        self.ismax = self.get('ismax',0)

        self.minmax = None

        if self.ismin:
            self.minmax = min

        elif self.ismax:
            self.minmax = max

    def norm(self, valu, oldval=None):

        if s_compat.isstr(valu):
            return self._norm_str(valu,oldval=oldval)

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu,{}

    def _norm_str(self, text, oldval=None):

        text = text.strip().lower()
        text = (''.join([ c for c in text if c.isdigit() ]))

        tlen = len(text)
        if tlen == 4:
            dt = datetime.datetime.strptime(text, '%Y')

        elif tlen == 6:
            dt = datetime.datetime.strptime(text, '%Y%m')

        elif tlen == 8:
            dt = datetime.datetime.strptime(text, '%Y%m%d')

        elif tlen == 10:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            dt = datetime.datetime.strptime(text, '%Y%m%d%H%M%S')

        else:
            self._raiseBadValu(text, mesg='Unknown time format')

        epoch = datetime.datetime(1970,1,1)

        valu = int((dt-epoch).total_seconds())
        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu,{}

    def repr(self, valu):
        dt = datetime.datetime(1970,1,1) + datetime.timedelta(seconds=int(valu))
        return '%d/%.2d/%.2d %.2d:%.2d:%.2d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

def fromUnixEpoch(valu):
    if s_compat.isstr(valu):
        valu =int(valu,0)
    return valu * 1000

def addCoreOns(core):
    core.addTypeCast('from:unix:epoch',fromUnixEpoch)

