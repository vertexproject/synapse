import os
import enum
import time
import heapq
import asyncio
import logging
import calendar
import datetime
from collections.abc import Iterable, Mapping
import itertools
from datetime import timezone as tz

import synapse.exc as s_exc
import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# A time that sorts past all reasonable times


def _dayofmonth(hardday, month, year):
    '''
    Returns a valid day of the month given the desired value.

    Negative values are interpreted as offset backwards from the last day of the month, with -1 representing the
    last day of the month.  Out-of-range values are clamped to the first or last day of the month.
    '''
    newday = hardday
    daysinmonth = calendar.monthrange(year, month)[1]
    if newday < 0:
        newday = daysinmonth + hardday + 1
    newday = max(1, min(newday, daysinmonth))
    return newday

# Manages running one-shot and periodic tasks in the future ("appointments")
class TimeUnit(enum.IntEnum):
    '''
    Different time units repeating appointments can be specified
    '''
    YEAR = enum.auto()
    MONTH = enum.auto()
    DAYOFMONTH = enum.auto()  # e.g. every 3rd of the month
    DAYOFWEEK = enum.auto()   # e.g. every Tuesday (Mon=0, Sun=6)
    DAY = enum.auto()         # every day
    HOUR = enum.auto()
    MINUTE = enum.auto()

_NextUnitMap = {
    TimeUnit.YEAR: None,
    TimeUnit.MONTH: TimeUnit.YEAR,
    TimeUnit.HOUR: TimeUnit.DAY,
    TimeUnit.MINUTE: TimeUnit.HOUR,
    TimeUnit.DAYOFMONTH: TimeUnit.DAYOFMONTH,
    TimeUnit.DAYOFWEEK: TimeUnit.DAYOFWEEK,
}

_TimeunitToDatetime = {
    TimeUnit.YEAR: 'year',
    TimeUnit.MONTH: 'month',
    TimeUnit.DAYOFMONTH: 'day',
    TimeUnit.DAYOFWEEK: 'day',
    TimeUnit.DAY: 'day',
    TimeUnit.HOUR: 'hour',
    TimeUnit.MINUTE: 'minute',
}

