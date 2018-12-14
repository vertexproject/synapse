import os
import enum
import time
import heapq
import asyncio
import logging
import calendar
import datetime
import itertools
from datetime import timezone as tz
from collections.abc import Iterable, Mapping

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.base as s_base

logger = logging.getLogger(__name__)

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

    @classmethod
    def fromString(cls, s):
        return cls.__members__[s.upper()]

_NextUnitMap = {
    TimeUnit.YEAR: None,
    TimeUnit.MONTH: TimeUnit.YEAR,
    TimeUnit.HOUR: TimeUnit.DAY,
    TimeUnit.MINUTE: TimeUnit.HOUR,
    TimeUnit.DAYOFMONTH: TimeUnit.MONTH,
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

# The valid ranges for required and recurring
_UnitBounds = {
    TimeUnit.YEAR: ((2000, 2999), (1, 5)),
    TimeUnit.MONTH: ((1, 12), (1, 60)),
    TimeUnit.DAYOFMONTH: ((-31, 31), (-31, 31)),
    TimeUnit.DAYOFWEEK: ((0, 6), (0, 6)),
    TimeUnit.DAY: ((0, 0), (1, 365 * 5)),
    TimeUnit.HOUR: ((0, 23), (1, 1000)),
    TimeUnit.MINUTE: ((0, 59), (1, 60 * 60 * 24 * 30))
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
            raise s_exc.BadTime(mesg='reqdict must be nonempty or incunit must be non-None')

        if TimeUnit.DAY in reqdict:
            raise s_exc.BadTime(mesg='Must not specify day as requirement')

        if TimeUnit.DAYOFMONTH in reqdict and TimeUnit.DAYOFWEEK in reqdict:
            raise s_exc.BadTime(mesg='Both day of month and day of week must not both be requirements')

        if TimeUnit.DAYOFWEEK in reqdict and incunit is not None:
            raise s_exc.BadTime(mesg='Day of week requirement not supported with a recurrence')

        if incunit == TimeUnit.DAYOFMONTH:
            raise s_exc.BadTime(mesg='Day of month not a valid incunit')

        if incunit is not None:
            boundmin, boundmax = _UnitBounds[incunit][1]
            if not boundmin <= incval <= boundmax:
                raise s_exc.BadTime(mesg='Out of bounds incval')

        for reqkey, reqval in reqdict.items():
            if reqkey not in TimeUnit:
                raise s_exc.BadTime(mesg='Keys of reqdict parameter must be valid TimeUnit values')
            boundmin, boundmax = _UnitBounds[reqkey][0]
            if not boundmin <= reqval <= boundmax:
                raise s_exc.BadTime(mesg='Out of bounds reqdict value')

            if incunit is not None and reqkey <= incunit:
                # We could, actually support this, but most of these combinations are nonsensical (e.g. run every 5
                # minutes in 2018 only?)
                raise s_exc.BadTime(mesg='Must not have fixed unit equal to or greater than recurrence unit')

        self.reqdict = {}
        # Put keys in size order, with dayof... added last, as nexttime processes in that order
        for key in _NextUnitMap:
            if key in reqdict:
                self.reqdict[key] = reqdict[key]

    def __repr__(self):
        return repr(self.entupl())

    def entupl(self):
        reqdictf = {k.name.lower(): v for (k, v) in self.reqdict.items()}
        incunitf = None if self.incunit is None else self.incunit.name.lower()
        return (reqdictf, incunitf, self.incval)

    @classmethod
    def untupl(cls, val):
        reqdictf, incunitf, incval = val
        reqdict = {TimeUnit[k.upper()]: v for (k, v) in reqdictf.items()}
        incunit = None if incunitf is None else TimeUnit[incunitf.upper()]
        return cls(reqdict, incunit, incval)

    def nexttime(self, lastts):
        '''
        Returns next timestamp that meets requirements, incrementing by self.incunit, incval if not increasing, or
        0.0 if there are no future matches
        '''
        lastdt = datetime.datetime.fromtimestamp(lastts, tz.utc)
        newvals = {}  # all the new fields that will be changed in the

        # Truncate the seconds part
        newdt = lastdt.replace(second=0)

        for unit, newval in self.reqdict.items():
            dtkey = _TimeunitToDatetime[unit]
            if unit is TimeUnit.DAYOFWEEK:
                newdt = newdt.replace(**newvals)
                newvals = {}
                newval = newdt.day + (6 + newval - newdt.weekday()) % 7 + 1
                if newval > calendar.monthrange(newdt.year, newdt.month)[1]:
                    newval -= 7
            elif unit is TimeUnit.MONTH:
                # As we change the month, clamp the day of the month to a valid value
                newdt = newdt.replace(**newvals)
                newvals = {}
                dayval = _dayofmonth(newdt.day, newval, newdt.year)
                newvals['day'] = dayval
            elif unit is TimeUnit.DAYOFMONTH:
                newdt = newdt.replace(**newvals)
                newvals = {}
                newval = _dayofmonth(newval, newdt.month, newdt.year)

            newvals[dtkey] = newval

        newdt = newdt.replace(**newvals)

        # Then move forward if we have to
        if newdt <= lastdt or \
                self.incunit == TimeUnit.DAYOFWEEK and newdt.weekday() != self.incval:
            if self.incunit is None:
                largest_req = min(self.reqdict.keys())
                tmpunit = _NextUnitMap[largest_req]
                if tmpunit is None:  # required a year and we're already there
                    return 0.0
                # Unless we're going to the next day of week, increment by 1 unit of the next larger unit
                tmpincval = self.reqdict.get(TimeUnit.DAYOFWEEK, 1)
            else:
                tmpunit = self.incunit
                tmpincval = self.incval
            newdt = self._inc(tmpunit, tmpincval, self.reqdict, lastdt, newdt)
            assert newdt > lastdt
        print(newdt)
        return newdt.timestamp()

    def _inc(self, incunit, incval, reqdict, origdt, dt):
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
            dayofmonthreq = reqdict.get(TimeUnit.DAYOFMONTH)
            if dayofmonthreq is not None:
                newday = _dayofmonth(dayofmonthreq, newmonth, newyear)
            else:
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
            return dt + datetime.timedelta(minutes=incval)
        else:
            raise s_exc.BadTime(mesg='Invalid incunit')

class _Appt:
    '''
    A single entry in the Agenda:  a storm query to run in the future
    '''
    def __init__(self, iden, recur, indx, query, username, recs, nexttime=None):
        self.iden = iden
        self.recur = recur
        self.indx = indx  # incremented for each appt added ever.  Used for nexttime tiebreaking for stable ordering
        self.query = query  # query to run
        self.username = username  # user to run query as
        self.recs = recs  # A list of zero or more ApptRecs
        self._recidxnexttime = None # index of rec who is up next

        if self.recur and not self.recs:
            raise s_exc.BadTime(mesg='A recurrent appointment with no records')

        if nexttime is None and self.recs:
            now = time.time()
            self.nexttime = now
            self.updateNexttime(now + 1.0)  # lie slightly about the time so it does advance
            if self.nexttime is None:
                raise s_exc.BadTime(mesg='Appointment is in the past')
        else:
            self.nexttime = nexttime
        self.isrunning = False  # whether it is currently running
        self.startcount = 0  # how many times query has started
        self.laststarttime = None
        self.lastfinishtime = None
        self.lastresult = None
        self.enabled = True

    def __eq__(self, other):
        ''' For heap logic '''
        return (self.nexttime, self.indx) == (other.nexttime, other.indx)

    def __lt__(self, other):
        ''' For heap logic '''
        return (self.nexttime, self.indx) < (other.nexttime, other.indx)

    def todict(self):
        return {
            'ver': 0,
            'enabled': self.enabled,
            'recur': self.recur,
            'iden': self.iden,
            'indx': self.indx,
            'query': self.query,
            'username': self.username,
            'recs': [d.entupl() for d in self.recs],
            'nexttime': self.nexttime,
            'startcount': self.startcount,
            'isrunning': self.isrunning,
            'laststarttime': self.laststarttime,
            'lastfinishtime': self.lastfinishtime,
            'lastresult': self.lastresult
        }

    @classmethod
    def fromdict(cls, val):
        if val['ver'] != 0:
            raise s_exc.BadStorageVersion
        recs = [ApptRec.untupl(tupl) for tupl in val['recs']]
        appt = cls(val['iden'], val['recur'], val['indx'], val['query'], val['username'], recs, val['nexttime'])
        appt.startcount = val['startcount']
        appt.laststarttime = val['laststarttime']
        appt.lastfinishtime = val['lastfinishtime']
        appt.lastresult = val['lastresult']

        return appt

    def updateNexttime(self, now):

        # If we're not recurring, delete the entry that just happened
        if self._recidxnexttime is not None and not self.recur:
            del self.recs[self._recidxnexttime]

        while self.recs and self.nexttime <= now:

            lowtime = 999999999999.9

            # Find the lowest next time of all of our recs (backwards, so we can delete)
            for i in range(len(self.recs) - 1, -1, -1):
                rec = self.recs[i]
                nexttime = rec.nexttime(self.nexttime)
                if nexttime == 0.0:
                    # We blew by and missed a fixed-year appointment, either due to clock shenanigans, this query going
                    # really long, or the initial requirement being in the past
                    logger.warning(f'Missed an appointment: {rec}')
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
        self.appts = {}  # Dict[bytes: Appt]
        self._next_indx = 0

        self._wake_event = asyncio.Event()
        self.onfini(self._wake_event.set)

        self._hivedict = await self.core.hive.dict(('agenda', 'appts'))
        self.onfini(self._hivedict)

        self.enabled = False
        self._schedtask = None
        await self._load_all()

    async def enable(self):
        '''
        Enable cron jobs to start running.

        Go through all the appointment s, making sure the query is valid, and remove the ones that aren't.  (We can't
        evaluate queries until enabled because not all the modules are loaded yet.)
        '''
        if self.enabled:
            return

        to_delete = []
        for iden, appt in self.appts.items():
            try:
                self.core.getStormQuery(appt.query)
            except Exception as e:
                logger.warning('Invalid appointment %r found in storage: %r.  Removing.', iden, e)
                to_delete.append(iden)

        for iden in to_delete:
            await self.delete(iden)

        self._schedtask = self.schedCoro(self._scheduleLoop())
        self.enabled = True

    async def _load_all(self):

        to_delete = []
        for idenf, val in self._hivedict.items():
            try:
                iden = s_common.uhex(idenf)
                breakpoint()
                appt = _Appt.fromdict(val)
                if appt.iden != iden:
                    raise s_exc.InconsistentStorage(mesg='iden inconsistency')
                self._addappt(iden, appt)
                self._next_indx = max(self._next_indx, appt.indx + 1)
            except (s_exc.InconsistentStorage, s_exc.BadTime, TypeError, KeyError) as e:
                logger.warning('Invalid appointment %r found in storage: %r.  Removing', iden, e)
                to_delete.append(iden)
                continue

        for iden in to_delete:
            await self._hivedict.pop(s_common.ehex(iden))

    def _addappt(self, iden, appt):
        if appt.nexttime:
            heapq.heappush(self.apptheap, appt)
        self.appts[iden] = appt
        if self.apptheap and self.apptheap[0] is appt:
            self._wake_event.set()

    async def _storeAppt(self, appt):
        await self._hivedict.set(s_common.ehex(appt.iden), appt.todict())

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

    async def add(self, username, query: str, reqs, incunit=None, incvals=None):
        '''
        Persistently adds an appointment

        Args:
            query (str):
                storm query to run
            reqs (Union[None, Dict[TimeUnit, Union[int, Tuple[int]], List[...]):
                one or more dicts of the fixed aspects of the appointment.  dict value may be a single or multiple.
                May be an empty dict or None.
            incunit (Union[None, TimeUnit]):
                the unit that changes for recurring, or None for non-recurring.  It is an error for this value to match
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

        if incunit is not None and incvals is None:
            raise ValueError('incvals must be non-None if incunit is non-None')

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

        await self._storeAppt(appt)

        return iden

    async def mod(self, iden, query):
        appt = self.appts.get(iden)
        if appt is None:
            raise s_exc.NoSuchIden()

        if self.enabled:
            self.core.getStormQuery(query)

        appt.query = query

        await self._storeAppt(appt)

    async def delete(self, iden):
        appt = self.appts.get(iden)
        if appt is None:
            raise s_exc.NoSuchIden()

        try:
            heappos = self.apptheap.index(appt)
        except ValueError:
            pass  # this is OK, just a non-recurring appt that has no more records
        else:
            # If we're already the last item, just delete it
            if heappos == len(self.apptheap) - 1:
                del self.apptheap[heappos]
            else:
                # put the last item at the current position and reheap
                self.apptheap[heappos] = self.apptheap.pop()
                heapq.heapify(self.apptheap)

        del self.appts[iden]
        await self._hivedict.pop(s_common.ehex(iden))

    async def _scheduleLoop(self):
        while True:
            try:
                timeout = None if not self.apptheap else self.apptheap[0].nexttime - time.time()
                if timeout is None or timeout >= 0.0:
                    print(f'Waiting for {timeout}s')
                    await asyncio.wait_for(self._wake_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass
            if self.isfini:
                return
            self._wake_event.clear()

            now = time.time()
            # print(f'now is {now} {datetime.datetime.fromtimestamp(now, tz.utc)}')
            while self.apptheap and self.apptheap[0].nexttime <= now:
                appt = heapq.heappop(self.apptheap)
                appt.updateNexttime(now)
                if appt.nexttime:
                    heapq.heappush(self.apptheap, appt)
                if appt.isrunning:
                    logger.warning(
                        'Appointment %s is still running from previous time when scheduled to run.  Skipping.',
                        appt.iden)

                await self.execute(appt)

    async def execute(self, appt):
        if appt.username is None or self.core.auth is None:
            user = None
        else:
            user = self.core.auth.users.get(appt.username)
            if user is None:
                logger.warning('Unknown username %s in stored appointment', appt.username)
                return
        await self.schedCoro(self._runJob(user, appt))

    async def _runJob(self, user, appt):
        count = 0
        appt.isrunning = True
        appt.laststarttime = time.time()
        appt.startcount += 1
        await self._storeAppt(appt)
        logger.info(f'Agenda executing as user {user} query {appt.query}')
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
            appt.lastfinishtime = time.time()
            appt.isrunning = False
            appt.lastresult = result
            await self._storeAppt(appt)
