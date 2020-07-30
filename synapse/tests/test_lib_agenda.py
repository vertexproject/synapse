import asyncio
import datetime
from unittest import mock
from datetime import timezone as tz

import synapse.exc as s_exc
import synapse.tests.utils as s_t_utils

import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive
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
        sync = asyncio.Event()
        lastquery = None

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        async def myeval(query, opts=None):
            nonlocal lastquery
            lastquery = query
            sync.set()
            if 'sleep' in query:
                await asyncio.sleep(60)

            if query == 'badquery':
                raise Exception('test exception')
            return
            yield None

        loop = asyncio.get_running_loop()
        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime), self.getTestDir() as dirn:
            core = mock.Mock()
            core.eval = myeval
            core.slab = await s_lmdbslab.Slab.anit(dirn, map_size=s_t_utils.TEST_MAP_SIZE, readonly=False)
            db = core.slab.initdb('hive')
            core.hive = await s_hive.SlabHive.anit(core.slab, db=db)
            core.boss = await s_boss.Boss.anit()
            async with await s_agenda.Agenda.anit(core) as agenda:
                agenda.onfini(core.hive)
                agenda.onfini(core.slab)
                agenda.onfini(core.boss)

                await agenda.start()
                await agenda.start()  # make sure it doesn't blow up
                self.eq([], agenda.list())

                rootiden = 'aaaaa'
                cdef = {'useriden': rootiden, 'iden': 'fakeiden', 'storm': '',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await self.asyncraises(ValueError, agenda.add(cdef))
                await self.asyncraises(s_exc.NoSuchIden, agenda.get('newp'))

                # Schedule a one-shot 1 minute from now
                cdef = {'useriden': rootiden, 'iden': 'IDEN1', 'storm': '[test:str=foo]',
                        'reqs': {s_agenda.TimeUnit.MINUTE: 1}}
                await agenda.add(cdef)
                await asyncio.sleep(0)  # give the scheduler a shot to wait
                unixtime += 61
                await sync.wait()  # wait for the query to run
                sync.clear()
                self.eq(lastquery, '[test:str=foo]')
                core.reset_mock()
                lastquery = None

                appts = agenda.list()
                self.len(1, appts)
                self.eq(appts[0][1].startcount, 1)
                self.eq(appts[0][1].nexttime, None)

                # Schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'useriden': rootiden, 'iden': 'IDEN2', 'storm': '[test:str=bar]',
                        'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                        'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                        'incvals': (2, 4)}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                # every 6th of the month at 7am and 8am (the 6th is a Thursday)
                cdef = {'useriden': rootiden, 'iden': 'IDEN3', 'storm': '[test:str=baz]',
                        'reqs': {s_tu.HOUR: (7, 8), s_tu.MINUTE: 0, s_tu.DAYOFMONTH: 6},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                guid2 = adef.get('iden')

                xmas = {s_tu.DAYOFMONTH: 25, s_tu.MONTH: 12, s_tu.YEAR: 2018}
                lasthanu = {s_tu.DAYOFMONTH: 10, s_tu.MONTH: 12, s_tu.YEAR: 2018}

                # And one-shots for Christmas and last day of Hanukkah of 2018
                cdef = {'useriden': rootiden, 'iden': 'IDEN4', 'storm': '#happyholidays',
                        'reqs': (xmas, lasthanu)}
                await agenda.add(cdef)

                await asyncio.sleep(0)
                unixtime += 1
                # Nothing should happen
                self.none(lastquery)

                # Advance to the first event on Wednesday the 5th
                unixtime = datetime.datetime(year=2018, month=12, day=5, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=bar]')

                # Then two on the 6th
                unixtime = datetime.datetime(year=2018, month=12, day=6, hour=7, minute=15, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=baz]')
                lastquery = None
                unixtime = datetime.datetime(year=2018, month=12, day=6, hour=8, minute=15, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=baz]')

                # Then back to the 10:15 on Friday
                unixtime = datetime.datetime(year=2018, month=12, day=7, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=bar]')

                # Then Dec 10
                unixtime = datetime.datetime(year=2018, month=12, day=10, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '#happyholidays')

                # Then the Wednesday again
                unixtime = datetime.datetime(year=2018, month=12, day=12, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=bar]')

                # Cancel the Wednesday/Friday appt
                await agenda.delete(guid)
                await self.asyncraises(s_exc.NoSuchIden, agenda.delete(b'1234'))

                # Then Dec 25
                unixtime = datetime.datetime(year=2018, month=12, day=25, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '#happyholidays')

                # Then Jan 6
                unixtime = datetime.datetime(year=2019, month=1, day=6, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=baz]')

                # Modify the last appointment
                await self.asyncraises(ValueError, agenda.mod(guid2, '', ))
                await agenda.mod(guid2, '#baz')
                self.eq(agenda.appts[guid2].query, '#baz')

                # Delete the other recurring appointment
                await agenda.delete(guid2)

                # Then nothing left scheduled
                self.len(0, agenda.apptheap)

                # Test that isrunning updated, cancelling works
                cdef = {'useriden': rootiden, 'iden': 'IDEN5', 'storm': 'inet:ipv4=1 | sleep 120',
                        'reqs': {}, 'incunit': s_agenda.TimeUnit.MINUTE, 'incvals': 1}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                unixtime += 60
                await sync.wait()
                sync.clear()
                self.len(1, core.boss.tasks)
                task = next(iter(core.boss.tasks.values()))
                self.eq(task.info.get('query'), 'inet:ipv4=1 | sleep 120')
                self.eq(task.info.get('iden'), guid)

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, True)
                await task.kill()

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, False)
                self.eq(appt.lastresult, 'cancelled')
                await agenda.delete(guid)

                # Test bad queries record exception
                cdef = {'useriden': rootiden, 'iden': '#foo', 'storm': 'IDEN',
                        'reqs': {}, 'incunit': s_agenda.TimeUnit.MINUTE,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                guid = adef.get('iden')

                # bypass the API because it would actually syntax check
                agenda.appts[guid].query = 'badquery'
                unixtime += 60
                await sync.wait()
                sync.clear()

                appt = await agenda.get(guid)
                self.eq(appt.isrunning, False)
                self.eq(appt.lastresult, 'raised exception test exception')

                # Test setting the global enable/disable flag
                # reset
                await agenda.delete(guid)
                lastquery = None
                self.len(0, agenda.apptheap)
                agenda._schedtask.cancel()
                agenda._schedtask = agenda.schedCoro(agenda._scheduleLoop())

                # schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'useriden': rootiden, 'iden': 'IDEN6', 'storm': '[test:str=bar]',
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
                self.none(lastquery)

                appt = await agenda.get(guid)
                self.eq(nexttime, appt.nexttime)
                self.true(appt.enabled)
                self.eq(0, appt.startcount)

                # enable crons and advance time
                agenda.enabled = True

                unixtime = datetime.datetime(year=2019, month=2, day=13, hour=10, minute=16, tzinfo=tz.utc).timestamp()
                await sync.wait()
                sync.clear()
                self.eq(lastquery, '[test:str=bar]')
                self.eq(1, appt.startcount)

    async def test_agenda_persistence(self):
        ''' Test we can make/change/delete appointments and they are persisted to storage '''
        with self.getTestDir() as fdir:

            async with self.getTestCore(dirn=fdir) as core:
                agenda = core.agenda
                # Schedule a query to run every Wednesday and Friday at 10:15am
                cdef = {'useriden': 'visi', 'iden': 'IDEN1', 'storm': '[test:str=bar]',
                        'reqs': {s_tu.HOUR: 10, s_tu.MINUTE: 15},
                        'incunit': s_agenda.TimeUnit.DAYOFWEEK,
                        'incvals': (2, 4)}
                adef = await agenda.add(cdef)
                guid1 = adef.get('iden')

                # every 6th of the month at 7am and 8am (the 6th is a Thursday)
                cdef = {'useriden': 'visi', 'iden': 'IDEN2', 'storm': '[test:str=baz]',
                        'reqs': {s_tu.HOUR: (7, 8), s_tu.MINUTE: 0, s_tu.DAYOFMONTH: 6},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                await agenda.add(cdef)

                # Add an appt with an invalid query
                cdef = {'useriden': 'visi', 'iden': 'BAD1', 'storm': '[test:str=',
                        'reqs': {s_tu.HOUR: (7, 8)},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                badguid1 = adef.get('iden')

                # Add an appt with a bad version in storage
                cdef = {'useriden': 'visi', 'iden': 'BAD2', 'storm': '[test:str=foo]',
                        'reqs': {s_tu.HOUR: (7, 8)},
                        'incunit': s_agenda.TimeUnit.MONTH,
                        'incvals': 1}
                adef = await agenda.add(cdef)
                badguid2 = adef.get('iden')

                adef['ver'] = 1337
                await agenda._hivedict.set(badguid2, adef)

                xmas = {s_tu.DAYOFMONTH: 25, s_tu.MONTH: 12, s_tu.YEAR: 2099}
                lasthanu = {s_tu.DAYOFMONTH: 10, s_tu.MONTH: 12, s_tu.YEAR: 2099}

                await agenda.delete(guid1)

                # And one-shots for Christmas and last day of Hanukkah of 2018
                cdef = {'useriden': 'visi', 'iden': 'IDEN3', 'storm': '#happyholidays',
                        'reqs': (xmas, lasthanu)}
                adef = await agenda.add(cdef)
                guid3 = adef.get('iden')

                await agenda.mod(guid3, '#bahhumbug')

            async with self.getTestCore(dirn=fdir) as core:
                agenda = core.agenda

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
            await core.agenda.stop()
            self.false(core.agenda.enabled)