class ApptRec:
    '''
    Represents a single element of a single combination of an appointment
    '''
    def __init__(self, reqdict, incunit=None, incval=1):
        self.reqdict = reqdict
        self.incunit = incunit
        self.incval = incval if incunit is not None else None

        if not reqdict and incunit is None:
            raise s_exc.BadTime('reqdict must be nonempty or incunit must be non-None')

        if TimeUnit.DAY in reqdict:
            raise s_exc.BadTime('Must not specify day as requirement')

        if incunit == TimeUnit.MONTH and (TimeUnit.DAYOFMONTH in reqdict or TimeUnit.DAYOFWEEK in reqdict):
            # There's more than one way to interpret this, so disallow all
            raise s_exc.BadTime('Requiring day of month only compatible with year increment')

        if TimeUnit.DAYOFMONTH in reqdict and TimeUnit.DAYOFWEEK in reqdict:
            raise s_exc.BadTime('Both day of month and day of week must not both be requirements')

        if TimeUnit.DAYOFWEEK in reqdict and incunit is not None:
            raise s_exc.BadTime('Day of week requirement not supported with an increment')

        if TimeUnit.YEAR in reqdict:
            if not 1970 < reqdict[TimeUnit.YEAR] < 3000:
                raise s_exc.BadTime('Year out of bounds')
        # FIXME add all bounds checks

        # and incval > 0 for several

        self.reqdict = {}

        if incunit is not None:
            for reqtime in reqdict:
                if reqtime not in TimeUnit:
                    raise s_exc.BadTime('Keys of reqdict parameter  must be valid TimeUnits')
                if reqtime <= incunit:
                    # We could, actually support this, but most of these combinations are nonsensical (e.g. run every 5
                    # minutes in 2018 only?)
                    raise s_exc.BadTime('Must not have fixed unit equal to or greater than variable unit')

        # Put keys in size order, with dayof... added last, as nexttime processes in that order
        for key in _NextUnitMap:
            if key in reqdict:
                self.reqdict[key] = reqdict[key]

    def __repr__(self):
        return repr(self.entupl())

    def entupl(self):
        return (self.reqdict, self.incunit, self.incval)

    @classmethod
    def untupl(cls, val):
        return cls(*val)

    def nexttime(self, lastts):
        '''
        Returns next timestamp that meets requirements, incrementing by self.incunit, incval if not increasing, or
        0.0 if there are no future k
        '''
        lastdt = datetime.datetime.fromtimestamp(lastts, tz.utc)
        newvals = {}  # all the new fields that will be changed in the

        newdt = lastdt.replace()

        for unit, newval in self.reqdict.items():
            dtkey = _TimeunitToDatetime[unit]
            if unit is TimeUnit.DAYOFMONTH:
                newdt = newdt.replace(**newvals)
                newvals = {}
                newval = _dayofmonth(newval, newdt.month, newdt.year)
            elif unit is TimeUnit.DAYOFWEEK:
                newdt = newdt.replace(**newvals)
                newvals = {}
                newval = newdt.day + (6 + newval - newdt.weekday()) % 7 + 1
                if newval > calendar.monthrange(newdt.year, newdt.month)[1]:
                    newval -= 7
            elif unit is TimeUnit.MONTH:
                # As we change the month, clamp the day of the month to a valid value
                newdt = newdt.replace(**newvals)
                newvals = {}
                newday = _dayofmonth(newdt.day, newval, newdt.year)
                newvals['day'] = newday

            newvals[dtkey] = newval

        newdt = newdt.replace(**newvals)

        # Then move forward if we have to
        if newdt <= lastdt or \
                self.incunit == TimeUnit.DAYOFMONTH and newdt.day != self.incval or \
                self.incunit == TimeUnit.DAYOFWEEK and newdt.weekday() != self.incval:
            if self.incunit is None:
                largest_req = min(self.reqdict.keys())
                tmpunit = _NextUnitMap[largest_req]
                if tmpunit is None:  # required a year and we're already there
                    return 0.0
                # Unless we're going to the next day of month or day of week, increment by 1 unit of the next larger
                # unit
                tmpincval = self.reqdict.get(TimeUnit.DAYOFWEEK, self.reqdict.get(TimeUnit.DAYOFMONTH, 1))
            else:
                tmpunit = self.incunit
                tmpincval = self.incval
            newdt = self._inc(tmpunit, tmpincval, lastdt, newdt)
            assert newdt > lastdt
        print(newdt)
        return newdt.timestamp()

    def _inc(self, incunit, incval, origdt, dt):
        '''
        Return a datetime incremented by the incunit
        '''
        if incunit == TimeUnit.YEAR:
            return dt.replace(year=dt.year + incval)
        if incunit == TimeUnit.MONTH:
            newyear = dt.year
            absmonth = dt.month + incval - 1
            newmonth = absmonth % 12 + 1
            newyear += absmonth // 12
            daysinmonth = calendar.monthrange(newyear, newmonth)[1]
            newday = min(daysinmonth, dt.day)
            return dt.replace(day=newday, month=newmonth, year=newyear)
        if incunit == TimeUnit.DAY:
            return dt + datetime.timedelta(days=incval)
        if incunit == TimeUnit.DAYOFWEEK:
            # incval in this case means next day of week whose weekday matches incval (0-6)
            days = (6 + incval - dt.weekday()) % 7 + 1
            newdt = dt + datetime.timedelta(days=days)
            assert newdt.weekday() == incval
            return newdt
        if incunit == TimeUnit.HOUR:
            return dt + datetime.timedelta(hours=incval)
        if incunit == TimeUnit.MINUTE:
            return dt + datetime.timedelta(minute=incval)
        if incunit == TimeUnit.DAYOFMONTH:
            # incval in this case means next instance of a particular day of the month, with negative values
            # counting backwards from the end of the month (e.g. -1 means the last day of the month)
            newday = _dayofmonth(incval, dt.month, dt.year)
            newdt = dt.replace(day=newday)
            if newdt > origdt:
                return newdt

            # Advance a month
            newyear = dt.year
            newmonth = dt.month % 12 + 1
            if newmonth == 1:
                newyear += 1
            newday = _dayofmonth(incval, newmonth, dt.year)
            return dt.replace(day=newday, month=newmonth, year=newyear)
        else:
            raise s_exc.BadTime('Invalid incunit')

