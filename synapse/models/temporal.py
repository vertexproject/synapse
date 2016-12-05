import time
import datetime

import synapse.compat as s_compat

from synapse.lib.types import DataType

def getDataModel():
    return {
        'prefix':'time',
        'version':201611251045,

        'types':(
            ('time',{'ctor':'synapse.models.temporal.TimeType'}),
            ('time:epoch',{'ctor':'synapse.models.temporal.EpochType'}),

            ('time:min',{'subof':'time', 'ismin':1}),
            ('time:max',{'subof':'time', 'ismax':1}),
            ('time:epoch:min',{'subof':'time:epoch', 'ismin':1}),
            ('time:epoch:max',{'subof':'time:epoch', 'ismax':1}),
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

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

    def parse(self, text, oldval=None):

        text = text.strip().lower()
        text = (''.join([ c for c in text if c.isdigit() ]))[:17]

        tlen = len(text)
        if tlen == 4:
            st = time.strptime(text, '%Y')

        elif tlen == 6:
            st = time.strptime(text, '%Y%m')

        elif tlen == 8:
            st = time.strptime(text, '%Y%m%d')

        elif tlen == 10:
            st = time.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            st = time.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            st = time.strptime(text, '%Y%m%d%H%M%S')

        elif tlen in (15,16,17):
            st = time.strptime(text, '%Y%m%d%H%M%S%f')

        else:
            raise Exception('Unknown time format: %s' % text)

        e = datetime.datetime(1970,1,1)
        d = datetime.datetime(st.tm_year, st.tm_mon, st.tm_mday)

        millis = (d - e).microseconds / 1000
        millis += st.tm_hour*3600000
        millis += st.tm_min*60000
        millis += st.tm_sec*1000
        millis += st.microseconds / 1000

        return millis

    def repr(self, valu):
        dt = datetime.datetime(1970,1,1) + datetime.timedelta(microseconds=valu*1000)
        millis = dt.microsecond / 1000
        return '%d/%.2d/%.2d %.2d:%.2d:%.2d.%.3d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,millis)

class EpochType(DataType):

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

        if not s_compat.isint(valu):
            self._raiseBadValu(valu)

        if oldval != None and self.minmax:
            valu = self.minmax(valu,oldval)

        return valu

    def frob(self, valu, oldval=None):
        if s_compat.isstr(valu):
            return self.parse(valu, oldval=oldval)
        return self.norm(valu, oldval=oldval)

    def parse(self, text, oldval=None):

        text = text.strip().lower()
        text = (''.join([ c for c in text if c.isdigit() ]))[:14]

        tlen = len(text)
        if tlen == 4:
            st = time.strptime(text, '%Y')

        elif tlen == 6:
            st = time.strptime(text, '%Y%m')

        elif tlen == 8:
            st = time.strptime(text, '%Y%m%d')

        elif tlen == 10:
            st = time.strptime(text, '%Y%m%d%H')

        elif tlen == 12:
            st = time.strptime(text, '%Y%m%d%H%M')

        elif tlen == 14:
            st = time.strptime(text, '%Y%m%d%H%M%S')

        else:
            raise Exception('Unknown time format: %s' % text)

        e = datetime.datetime(1970,1,1)
        d = datetime.datetime(st.tm_year, st.tm_mon, st.tm_mday)

        epoch = int((d - e).total_seconds())
        epoch += st.tm_hour*3600
        epoch += st.tm_min*60
        epoch += st.tm_sec

        return epoch

    def repr(self, valu):
        dt = datetime.datetime(1970,1,1) + datetime.timedelta(seconds=int(valu))
        return '%d/%.2d/%.2d %.2d:%.2d:%.2d' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

