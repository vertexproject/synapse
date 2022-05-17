import asyncio
import hashlib
import datetime
from unittest import mock
from datetime import timezone as tz

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive
import synapse.lib.nexus as s_nexus
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.lib.agenda as s_agenda
from synapse.lib.agenda import TimeUnit as s_tu

class AgendaTest(s_t_utils.SynTest):
    def test_apptreq(self):

        # Invalid combinations
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.DAYOFWEEK: 3, s_tu.DAYOFMONTH: 4})
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.HOUR: 1}, s_tu.MINUTE)
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {}, None)
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {}, s_tu.DAYOFMONTH)
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.HOUR: -99}, s_tu.MINUTE)
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {}, s_tu.YEAR, -1)
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {'day': 4}, s_tu.YEAR, -1)

        ###############################

        # incunit = None, i.e. one-shot

        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.DAY: 15})

        # No inc, year req: One shot in 2017.  It is 2018
        now = datetime.datetime(year=2018, month=12, day=3, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        ar = s_agenda.ApptRec({s_tu.YEAR: 2017})
        newts = ar.nexttime(now)
        self.eq(newts, 0.0)

        # one shot in 2019.
        ar = s_agenda.ApptRec({s_tu.YEAR: 2019})
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=12, day=3, hour=2, minute=2, tzinfo=tz.utc).timestamp())

        # It is leap day 2020, one shot next year
        now = datetime.datetime(year=2020, month=2, day=29, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        ar = s_agenda.ApptRec({s_tu.YEAR: 2021})
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2021, month=2, day=28, hour=2, minute=2, tzinfo=tz.utc).timestamp())

        # It is leap day 2020, one shot next year, Halloween
        now = datetime.datetime(year=2020, month=2, day=29, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        ar = s_agenda.ApptRec({s_tu.DAYOFMONTH: 31, s_tu.YEAR: 2021, s_tu.MONTH: 10})
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2021, month=10, day=31, hour=2, minute=2, tzinfo=tz.utc).timestamp())

        # No inc, month req: One shot in July
        ar = s_agenda.ApptRec({s_tu.MONTH: 7})
        now = datetime.datetime(year=2018, month=12, day=3, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=7, day=3, hour=2, minute=2, tzinfo=tz.utc).timestamp())

        # No inc, day of month req: one shot on the 3rd of the month at 1:01am
        ar = s_agenda.ApptRec({s_tu.DAYOFMONTH: 3, s_tu.HOUR: 1, s_tu.MINUTE: 1})
        now = datetime.datetime(year=2018, month=12, day=4, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=1, day=3, hour=1, minute=1, tzinfo=tz.utc).timestamp())

        # No inc, day of week req: One shot next Monday at 1:01 am
        ar = s_agenda.ApptRec({s_tu.DAYOFWEEK: 0, s_tu.HOUR: 1, s_tu.MINUTE: 1})
        now = datetime.datetime(year=2018, month=12, day=31, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=1, day=7, hour=1, minute=1, tzinfo=tz.utc).timestamp())

        # No inc, hour req:  One shot at 4pm.  It is 5pm, last day of the year.
        ar = s_agenda.ApptRec({s_tu.HOUR: 16})
        now = datetime.datetime(year=2018, month=12, day=31, hour=17, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=1, day=1, hour=16, minute=2, tzinfo=tz.utc).timestamp())

        ################

        # incunit = Year

        # Year inc, day of month req:  every year on the 15th of the month
        ar = s_agenda.ApptRec({s_tu.DAYOFMONTH: 15}, s_tu.YEAR, 1)

        # before the target matches the target
        now = datetime.datetime(year=2018, month=3, day=1, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2018, month=3, day=15, tzinfo=tz.utc).timestamp())

        # at the appointment advances
        now = datetime.datetime(year=2018, month=3, day=15, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=3, day=15, tzinfo=tz.utc).timestamp())

        # past the appointment advances
        now = datetime.datetime(year=2018, month=3, day=15, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=3, day=15, tzinfo=tz.utc).timestamp())

        # Year inc, month req:  every other year in February
        ar = s_agenda.ApptRec({s_tu.MONTH: 2}, s_tu.YEAR, 2)
        now = datetime.datetime(year=2018, month=12, day=31, hour=17, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2020, month=2, day=28, hour=17, minute=2, tzinfo=tz.utc).timestamp())

        # Year inc, day of week req:  every other year on a Friday:  not supported
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.DAYOFWEEK: 4}, s_tu.YEAR, 2)

        # Year inc, hour req
        ar = s_agenda.ApptRec({s_tu.HOUR: 10}, s_tu.YEAR, 2)
        now = datetime.datetime(year=2018, month=12, day=31, hour=17, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2020, month=12, day=31, hour=10, minute=2, tzinfo=tz.utc).timestamp())

        #################

        # incunit = Month

        # Month inc, minute req: When the minute hand hits 30 every 14 months
        ar = s_agenda.ApptRec({s_tu.MINUTE: 30}, s_tu.MONTH, 14)
        now = datetime.datetime(year=2017, month=12, day=30, hour=0, minute=30, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=2, day=28, hour=0, minute=30, tzinfo=tz.utc).timestamp())

        # Month inc, day of month req:  every other month on the 4th
        ar = s_agenda.ApptRec({s_tu.DAYOFMONTH: 4}, s_tu.MONTH, 2)
        now = datetime.datetime(year=2017, month=12, day=30, hour=0, minute=30, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(2018, 2, 4, 0, 30, tzinfo=tz.utc).timestamp())

        # Month inc, day of week fail
        self.raises(s_exc.BadTime, s_agenda.ApptRec, {s_tu.DAYOFWEEK: 4}, s_tu.MONTH, 2)

        ###############

        # incunit = Day

        # Day inc, minute req:  Every day some time when the minute hand hits 30
        ar = s_agenda.ApptRec({s_tu.MINUTE: 30}, s_tu.DAY, 1)
        now = datetime.datetime(year=2019, month=2, day=1, hour=0, minute=2, tzinfo=tz.utc).timestamp()
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2019, month=2, day=1, hour=0, minute=30, tzinfo=tz.utc).timestamp())

        ###############

        # incunit = DayOfWeek

        # Day of week inc, hour req: Every Wednesday at 7pm
        ar = s_agenda.ApptRec({s_tu.HOUR: 7}, s_tu.DAYOFWEEK, 2)
        now = datetime.datetime(year=2018, month=12, day=3, hour=2, minute=2, tzinfo=tz.utc).timestamp()  # Monday
        newts = ar.nexttime(now)
        self.eq(newts, datetime.datetime(year=2018, month=12, day=5, hour=7, minute=2, tzinfo=tz.utc).timestamp())

    async def test_agenda(self):
        MONO_DELT = 1543827303.0
        unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=0, tzinfo=tz.utc).timestamp()

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        loop = asyncio.get_running_loop()
        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime), self.getTestDir() as dirn:

            async with self.getTestCore() as core:

                visi = await core.auth.addUser('visi')
                await visi.setAdmin(True)

                agenda = core.agenda
                await agenda.start()  # make sure it doesn't blow up

                self.eq([], agenda.list())

                # Missing reqs
                cdef = {'creator': core.auth.rootuser.iden, 'iden': 'fakeiden', 'storm': 'foo'}
                await self.asyncraises(ValueError, agenda.add(cdef))

                # Missing creator
                cdef = {'iden': 'fakeiden', 'storm': 'foo',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await self.asyncraises(ValueError, agenda.add(cdef))

                # Missing storm
                cdef = {'creator': core.auth.rootuser.iden, 'iden': 'fakeiden',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await self.asyncraises(ValueError, agenda.add(cdef))
                await self.asyncraises(s_exc.NoSuchIden, agenda.get('newp'))

                # Missing incvals
                cdef = {'creator': core.auth.rootuser.iden, 'iden': 'DOIT', 'storm': '[test:str=doit]',
                        'reqs': {s_agenda.TimeUnit.NOW: True},
                        'incunit': s_agenda.TimeUnit.MONTH}
                await self.asyncraises(ValueError, agenda.add(cdef))

                # Cannot schedule a recurring job with 'now'
                cdef = {'creator': core.auth.rootuser.iden, 'iden': 'DOIT', 'storm': '[test:str=doit]',
                        'reqs': {s_agenda.TimeUnit.NOW: True},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                await self.asyncraises(ValueError, agenda.add(cdef))
                await self.asyncraises(s_exc.NoSuchIden, agenda.get('DOIT'))

                # Schedule a one-shot to run immediately
                doit = s_common.guid()
                cdef = {'creator': core.auth.rootuser.iden, 'iden': doit,
                        'storm': '$lib.queue.gen(visi).put(woot)',
                        'reqs': {s_agenda.TimeUnit.NOW: True}}
                await agenda.add(cdef)

                # Can't have two with the same iden
                await self.asyncraises(s_exc.DupIden, agenda.add(cdef))

                self.eq((0, 'woot'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                appts = agenda.list()
                self.len(1, appts)
                self.eq(appts[0][1].startcount, 1)
                self.eq(appts[0][1].nexttime, None)
                await agenda.delete(doit)

                # Schedule a one-shot 1 minute from now
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(woot)',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await agenda.add(cdef)
                unixtime += 61
                self.eq((1, 'woot'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                appts = agenda.list()
                self.len(1, appts)
                self.eq(appts[0][1].startcount, 1)
                self.eq(appts[0][1].nexttime, None)

                # Schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(bar)',
                        'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                        'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                        'incvals': (2, 4)}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                # every 6th of the month at 7am and 8am (the 6th is a Thursday)
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(baz)',
                        'reqs': {s_tu.HOUR: (7, 8), s_tu.MINUTE: 0, s_tu.DAYOFMONTH: 6},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                guid2 = adef.get('iden')

                xmas = {s_tu.DAYOFMONTH: 25, s_tu.MONTH: 12, s_tu.YEAR: 2018}
                lasthanu = {s_tu.DAYOFMONTH: 10, s_tu.MONTH: 12, s_tu.YEAR: 2018}

                # And one-shots for Christmas and last day of Hanukkah of 2018
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(happyholidays)',
                        'reqs': (xmas, lasthanu)}
                await agenda.add(cdef)

                unixtime += 1
                await asyncio.sleep(0)
                self.none(await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop())'), timeout=5))

                # Advance to the first event on Wednesday the 5th
                unixtime = datetime.datetime(year=2018, month=12, day=5, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((2, 'bar'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Then two on the 6th
                unixtime = datetime.datetime(year=2018, month=12, day=6, hour=7, minute=15, tzinfo=tz.utc).timestamp()
                self.eq((3, 'baz'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                unixtime = datetime.datetime(year=2018, month=12, day=6, hour=8, minute=15, tzinfo=tz.utc).timestamp()
                self.eq((4, 'baz'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Then back to the 10:15 on Friday
                unixtime = datetime.datetime(year=2018, month=12, day=7, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((5, 'bar'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Then Dec 10
                unixtime = datetime.datetime(year=2018, month=12, day=10, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((6, 'happyholidays'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Then the Wednesday again
                unixtime = datetime.datetime(year=2018, month=12, day=12, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((7, 'bar'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Cancel the Wednesday/Friday appt
                await agenda.delete(guid)
                await self.asyncraises(s_exc.NoSuchIden, agenda.delete(b'1234'))

                # Then Dec 25
                unixtime = datetime.datetime(year=2018, month=12, day=25, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((8, 'happyholidays'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Then Jan 6
                unixtime = datetime.datetime(year=2019, month=1, day=6, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((9, 'baz'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                # Modify the last appointment
                await self.asyncraises(ValueError, agenda.mod(guid2, '', ))
                await agenda.mod(guid2, '#baz')
                self.eq(agenda.appts[guid2].query, '#baz')

                # Delete the other recurring appointment
                await agenda.delete(guid2)

                # Then nothing left scheduled
                self.len(0, agenda.apptheap)

                # Test that isrunning updated, cancelling works
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(),
                        'storm': '$lib.queue.gen(visi).put(sleep) [ inet:ipv4=1 ] | sleep 120',
                        'reqs': {}, 'incunit': s_agenda.TimeUnit.MINUTE, 'incvals': 1}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                unixtime += 60
                self.eq((10, 'sleep'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, True)
                await appt.task.kill()

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, False)
                self.eq(appt.lastresult, 'cancelled')
                await agenda.delete(guid)

                # Test bad queries record exception
                cdef = {'creator': core.auth.rootuser.iden, 'iden': s_common.guid(),
                        'storm': '$lib.queue.gen(visi).put(boom) $lib.raise(OmgWtfBbq, boom)',
                        'reqs': {}, 'incunit': s_agenda.TimeUnit.MINUTE,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                # bypass the API because it would actually syntax check
                unixtime += 60
                self.eq((11, 'boom'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, False)
                self.eq(appt.lastresult, "raised exception StormRaise: errname='OmgWtfBbq' mesg='boom'")

                # Test setting the global enable/disable flag
                # reset
                await agenda.delete(guid)
                self.len(0, agenda.apptheap)

                agenda._schedtask.cancel()
                agenda._schedtask = agenda.schedCoro(agenda._scheduleLoop())

                # schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'creator': visi.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(bar)',
                        'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                        'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                        'incvals': (2, 4)}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                self.len(1, agenda.apptheap)

                # disable crons and advance time
                agenda.enabled = False

                unixtime = datetime.datetime(year=2019, month=2, day=6, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                nexttime = datetime.datetime(year=2019, month=2, day=8, hour=10, minute=15, tzinfo=tz.utc).timestamp()

                await asyncio.sleep(0)

                appt = await agenda.get(guid)
                self.eq(nexttime, appt.nexttime)
                self.true(appt.enabled)
                self.eq(0, appt.startcount)

                # enable crons and advance time
                agenda.enabled = True

                unixtime = datetime.datetime(year=2019, month=2, day=13, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                self.eq((12, 'bar'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))

                self.eq(1, appt.startcount)

                cdef = {'creator': visi.iden, 'iden': s_common.guid(), 'storm': '[test:str=foo2]',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}

                await agenda.add(cdef)

                # Lock user and advance time
                await visi.setLocked(True)

                with self.getLoggerStream('synapse.lib.agenda', 'locked') as stream:
                    unixtime = datetime.datetime(year=2019, month=2, day=16, hour=10, minute=16, tzinfo=tz.utc).timestamp()

                    # pump the ioloop via sleep(0) until the log message appears
                    while not stream.wait(0.1):
                        await asyncio.sleep(0)

                    self.eq(2, appt.startcount)

    async def test_agenda_persistence(self):
        ''' Test we can make/change/delete appointments and they are persisted to storage '''
        with self.getTestDir() as fdir:

            core = mock.Mock()

            def raiseOnBadStorm(q):
                ''' Just enough storm parsing for this test '''
                # TODO: Async this and use AsyncMock when Python 3.8+ only
                f = asyncio.Future()
                if (q[0] == '[') != (q[-1] == ']'):
                    f.set_exception(s_exc.BadSyntax(mesg='mismatched braces'))
                else:
                    f.set_result('all good')
                return f

            core.getStormQuery = raiseOnBadStorm

            async with await s_lmdbslab.Slab.anit(fdir, map_size=100000) as slab:
                db = slab.initdb('hive')
                hive = await s_hive.SlabHive.anit(slab, db=db)
                core.hive = hive

                async with await s_agenda.Agenda.anit(core) as agenda:
                    await agenda.start()
                    # Schedule a query to run every Wednesday and Friday at 10:15am
                    cdef = {'creator': 'visi', 'iden': 'IDEN1', 'storm': '[test:str=bar]',
                            'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                            'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                            'incvals': (2, 4)}
                    adef = await agenda.add(cdef)
                    guid1 = adef.get('iden')

                    # every 6th of the month at 7am and 8am (the 6th is a Thursday)
                    cdef = {'creator': 'visi', 'iden': 'IDEN2', 'storm': '[test:str=baz]',
                            'reqs': {s_tu.HOUR: (7, 8), s_tu.MINUTE: 0, s_tu.DAYOFMONTH: 6},
                            'incunit': s_agenda.TimeUnit.MONTH,
                            'incvals': 1}
                    adef = await agenda.add(cdef)

                    guid2 = adef.get('iden')
                    appt = agenda.appts[guid2]
                    appt.lasterrs.append('error happened')
                    await agenda._storeAppt(appt)

                    # Add an appt with an invalid query
                    cdef = {'creator': 'visi', 'iden': 'BAD1', 'storm': '[test:str=',
                            'reqs': {s_tu.HOUR: (7, 8)},
                            'incunit': s_agenda.TimeUnit.MONTH,
                            'incvals': 1}
                    adef = await agenda.add(cdef)
                    badguid1 = adef.get('iden')

                    # Add an appt with a bad version in storage
                    cdef = {'creator': 'visi', 'iden': 'BAD2', 'storm': '[test:str=foo]',
                            'reqs': {s_tu.HOUR: (7, 8)},
                            'incunit': s_agenda.TimeUnit.MONTH,
                            'incvals': 1}
                    adef = await agenda.add(cdef)
                    badguid2 = adef.get('iden')

                    adef['ver'] = 1337
                    full = agenda._hivenode.full + (badguid2,)
                    await agenda.core.hive.set(full, adef)

                    xmas = {s_tu.DAYOFMONTH: 25, s_tu.MONTH: 12, s_tu.YEAR: 2099}
                    lasthanu = {s_tu.DAYOFMONTH: 10, s_tu.MONTH: 12, s_tu.YEAR: 2099}

                    await agenda.delete(guid1)

                    # And one-shots for Christmas and last day of Hanukkah of 2018
                    cdef = {'creator': 'visi', 'iden': 'IDEN3', 'storm': '#happyholidays',
                            'reqs': (xmas, lasthanu)}

                    adef = await agenda.add(cdef)
                    guid3 = adef.get('iden')

                    await agenda.mod(guid3, '#bahhumbug')

                async with await s_agenda.Agenda.anit(core) as agenda:
                    await agenda.start()
                    agenda.enabled = True

                    appts = agenda.list()
                    self.len(3, appts)

                    last_appt = [appt for (iden, appt) in appts if iden == guid3][0]
                    self.eq(last_appt.query, '#bahhumbug')

                    bad_appt = [appt for (iden, appt) in appts if iden == badguid1][0]
                    self.false(bad_appt.enabled)

                    self.len(0, [appt for (iden, appt) in appts if iden == badguid2])

    async def test_cron_perms(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            newb = await core.auth.addUser('newb')
            async with core.getLocalProxy(user='visi') as proxy:

                cdef = {'storm': 'inet:ipv4', 'reqs': {'hour': 2}}
                with self.raises(s_exc.AuthDeny):
                    await proxy.addCronJob(cdef)

                await visi.addRule((True, ('cron', 'add')))
                cron0 = await proxy.addCronJob(cdef)
                cron0_iden = cron0.get('iden')

                cdef = {'storm': 'inet:ipv6', 'reqs': {'hour': 2}}
                cron1 = await proxy.addCronJob(cdef)
                cron1_iden = cron1.get('iden')

                await proxy.delCronJob(cron0_iden)

                cdef = {'storm': '[test:str=foo]', 'reqs': {'now': True},
                        'incunit': 'month',
                        'incvals': 1}
                await self.asyncraises(s_exc.BadConfValu, proxy.addCronJob(cdef))

            async with core.getLocalProxy(user='newb') as proxy:

                with self.raises(s_exc.AuthDeny):
                    await proxy.delCronJob(cron1_iden)

                self.eq(await proxy.listCronJobs(), ())
                await newb.addRule((True, ('cron', 'get')))
                self.len(1, await proxy.listCronJobs())

                with self.raises(s_exc.AuthDeny):
                    await proxy.disableCronJob(cron1_iden)

                await newb.addRule((True, ('cron', 'set')))
                self.none(await proxy.disableCronJob(cron1_iden))

                await newb.addRule((True, ('cron', 'del')))
                await proxy.delCronJob(cron1_iden)

    async def test_agenda_stop(self):

        async with self.getTestCore() as core:
            await core.callStorm('$lib.queue.add(foo)')
            await core.callStorm('cron.add --minute +1 { $lib.queue.get(foo).put((99)) $lib.time.sleep(10) }')
            appts = core.agenda.list()
            await core.agenda._execute(appts[0][1])
            self.eq((0, 99), await core.callStorm('return($lib.queue.get(foo).get())'))

            appts[0][1].creator = 'fakeuser'
            await core.agenda._execute(appts[0][1])
            self.eq(appts[0][1].lastresult, 'Failed due to unknown user')

            await core.agenda.stop()
            self.false(core.agenda.enabled)

    async def test_agenda_custom_view(self):

        async with self.getTestCoreAndProxy() as (core, prox):
            # no existing view
            await core.callStorm('$lib.queue.add(testq)')
            defview = core.getView()
            fakeiden = hashlib.md5(defview.iden.encode('utf-8')).hexdigest()
            opts = {'vars': {'fakeiden': fakeiden}}
            with self.raises(s_exc.NoSuchView):
                await prox.callStorm('cron.add --view $fakeiden --minute +2 { $lib.queue.get(testq).put((43)) }', opts=opts)

            fail = await core.auth.addUser('fail')

            # can't move a thing that doesn't exist
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('cron.move $fakeiden $fakeiden', opts=opts)

            with self.raises(s_exc.NoSuchIden):
                await core.moveCronJob(fail.iden, 'NoSuchCronJob', defview.iden)

            with self.raises(s_exc.NoSuchIden):
                await core.agenda.move('StillDoesNotExist', defview.iden)

            # make a new view
            ldef = await core.addLayer()
            newlayr = core.getLayer(ldef.get('iden'))
            newview = await core.callStorm(f'return($lib.view.add(({newlayr.iden},)).iden)')

            # no perms to write to that view
            asfail = {'user': fail.iden, 'vars': {'newview': newview}}
            with self.raises(s_exc.AuthDeny):
                await prox.callStorm('cron.add --view $newview --minute +2 { $lib.queue.get(testq).put(lolnope) }', opts=asfail)

            # and just to be sure
            msgs = await core.stormlist('cron.list')
            self.stormIsInPrint('No cron jobs found', msgs)

            # no --view means it goes in the default view for the user, which fail doesn't have rights to
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('cron.add --minute +1 { $lib.queue.get(testq).put((44)) }', opts=asfail)

            # let's give fail permissions to do some things, but not in our super special view (fail is missing
            # the view read perm for the special view)
            await fail.addRule((True, ('cron', 'add')))

            # But we should still fail on this:
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('cron.add --view $newview --minute +2 { $lib.queue.get(testq).put(lolnope)}', opts=asfail)

            # and again, just to be sure
            msgs = await core.stormlist('cron.list')
            self.stormIsInPrint('No cron jobs found', msgs)

            # Now let's give him perms to do things
            await fail.addRule((True, ('view', 'read')), gateiden=newview)
            await fail.addRule((True, ('queue', 'get')), gateiden='queue:testq')
            await fail.addRule((True, ('queue', 'put')), gateiden='queue:testq')
            await fail.addRule((True, ('node', 'add')))
            await fail.addRule((True, ('cron', 'get')))

            # but should work on the default view
            opts = {'user': fail.iden, 'view': defview.iden, 'vars': {'defview': defview.iden}}
            await prox.callStorm('cron.at --view $defview --minute +1 { $lib.queue.get(testq).put((44)) }', opts=opts)

            jobs = await core.callStorm('return($lib.cron.list())')
            self.len(1, jobs)
            self.eq(defview.iden, jobs[0]['view'])

            core.agenda._addTickOff(60)
            retn = await core.callStorm('return($lib.queue.get(testq).get())', opts=asfail)
            self.eq((0, 44), retn)

            await core.callStorm('cron.del $croniden', opts={'vars': {'croniden': jobs[0]['iden']}})
            await core.callStorm('$lib.queue.get(testq).cull(0)')

            opts = {'vars': {'newview': newview}}
            await prox.callStorm('cron.add --minute +1 --view $newview { [test:guid=$lib.guid()] | $lib.queue.get(testq).put($node) }', opts=opts)

            jobs = await core.callStorm('return($lib.cron.list())')
            self.len(1, jobs)
            self.eq(newview, jobs[0]['view'])

            core.agenda._addTickOff(60)
            retn = await core.callStorm('return($lib.queue.get(testq).get())')
            await core.callStorm('$lib.queue.get(testq).cull(1)')

            # That node had better have been made in the new view
            guidnode = await core.nodes('test:guid', opts={'view': newview})
            self.len(1, guidnode)
            self.eq(('test:guid', retn[1]), guidnode[0].ndef)

            # and definitely not in the base view
            nonode = await core.nodes('test:guid', opts={'view': defview.iden})
            self.len(0, nonode)

            # no permission yet
            opts = {'user': fail.iden, 'vars': {'croniden': jobs[0]['iden'], 'viewiden': defview.iden}}
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('cron.move $croniden $viewiden', opts=opts)

            await fail.addRule((True, ('cron', 'set')))
            # try and fail to move to a view that doesn't exist
            opts = {'user': fail.iden, 'vars': {'croniden': jobs[0]['iden'], 'viewiden': fakeiden}}
            with self.raises(s_exc.NoSuchView):
                await core.callStorm('cron.move $croniden $viewiden', opts=opts)

            croniden = jobs[0]['iden']
            # now to test that we can move from the new layer to the base layer
            opts = {'user': fail.iden, 'vars': {'croniden': croniden, 'viewiden': defview.iden}}
            await core.callStorm('cron.move $croniden $viewiden', opts=opts)

            jobs = await core.callStorm('return($lib.cron.list())')
            self.len(1, jobs)
            self.eq(defview.iden, jobs[0]['view'])

            # moving to the same view shouldn't do much
            await core.moveCronJob(fail.iden, croniden, defview.iden)

            samejobs = await core.callStorm('return($lib.cron.list())')
            self.len(1, jobs)
            self.eq(jobs, samejobs)

            core.agenda._addTickOff(60)
            retn = await core.callStorm('return($lib.queue.get(testq).get())', opts=asfail)
            await core.callStorm('$lib.queue.get(testq).cull(2)')

            node = await core.nodes('test:guid', opts={'view': defview.iden})
            self.len(1, node)
            self.eq(('test:guid', retn[1]), node[0].ndef)
            self.ne(guidnode[0].ndef, node[0].ndef)

            # reach in, monkey with the view a bit
            appt = core.agenda.appts.get(croniden)
            appt.view = "ThisViewStillDoesntExist"
            await core.agenda._execute(appt)
            self.eq(appt.lastresult, 'Failed due to unknown view')

            await core.callStorm('cron.del $croniden', opts={'vars': {'croniden': croniden}})

            opts = {'vars': {'newview': newview}}
            await prox.callStorm('cron.at --now --view $newview { [test:str=gotcha] | $lib.queue.get(testq).put($node) }', opts=opts)
            retn = await core.callStorm('return($lib.queue.get(testq).get())', opts=asfail)
            self.eq((3, 'gotcha'), retn)
            await core.callStorm('$lib.queue.get(testq).cull(3)')
            atjob = await core.callStorm('return($lib.cron.list())')
            self.len(1, atjob)
            self.eq(atjob[0]['view'], newview)

            nodes = await core.nodes('test:str', opts={'view': defview.iden})
            self.len(0, nodes)
            nodes = await core.nodes('test:str', opts={'view': newview})
            self.len(1, nodes)

            croniden = atjob[0]['iden']
            await core.callStorm('cron.del $croniden', opts={'vars': {'croniden': croniden}})

            await prox.callStorm('cron.at --now { [test:int=97] | $lib.queue.get(testq).put($node) }')
            retn = await core.callStorm('return($lib.queue.get(testq).get())', opts=asfail)
            await core.callStorm('$lib.queue.get(testq).cull(4)')
            self.eq((4, 97), retn)

            nodes = await core.nodes('test:int=97', opts={'view': defview.iden})
            self.len(1, nodes)
            nodes = await core.nodes('test:int=97', opts={'view': newview})
            self.len(0, nodes)