class _Appt:
    '''
    A single entry in the Agenda:  a storm query to run in the future
    '''

    def __init__(self, iden, recur, indx, query, username, recs, nexttime=None, timesrun=0):
        self.iden = iden
        self.recur = recur
        self.indx = indx  # incremented for each appt added ever.  Used for nexttime tiebreaking for stable ordering
        self.query = query  # query to run
        self.username = username  # user to run query as
        self.recs = recs  # A list of zero or more ApptRecs
        self._recidxnexttime = None # index of rec who is up next

        if nexttime is None:
            now = time.time()
            self.nexttime = now
            self.updateNexttime(now + 1.0)  # lie slightly about the time so it does advance
            if self.nexttime is None:
                raise s_exc.BadTime('Appointment is in the past')
        else:
            self.nexttime = nexttime
        self.isrunning = False  # whether it is currently running
        self.timesrun = 0  # how many times query has started

    def __eq__(self, other):
        ''' For heap logic '''
        return (self.nexttime, self.indx) == (other.nexttime, other.indx)

    def __lt__(self, other):
        ''' For heap logic '''
        return (self.nexttime, self.indx) < (other.nexttime, other.indx)

    def todict(self):
        return {
            'ver': 0,
            'recur': self.recur,
            'indx': self.indx,
            'query': self.query,
            'user': self.username,
            'recs': [d.entupl() for d in self.recs],
            'nexttime': self.nexttime,
            'timesrun': self.timesrun
        }

    @classmethod
    def fromdict(cls, val):
        if val['ver'] != 0:
            raise s_exc.BadStorageVersion
        # FIXME

    def updateNexttime(self, now):

        # If we're not recurring, delete the entry that just happened
        if self._recidxnexttime is not None and not self.recur:
            del self.recs[self._recidxnexttime]

        while self.recs and self.nexttime < now:

            lowtime = 999999999999.9

            # Find the lowest next time of all of our recs (backwards, so we can delete)
            for i in range(len(self.recs) - 1, -1, -1):
                rec = self.recs[i]
                nexttime = rec.nexttime(self.nexttime)
                if nexttime == 0.0:
                    # We blew by and missed a fixed-year appointment, either due to clock shenanigans, this query going
                    # really long, or the initial requirement being in the past
                    logger.warning('Missed an appointment: {rec}')
                    del self.recs[i]
                    continue
                if nexttime < lowtime:
                    lowtime = nexttime
                    lowidx = i

            if not self.recs:
                break

            self._recidxnexttime = lowidx
            self.nexttime = lowtime

        if not self.recs:
            self.nexttime = None
            return

