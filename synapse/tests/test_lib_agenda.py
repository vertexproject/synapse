import time
import asyncio
import hashlib
import datetime
from unittest import mock
from datetime import timezone as tz

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_t_utils

import synapse.tools.backup as s_tools_backup

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

    async def test_agenda_base(self):
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

                # Require valid storm
                cdef = {'creator': core.auth.rootuser.iden, 'iden': 'DOIT', 'storm': ' | | | ',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await self.asyncraises(s_exc.BadSyntax, agenda.add(cdef))
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
                self.eq(core.view.iden, appt.task.info.get('view'))

                self.true(await core._killCronTask(guid))

                events = [
                    {'event': 'cron:stop', 'info': {'iden': appt.iden}},
                ]

                task = core.schedCoro(s_t_utils.waitForBehold(core, events))
                await asyncio.wait_for(task, timeout=5)

                self.false(await core._killCronTask(guid))

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

                strt = await core.nexsroot.index()
                # bypass the API because it would actually syntax check
                unixtime += 60
                self.eq((11, 'boom'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))
                await core.nexsroot.waitOffs(strt + 5)

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, False)
                self.isin("raised exception StormRaise: errname='OmgWtfBbq'", appt.lastresult)
                self.isin("highlight={'hash': '6736b8252d9413221a9b693b2b19cf53'", appt.lastresult)
                self.isin("mesg='boom'", appt.lastresult)

                # Test setting the global enable/disable flag
                await agenda.delete(guid)
                self.len(0, agenda.apptheap)

                # schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'creator': visi.iden, 'iden': s_common.guid(), 'storm': '$lib.queue.gen(visi).put(bar)',
                        'pool': True,
                        'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                        'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                        'incvals': (2, 4)}
                adef = await agenda.add(cdef)

                self.true(adef['pool'])
                guid = adef.get('iden')

                self.len(1, agenda.apptheap)

                unixtime = datetime.datetime(year=2019, month=2, day=6, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                nexttime = datetime.datetime(year=2019, month=2, day=8, hour=10, minute=15, tzinfo=tz.utc).timestamp()

                await asyncio.sleep(0)

                appt = await agenda.get(guid)
                self.eq(nexttime, appt.nexttime)
                self.true(appt.enabled)
                self.eq(0, appt.startcount)

                # Ensure structured logging captures the cron iden value
                core.stormlog = True
                with self.getStructuredAsyncLoggerStream('synapse.storm') as stream:
                    unixtime = datetime.datetime(year=2019, month=2, day=13, hour=10, minute=16,
                                                 tzinfo=tz.utc).timestamp()
                    self.eq((12, 'bar'), await asyncio.wait_for(core.callStorm('return($lib.queue.gen(visi).pop(wait=$lib.true))'), timeout=5))
                core.stormlog = False

                msgs = stream.jsonlines()
                msgs = [m for m in msgs if m['text'] == '$lib.queue.gen(visi).put(bar)']
                self.gt(len(msgs), 0)
                for m in msgs:
                    self.eq(m.get('cron'), appt.iden)

                self.eq(1, appt.startcount)

                cdef = {'creator': visi.iden, 'iden': s_common.guid(), 'storm': '[test:str=foo2]',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}

                await agenda.add(cdef)

                # Lock user and advance time
                strt = await core.nexsroot.index()

                await visi.setLocked(True)

                with self.getLoggerStream('synapse.lib.agenda', 'locked') as stream:
                    unixtime = datetime.datetime(year=2019, month=2, day=16, hour=10, minute=16, tzinfo=tz.utc).timestamp()

                    # pump the ioloop via sleep(0) until the log message appears
                    while not stream.wait(0.1):
                        await asyncio.sleep(0)

                    await core.nexsroot.waitOffs(strt + 4)

                    self.eq(2, appt.startcount)

                # Can't use an existing authgate iden
                viewiden = core.getView().iden
                cdef = {'creator': core.auth.rootuser.iden,
                        'storm': '[test:str=bar]',
                        'reqs': {'hour': 10},
                        'incunit': 'dayofweek',
                        'incvals': (2, 4),
                        'iden': viewiden}
                await self.asyncraises(s_exc.DupIden, core.addCronJob(cdef))
                await core.delCronJob(viewiden)

                self.nn(await core.getAuthGate(viewiden))

    async def test_agenda_persistence(self):
        ''' Test we can make/change/delete appointments and they are persisted to storage '''

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                cdef = {'creator': core.auth.rootuser.iden,
                        'storm': '[test:str=bar]',
                        'reqs': {'hour': 10, 'minute': 15},
                        'incunit': 'dayofweek',
                        'incvals': (2, 4)}
                adef = await core.addCronJob(cdef)
                guid1 = adef.get('iden')

                # every 6th of the month at 7am and 8am (the 6th is a Thursday)
                cdef = {'creator': core.auth.rootuser.iden,
                        'storm': '[test:str=baz]',
                        'reqs': {'hour': (7, 8), 'minute': 0, 'dayofmonth': 6},
                        'incunit': 'month',
                        'incvals': 1}
                adef = await core.addCronJob(cdef)

                guid2 = adef.get('iden')
                appt = core.agenda.appts[guid2]
                appt.lasterrs.append('error happened')
                await appt.save()

                # Add an appt with an invalid query
                cdef = {'creator': core.auth.rootuser.iden,
                        'storm': '[test:str=',
                        'reqs': {'hour': (7, 8)},
                        'incunit': 'month',
                        'incvals': 1}

                with self.raises(s_exc.BadSyntax):
                    await core.addCronJob(cdef)

                xmas = {'dayofmonth': 25, 'month': 12, 'year': 2099}
                lasthanu = {'dayofmonth': 10, 'month': 12, 'year': 2099}

                await core.delCronJob(guid1)

                # And one-shots for Christmas and last day of Hanukkah of 2018
                cdef = {'creator': core.auth.rootuser.iden,
                        'storm': '#happyholidays',
                        'reqs': (xmas, lasthanu)}

                adef = await core.addCronJob(cdef)
                guid3 = adef.get('iden')

                await core.updateCronJob(guid3, '#bahhumbug')

                # Add a job with invalid storage version
                cdef = (await core.listCronJobs())[0]
                guid = s_common.guid()
                cdef['ver'] = 0
                cdef['iden'] = guid
                core.agenda.apptdefs.set(guid, cdef)

            async with self.getTestCore(dirn=dirn) as core:

                appts = await core.listCronJobs()

                self.len(2, appts)

                last_appt = [appt for appt in appts if appt.get('iden') == guid3][0]
                self.eq(last_appt.get('query'), '#bahhumbug')

    async def test_agenda_custom_view(self):

        async with self.getTestCoreAndProxy() as (core, prox):
            # no existing view
            await core.callStorm('$lib.queue.add(testq)')
            defview = core.getView()
            fakeiden = hashlib.md5(defview.iden.encode('utf-8'), usedforsecurity=False).hexdigest()
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
            self.nn(jobs[0].get('created'))

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

    async def test_agenda_edit(self):

        async with self.getTestCore() as core:

            lowuser = await core.addUser('lowuser')
            lowuser = lowuser.get('iden')

            msgs = await core.stormlist('cron.add --hourly 32 { $lib.print(woot) }')
            self.stormHasNoWarnErr(msgs)

            cdef = await core.callStorm('for $cron in $lib.cron.list() { return($cron) }')
            self.false(cdef['pool'])
            self.eq(cdef['creator'], core.auth.rootuser.iden)

            cdef = await core.callStorm('for $cron in $lib.cron.list() { $cron.set(pool, (true)) return($cron) }')
            self.true(cdef['pool'])

            opts = {'vars': {'lowuser': lowuser}}
            cdef = await core.callStorm('for $cron in $lib.cron.list() { return($cron.set(creator, $lowuser)) }',
                                        opts=opts)
            self.eq(cdef['creator'], lowuser)

            opts = {'user': lowuser, 'vars': {'iden': cdef.get('iden'), 'lowuser': lowuser}}
            q = '$cron = $lib.cron.get($iden) return ( $cron.set(creator, $lowuser) )'
            msgs = await core.stormlist(q, opts=opts)
            # XXX FIXME - This is an odd message since the new creator does not implicitly have
            # access to the cronjob that is running as them.
            self.stormIsInErr('Provided iden does not match any valid authorized cron job.', msgs)

            await core.addUserRule(lowuser, (True, ('cron', 'get')))
            opts = {'user': lowuser, 'vars': {'iden': cdef.get('iden'), 'lowuser': lowuser}}
            q = '$cron = $lib.cron.get($iden) return ( $cron.set(creator, $lowuser) )'
            msgs = await core.stormlist(q, opts=opts)
            self.stormIsInErr('must have permission cron.set.creator', msgs)

    async def test_agenda_fatal_run(self):

        # Create a scenario where an agenda appointment is "correct"
        # but encounters a fatal error when attempting to be created.
        # This error is then logged, and corrected.

        async with self.getTestCore() as core:

            udef = await core.addUser('user')
            user = udef.get('iden')

            fork = await core.callStorm('$fork = $lib.view.get().fork().iden return ( $fork )')

            q = '$lib.log.info(`I am a cron job run by {$lib.user.name()} in {$lib.view.get().iden}`)'
            msgs = await core.stormlist('cron.add --minute +1 $q', opts={'vars': {'q': q}, 'view': fork})
            self.stormHasNoWarnErr(msgs)

            cdef = await core.callStorm('for $cron in $lib.cron.list() { return($cron.set(creator, $user)) }',
                                        opts={'vars': {'user': user}})
            self.eq(cdef['creator'], user)

            # Force the cron to run.

            with self.getAsyncLoggerStream('synapse.lib.agenda', 'Agenda error running appointment ') as stream:
                core.agenda._addTickOff(55)
                self.true(await stream.wait(timeout=12))

            await core.addUserRule(user, (True, ('storm',)))
            await core.addUserRule(user, (True, ('view', 'read')), gateiden=fork)

            with self.getAsyncLoggerStream('synapse.storm.log', 'I am a cron job') as stream:
                core.agenda._addTickOff(60)
                self.true(await stream.wait(timeout=12))

    async def test_agenda_mirror_realtime(self):
        with self.getTestDir() as dirn:

            path00 = s_common.gendir(dirn, 'core00')
            path01 = s_common.gendir(dirn, 'core01')

            async with self.getTestCore(dirn=path00) as core00:
                await core00.nodes('[ inet:ipv4=1.2.3.4 ]')

            s_tools_backup.backup(path00, path01)

            async with self.getTestCore(dirn=path00) as core00:
                self.false(core00.conf.get('mirror'))

                await core00.callStorm('cron.add --minute +1 { $lib.time.sleep(5) }')

                url = core00.getLocalUrl()

                core01conf = {'mirror': url}

                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:
                    core00.agenda._addTickOff(55)

                    mesgs = []
                    async for mesg in core00.behold():
                        mesgs.append(mesg)
                        core00.agenda._addTickOff(30)
                        if len(mesgs) == 2:
                            break

                    await core01.sync()

                    cron00 = await core00.callStorm('return($lib.cron.list())')
                    cron01 = await core01.callStorm('return($lib.cron.list())')

                    self.eq(cron00, cron01)

                    start = mesgs[0]
                    stop = mesgs[1]

                    self.eq(start['event'], 'cron:start')
                    self.eq(stop['event'], 'cron:stop')

                    self.eq(start['info']['iden'], cron00[0]['iden'])
                    self.eq(stop['info']['iden'], cron00[0]['iden'])

                async with self.getTestCore(dirn=path01, conf=core01conf) as core01:
                    nodes = await core00.nodes('syn:cron')
                    self.len(1, nodes)

                    msgs = await core00.stormlist('syn:cron [ :name=foo :doc=bar ]')
                    self.stormHasNoWarnErr(msgs)
                    await core01.sync()

                    nodes = await core01.nodes('syn:cron')
                    self.len(1, nodes)
                    self.nn(nodes[0].props.get('.created'))
                    self.eq(nodes[0].props.get('name'), 'foo')
                    self.eq(nodes[0].props.get('doc'), 'bar')

                    appt = await core01.agenda.get(nodes[0].ndef[1])
                    self.eq(appt.name, 'foo')
                    self.eq(appt.doc, 'bar')

            with self.getLoggerStream('synapse.lib.agenda') as stream:
                async with self.getTestCore(dirn=path00) as core00:
                    appts = core00.agenda.list()
                    self.len(1, appts)
                    appt = appts[0][1]

                    edits = {
                        'invalid': 'newp',
                    }
                    await core00.addCronEdits(appt.iden, edits)

                stream.seek(0)
                data = stream.read()
                self.isin("_Appt.edits() Invalid attribute received: invalid = 'newp'", data)

    async def test_agenda_promotions(self):
        # Adjust this knob for the number of cron jobs you want to test. Below
        # are some average run times from my dev box
        # 100 -> ~15s
        # 250 -> ~18s
        # 500 -> ~22s
        # 5000 -> ~88s
        NUMJOBS = 100

        async with self.getTestAha() as aha:

            conf00 = {
                'aha:provision': await aha.addAhaSvcProv('00.cortex')
            }

            async with self.getTestCore(conf=conf00) as core00:
                self.false(core00.conf.get('mirror'))

                msgs = await core00.stormlist('[it:dev:str=foo]')
                self.stormHasNoWarnErr(msgs)

                # Forward wind agenda to two minutes past the hour so we don't hit any weird timing windows
                tick = core00.agenda._getNowTick()
                now = time.gmtime(int(tick))
                diff = (60 - now.tm_min) * 60
                core00.agenda._addTickOff(diff + 120)

                # Add NUMJOBS cron jobs that starts every hour
                q = '''
                for $ii in $lib.range($numjobs) {
                    cron.add --name `CRON{$ii}` --hour +1 { $lib.time.sleep(90) }
                }
                '''
                opts = {'vars': {'numjobs': NUMJOBS}}
                await core00.callStorm(q, opts=opts)

                prov01 = {'mirror': '00.cortex'}
                conf01 = {
                    'aha:provision': await aha.addAhaSvcProv('01.cortex', provinfo=prov01),
                }

                async with self.getTestCore(conf=conf01) as core01:
                    # Advance the ticks so the cronjob starts sooner
                    core00.agenda._addTickOff(3600)

                    # Sync agenda ticks
                    diff = core00.agenda._getNowTick() - core01.agenda._getNowTick()
                    core01.agenda._addTickOff(diff)

                    mesgs = []
                    async for mesg in core00.behold():
                        mesgs.append(mesg)
                        if len(mesgs) >= NUMJOBS:
                            break

                    for mesg in mesgs:
                        self.eq(mesg['event'], 'cron:start')

                    # Inspect crons and tasks
                    crons00 = await core00.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons00)
                    # isrunning is synced via nexus so it should be true for both cortexes
                    for cron in crons00:
                        self.true(cron.get('isrunning'))

                    cronidens = [k['iden'] for k in crons00]

                    await core01.sync()

                    crons01 = await core01.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons01)
                    # isrunning is synced via nexus so it should be true for both cortexes
                    for cron in crons01:
                        self.true(cron.get('isrunning'))

                    tasks00 = await core00.callStorm('return($lib.ps.list())')
                    # 101 tasks: one for the main task and NUMJOBS for the cronjob instances
                    self.len(NUMJOBS + 1, tasks00)
                    self.eq(tasks00[0]['info']['query'], '[it:dev:str=foo]')
                    for idx, task in enumerate(tasks00):
                        if idx == 0:
                            continue

                        self.isin(task['info']['iden'], cronidens)
                        self.eq(task['info']['query'], '$lib.time.sleep(90)')

                    # No tasks running on the follower
                    tasks01 = await core01.callStorm('return($lib.ps.list())')
                    self.len(0, tasks01)

                    with self.getLoggerStream('synapse.lib.agenda', mesg='name=CRON99') as stream:
                        # Promote and inspect cortex status
                        await core01.promote(graceful=True)
                        self.false(core00.isactive)
                        self.true(core01.isactive)

                    stream.seek(0)
                    data = stream.read()
                    for ii in range(NUMJOBS):
                        self.isin(f' name=CRON{ii} with result "cancelled" took ', data)

                    # Sync the (now) follower so the isrunning status gets updated to false on both cortexes
                    await core00.sync()

                    crons00 = await core00.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons00)
                    for cron in crons00:
                        self.false(cron.get('isrunning'))

                    crons01 = await core01.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons01)
                    for cron in crons01:
                        self.false(cron.get('isrunning'))

                    # Bump the ticks on core01 so the cron jobs start
                    core01.agenda._addTickOff(3600)

                    mesgs = []
                    async for mesg in core01.behold():
                        mesgs.append(mesg)
                        if len(mesgs) >= NUMJOBS:
                            break

                    for mesg in mesgs:
                        self.eq(mesg['event'], 'cron:start')

                    # Sync the follower to get the latest isrunning status
                    await core00.sync()

                    crons00 = await core00.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons00)
                    # Cronjobs are running so true on both cortexes
                    for cron in crons00:
                        self.true(cron.get('isrunning'))

                    crons01 = await core01.callStorm('return($lib.cron.list())')
                    self.len(NUMJOBS, crons01)
                    # Cronjobs are running so true on both cortexes
                    for cron in crons01:
                        self.true(cron.get('isrunning'))

                    tasks00 = await core00.callStorm('return($lib.ps.list())')
                    # This task is the main task from before promotion
                    self.len(1, tasks00)
                    self.eq(tasks00[0]['info']['query'], '[it:dev:str=foo]')

                    tasks01 = await core01.callStorm('return($lib.ps.list())')
                    # The cronjob instances are the only tasks
                    self.len(NUMJOBS, tasks01)
                    for task in tasks01:
                        self.isin(task['info']['iden'], cronidens)
                        self.eq(task['info']['query'], '$lib.time.sleep(90)')

    async def test_cron_kill(self):
        async with self.getTestCore() as core:

            data = []
            evt = asyncio.Event()

            async def task():
                async for mesg in core.behold():
                    data.append(mesg)
                    if mesg.get('event') == 'cron:stop':
                        evt.set()

            core.schedCoro(task())

            q = '$q=$lib.queue.gen(test) for $i in $lib.range(60) { $lib.time.sleep(0.1) $q.put($i) }'
            guid = s_common.guid()
            cdef = {
                'creator': core.auth.rootuser.iden, 'iden': guid,
                'storm': q,
                'reqs': {'now': True}
            }
            await core.addCronJob(cdef)

            q = '$q=$lib.queue.gen(test) for $valu in $q.get((0), wait=(true)) { return ($valu) }'
            valu = await core.callStorm(q)
            self.eq(valu, 0)

            opts = {'vars': {'iden': guid}}
            get_cron = 'return($lib.cron.get($iden).pack())'
            cdef = await core.callStorm(get_cron, opts=opts)
            self.true(cdef.get('isrunning'))

            self.true(await core.callStorm('return($lib.cron.get($iden).kill())', opts=opts))

            self.true(await asyncio.wait_for(evt.wait(), timeout=12))

            cdef = await core.callStorm(get_cron, opts=opts)
            self.false(cdef.get('isrunning'))

    async def test_cron_kill_pool(self):

        async with self.getTestAha() as aha:

            import synapse.cortex as s_cortex
            import synapse.lib.base as s_base

            async with await s_base.Base.anit() as base:

                with self.getTestDir() as dirn:

                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.core', s_cortex.Cortex, dirn=dirn00))
                    provinfo = {'mirror': '00.core'}
                    core01 = await base.enter_context(self.addSvcToAha(aha, '01.core', s_cortex.Cortex, dirn=dirn01, provinfo=provinfo))

                    self.len(1, await core00.nodes('[inet:asn=0]'))
                    await core01.sync()
                    self.len(1, await core01.nodes('inet:asn=0'))

                    msgs = await core00.stormlist('aha.pool.add pool00...')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('Created AHA service pool: pool00.synapse', msgs)

                    msgs = await core00.stormlist('aha.pool.svc.add pool00... 01.core...')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('AHA service (01.core...) added to service pool (pool00.synapse)', msgs)

                    msgs = await core00.stormlist('cortex.storm.pool.set --connection-timeout 1 --sync-timeout 1 aha://pool00...')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('Storm pool configuration set.', msgs)

                    await core00.stormpool.waitready(timeout=12)

                    data = []
                    evt = asyncio.Event()

                    async def task():
                        async for mesg in core00.behold():
                            data.append(mesg)
                            if mesg.get('event') == 'cron:stop':
                                evt.set()

                    core00.schedCoro(task())

                    q = '$q=$lib.queue.gen(test) for $i in $lib.range(60) { $lib.time.sleep(0.1) $q.put($i) }'
                    guid = s_common.guid()
                    cdef = {
                        'creator': core00.auth.rootuser.iden, 'iden': guid,
                        'storm': q,
                        'reqs': {'NOW': True},
                        'pool': True,
                    }
                    await core00.addCronJob(cdef)

                    q = '$q=$lib.queue.gen(test) for $valu in $q.get((0), wait=(true)) { return ($valu) }'
                    valu = await core00.callStorm(q, opts={'mirror': False})
                    self.eq(valu, 0)

                    opts = {'vars': {'iden': guid}, 'mirror': False}
                    get_cron = 'return($lib.cron.get($iden).pack())'
                    cdef = await core00.callStorm(get_cron, opts=opts)
                    self.true(cdef.get('isrunning'))

                    self.true(await core00.callStorm('return($lib.cron.get($iden).kill())', opts=opts))

                    self.true(await asyncio.wait_for(evt.wait(), timeout=12))

                    cdef00 = await core00.callStorm(get_cron, opts=opts)
                    self.false(cdef00.get('isrunning'))

                    cdef01 = await core01.callStorm(get_cron, opts=opts)
                    self.false(cdef01.get('isrunning'))
                    self.eq(cdef01.get('lastresult'), 'cancelled')
                    self.gt(cdef00['laststarttime'], 0)
                    self.eq(cdef00['laststarttime'], cdef01['laststarttime'])

    async def test_agenda_warnings(self):

        async with self.getTestCore() as core:
            with self.getAsyncLoggerStream('synapse.lib.agenda', 'issued warning: oh hai') as stream:
                q = '$lib.warn("oh hai")'
                msgs = await core.stormlist('cron.at --now $q', opts={'vars': {'q': q}})
                self.stormHasNoWarnErr(msgs)
                self.true(await stream.wait(timeout=6))

    async def test_agenda_graceful_promotion_with_running_cron(self):

        async with self.getTestAha() as aha:

            conf00 = {
                'aha:provision': await aha.addAhaSvcProv('00.cortex')
            }

            async with self.getTestCore(conf=conf00) as core00:
                self.false(core00.conf.get('mirror'))

                q = '''
                while((true)) {
                    $lib.log.error('I AM A ERROR LOG MESSAGE')
                    $lib.time.sleep(6)
                }
                '''
                msgs = await core00.stormlist('cron.at --now $q', opts={'vars': {'q': q}})
                self.stormHasNoWarnErr(msgs)

                crons00 = await core00.callStorm('return($lib.cron.list())')
                self.len(1, crons00)

                prov01 = {'mirror': '00.cortex'}
                conf01 = {
                    'aha:provision': await aha.addAhaSvcProv('01.cortex', provinfo=prov01),
                }

                async with self.getTestCore(conf=conf01) as core01:

                    with self.getAsyncLoggerStream('synapse.storm.log', 'I AM A ERROR LOG MESSAGE') as stream:
                        self.true(await stream.wait(timeout=6))

                    cron = await core00.callStorm('return($lib.cron.list())')
                    self.len(1, cron)
                    self.true(cron[0].get('isrunning'))

                    await core01.promote(graceful=True)

                    self.false(core00.isactive)
                    self.true(core01.isactive)

                    await core00.sync()

                    cron00 = await core00.callStorm('return($lib.cron.list())')
                    self.len(1, cron00)
                    self.false(cron00[0].get('isrunning'))
                    self.eq(cron00[0].get('lasterrs')[0], 'aborted')

                    cron01 = await core01.callStorm('return($lib.cron.list())')
                    self.len(1, cron01)
                    self.false(cron01[0].get('isrunning'))
                    self.eq(cron01[0].get('lasterrs')[0], 'aborted')

    async def test_agenda_force_promotion_with_running_cron(self):

        async with self.getTestAha() as aha:

            conf00 = {
                'aha:provision': await aha.addAhaSvcProv('00.cortex')
            }

            async with self.getTestCore(conf=conf00) as core00:
                self.false(core00.conf.get('mirror'))

                q = '''
                while((true)) {
                    $lib.log.error('I AM A ERROR LOG MESSAGE')
                    $lib.time.sleep(6)
                }
                '''
                msgs = await core00.stormlist('cron.at --now $q', opts={'vars': {'q': q}})
                self.stormHasNoWarnErr(msgs)

                crons00 = await core00.callStorm('return($lib.cron.list())')
                self.len(1, crons00)

                prov01 = {'mirror': '00.cortex'}
                conf01 = {
                    'aha:provision': await aha.addAhaSvcProv('01.cortex', provinfo=prov01),
                }

                async with self.getTestCore(conf=conf01) as core01:

                    cron = await core00.callStorm('return($lib.cron.list())')
                    self.len(1, cron)
                    self.true(cron[0].get('isrunning'))

                    await core01.promote(graceful=False)

                    self.true(core00.isactive)
                    self.true(core01.isactive)

                    cron01 = await core01.callStorm('return($lib.cron.list())')
                    self.len(1, cron01)
                    self.false(cron01[0].get('isrunning'))
                    self.eq(cron01[0].get('lasterrs')[0], 'aborted')

    async def test_agenda_clear_running_none_nexttime(self):

        async with self.getTestCore() as core:

            cdef = {
                'creator': core.auth.rootuser.iden,
                'iden': s_common.guid(),
                'storm': '$lib.log.info("test")',
                'reqs': {},
                'incunit': 'minute',
                'incvals': 1
            }
            await core.addCronJob(cdef)

            appt = core.agenda.appts[cdef['iden']]
            self.true(appt in core.agenda.apptheap)

            appt.isrunning = True
            appt.nexttime = None

            await core.agenda.clearRunningStatus()
            self.false(appt in core.agenda.apptheap)

            crons = await core.callStorm('return($lib.cron.list())')
            self.len(1, crons)

    async def test_agenda_lasterrs(self):

        async with self.getTestCore() as core:

            cdef = {
                'iden': 'test',
                'creator': core.auth.rootuser.iden,
                'storm': '[ test:str=foo ]',
                'reqs': {},
                'incunit': s_tu.MINUTE,
                'incvals': 1
            }

            await core.agenda.add(cdef)
            appt = await core.agenda.get('test')

            self.true(isinstance(appt.lasterrs, list))
            self.eq(appt.lasterrs, [])

            edits = {
                'lasterrs': ('error1', 'error2'),
            }
            await appt.edits(edits)

            self.true(isinstance(appt.lasterrs, list))
            self.eq(appt.lasterrs, ['error1', 'error2'])

            await core.agenda._load_all()
            appt = await core.agenda.get('test')
            self.true(isinstance(appt.lasterrs, list))
            self.eq(appt.lasterrs, ['error1', 'error2'])