class Agenda(s_base.Base):
    AGENDA_DB_NAME = 'agenda'

    async def __anit__(self, core):
        await s_base.Base.__anit__(self)
        self.core = core
        self.apptheap = []
        self.appts = {}  # iden: appt
        self._next_indx = 0
        self._wake_event = asyncio.Event()
        self.onfini(self._wake_event.set)
        self._load_all()
        self._schedtask = self.schedCoro(self._scheduleLoop())

    async def enable(self):
        # FIXME
        pass

    def _load_all(self):

        # FIXME:  need enable step, evaluate trigger

        # FIXME:  migrate to hive
        return
        db = self.core.slab.initdb(self.AGENDA_DB_NAME)
        for iden, val in self.core.slab.scanByRange(b'', db=db):
            try:
                apptdict = s_msgpack.un(val)
                appt = _Appt.unsimpl(apptdict)
                self._addappt(iden, appt)
                self._next_indx = max(self._next_indx, appt.indx + 1)
            except (s_exc.InconsistentStorage, TypeError, KeyError) as e:
                logger.warning('Invalid appointment %r found in storage: %r', iden, e)
                continue

    def _addappt(self, iden, appt):
        heapq.heappush(self.apptheap, appt)
        self.appts[iden] = appt
        if self.apptheap[0] is appt:
            self._wake_event.set()

    def _storeAppt(self, appt):
        # FIXME
        pass

    @staticmethod
    def _dictproduct(rdict):
        '''
        Yields a series of dicts that cover the combination of all multiple-value (e.g. lists or tuples) values, with
        non-multiple-value values remaining the same.
        '''
        multkeys = [k for k, v in rdict.items() if isinstance(v, Iterable)]
        if not multkeys:
            yield rdict
            return

        multvals = [rdict[k] for k in multkeys]

        for combo in itertools.product(*multvals):
            newdict = rdict.copy()
            for i, k in enumerate(multkeys):
                newdict[k] = combo[i]
            yield newdict

    def list(self):
        return [(iden, (appt.todict())) for (iden, appt) in self.appts.items()]

    def add(self, username, query: str, reqs, incunit=None, incvals=None):
        '''
        Persistently adds an appointment

        Args:
            query (str):
                storm query to run
            reqs (Union[None, Dict[TimeUnit, Union[int, Tuple[int]], List[...]):
                one or more dicts of the fixed aspects of the appointment.  dict value may be a single or multiple.
                May be an empty dict or None.
            incunit (Union[None, TimeUnit]):
                the unit that changes for repeating, or None for non-repeating.  It is an error for this value to match
                a key in reqdict.
            incvals (Union[None, int, Iterable[int]): count of units of incunit or explicit day of week or day of month.
                Not allowed for incunit == None, required for others (1 would be a typical
                value)

        Returns:
            iden of new appointment
        '''
        iden = os.urandom(16)
        recur = incunit is not None
        indx = self._next_indx
        self._next_indx += 1

        if reqs is None:
            reqs = {}

        if isinstance(reqs, Mapping):
            reqs = [reqs]

        recs = []
        for req in reqs:
            # Find all combinations of values in reqdict values and incvals values

            reqdicts = self._dictproduct(req)
            if not isinstance(incvals, Iterable):
                incvals = (incvals, )
            recs.extend(ApptRec(rd, incunit, v) for (rd, v) in itertools.product(reqdicts, incvals))

        appt = _Appt(iden, recur, indx, query, username, recs)
        self._addappt(iden, appt)

        # FIXME: persist

        return iden

    def delete(self, iden):
        appt = self.appts.get(iden)
        if appt is None:
            raise s_exc.NoSuchIden()

        try:
            heappos = self.apptheap.index(appt)
        except ValueError:
            pass
        else:
            # If we're already the last item, just delete it
            if heappos == len(self.apptheap) - 1:
                del self.apptheap[heappos]
            else:
                # put the last item at the current position and reheap
                self.apptheap[heappos] = self.apptheap.pop()
                heapq.heapify(self.apptheap)

        # FIXME: persist

    async def _scheduleLoop(self):
        while True:
            try:
                timeout = None if not self.apptheap else self.apptheap[0].nexttime - time.time()
                if timeout is None or timeout >= 0.0:
                    print(f'**Waiting for event or {timeout}s')
                    await asyncio.wait_for(self._wake_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print('Woke up due to timeout')
                pass
            if self.isfini:
                return
            self._wake_event.clear()

            now = time.time()
            print(f'now is {now} {datetime.datetime.fromtimestamp(now, tz.utc)}')
            while self.apptheap and self.apptheap[0].nexttime <= now:
                appt = heapq.heappop(self.apptheap)
                appt.updateNexttime(now)
                if appt.nexttime:
                    heapq.heappush(self.apptheap, appt)
                if appt.isrunning:
                    logger.warning(
                        'Appointment %s is still running from previous time when scheduled to run.  Skipping.',
                        appt.iden)

                appt.timesrun += 1
                await self.execute(appt)

    async def execute(self, appt):
        user = self.core.auth.users.get(appt.username)
        if user is None:
            logger.warning('Unknown username %s in stored appointment', appt.username)
            return
        await self.schedCoro(self._runJob(user, appt))

    async def _runJob(self, user, appt):
        count = 0
        appt.isrunning = True
        try:
            async for _ in self.core.eval(appt.query, user=user):
                count += 1
        except asyncio.CancelledError:
            result = 'cancelled'
            raise
        except Exception as e:
            result = f'raised exception {e}'
        else:
            result = f'finished successfully with {count} nodes'
        finally:
            appt.isrunning = False
            appt.lastresult = result
            self._storeAppt(appt)
