import asyncio
import datetime
from datetime import timezone as tz
from unittest import mock

import synapse.lib.cmdr as s_cmdr
import synapse.lib.provenance as s_provenance

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

MINSECS = 60
HOURSECS = 60 * MINSECS
DAYSECS = 24 * HOURSECS

class CmdCronTest(s_t_utils.SynTest):

    async def test_cron(self):
        MONO_DELT = 1543827303.0
        unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=0, tzinfo=tz.utc).timestamp()
        sync = asyncio.Event()
        lastquery = None
        s_provenance.reset()

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        async def myeval(query, user=None):
            nonlocal lastquery
            lastquery = query
            sync.set()
            return
            yield None

        loop = asyncio.get_running_loop()

        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime):
            async with self.getTestCoreAndProxy() as (realcore, core):

                outp = self.getTestOutp()
                async with await s_cmdr.getItemCmdr(core, outp=outp) as cmdr:

                    # Various silliness

                    await cmdr.runCmdLine('cron')
                    self.true(outp.expect('Manages cron jobs in a cortex'))
                    await cmdr.runCmdLine('cron timemachine')
                    self.true(outp.expect('invalid choice'))

                    await cmdr.runCmdLine('cron list')
                    self.true(outp.expect('No cron jobs found'))

                    outp.clear()

                    await cmdr.runCmdLine("cron add -M+1,beeroclock {[graph:node='*' :type=m1]}")
                    self.true(outp.expect('failed to parse parameter'))

                    await cmdr.runCmdLine("cron add -m nosuchmonth -d=-2 {#foo}")
                    self.true(outp.expect('failed to parse fixed parameter'))

                    outp.clear()
                    await cmdr.runCmdLine("cron add -m 8nosuchmonth -d=-2 {#foo}")
                    self.true(outp.expect('failed to parse fixed parameter'))

                    await cmdr.runCmdLine("cron add -d=, {#foo}")
                    self.true(outp.expect('failed to parse day value'))

                    await cmdr.runCmdLine("cron add -dMon -m +3 {#foo}")
                    self.true(outp.expect('provide a recurrence value with day of week'))

                    await cmdr.runCmdLine("cron add -dMon -m June {#foo}")
                    self.true(outp.expect('fix month or year with day of week'))

                    await cmdr.runCmdLine("cron add -dMon -m +3 -y +2 {#foo}")
                    self.true(outp.expect('more than 1 recurrence'))

                    await cmdr.runCmdLine("cron add --year=2019 {#foo}")
                    self.true(outp.expect('year may not be a fixed value'))

                    await cmdr.runCmdLine("cron add {#foo}")
                    self.true(outp.expect('must provide at least one optional'))

                    await cmdr.runCmdLine("cron add -H3 -M +4 {#foo}")
                    self.true(outp.expect('fixed unit may not be larger'))

                    outp.clear()
                    await cmdr.runCmdLine('cron add -d Tuesday,1 {#foo}')
                    self.true(outp.expect('failed to parse day value'))

                    outp.clear()
                    await cmdr.runCmdLine('cron add -d Fri,3 {#foo}')
                    self.true(outp.expect('failed to parse day value'))

                    outp.clear()
                    await cmdr.runCmdLine('cron add }')
                    self.true(outp.expect('BadSyntax'))

                    ##################
                    oldsplices = len(await alist(core.splices(0, 1000)))

                    # Start simple: add a cron job that creates a node every minute
                    outp.clear()
                    await cmdr.runCmdLine("cron add -M +1 {[graph:node='*' :type=m1]}")
                    self.true(outp.expect('Created cron job'))
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += 60
                    await cmdr.runCmdLine('cron list')
                    self.true(outp.expect(':type=m1'))

                    # Make sure it ran
                    await self.agenlen(1, core.eval('graph:node:type=m1'))

                    # Make sure the provenance of the new splices looks right
                    splices = await alist(core.splices(oldsplices, 1000))
                    self.gt(len(splices), 1)
                    aliases = [splice[1]['prov'] for splice in splices]
                    self.true(all(a == aliases[0] for a in aliases))
                    prov = await core.getProvStack(aliases[0])
                    rootiden = prov[1][1][1]['user']
                    correct = ({}, (
                               ('cron', {'iden': guid}),
                               ('storm', {'q': "[graph:node='*' :type=m1]", 'user': rootiden})))
                    self.eq(prov, correct)

                    await cmdr.runCmdLine(f"cron mod {guid[:6]} {{[graph:node='*' :type=m2]}}")
                    self.true(outp.expect('Modified cron job'))
                    await cmdr.runCmdLine(f"cron mod xxx {{[graph:node='*' :type=m2]}}")
                    self.true(outp.expect('does not match'))
                    await cmdr.runCmdLine(f"cron mod xxx yyy")
                    self.true(outp.expect('expected second argument to start with {'))

                    # Make sure the old one didn't run and the new query ran
                    unixtime += 60
                    await self.agenlen(1, core.eval('graph:node:type=m1'))
                    await self.agenlen(1, core.eval('graph:node:type=m2'))

                    outp.clear()

                    # Delete the job
                    await cmdr.runCmdLine(f"cron del {guid}")
                    self.true(outp.expect('Deleted cron job'))
                    await cmdr.runCmdLine(f"cron del xxx")
                    self.true(outp.expect('does not match'))

                    # Make sure deleted job didn't run
                    unixtime += 60
                    await self.agenlen(1, core.eval('graph:node:type=m1'))
                    await self.agenlen(1, core.eval('graph:node:type=m2'))

                    # Test fixed minute, i.e. every hour at 17 past
                    unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=10,
                                                 tzinfo=tz.utc).timestamp()
                    await cmdr.runCmdLine("cron add -M 17 {[graph:node='*' :type=m3]}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += 7 * MINSECS

                    # Make sure it runs.  We add the cron list to give the cron scheduler a chance to run
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=m3'))
                    await cmdr.runCmdLine(f"cron del {guid}")

                    ##################

                    # Test day increment
                    await cmdr.runCmdLine("cron add -d +2 {[graph:node='*' :type=d1]}")
                    self.true(outp.expect('Created cron job'))
                    guid1 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += DAYSECS

                    # Make sure it *didn't* run
                    await self.agenlen(0, core.eval('graph:node:type=d1'))

                    unixtime += DAYSECS

                    # Make sure it runs.  We add the cron list to give the cron scheduler a chance to run

                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=d1'))

                    unixtime += DAYSECS * 2
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(2, core.eval('graph:node:type=d1'))

                    ##################

                    # Test fixed day of week: every Monday and Thursday at 3am
                    unixtime = datetime.datetime(year=2018, month=12, day=11, hour=7, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # A Tuesday

                    await cmdr.runCmdLine("cron add -H 3 -d Mon,Thursday {[graph:node='*' :type=d2]}")
                    guid2 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    unixtime = datetime.datetime(year=2018, month=12, day=13, hour=3, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=d2'))

                    await cmdr.runCmdLine(f"cron del {guid1}")
                    await cmdr.runCmdLine(f"cron del {guid2}")

                    await cmdr.runCmdLine("cron add -H 3 -d Noday {[graph:node='*' :type=d2]}")
                    self.true(outp.expect('failed to parse day value "Noday"'))

                    ##################

                    # Test fixed day of month: second-to-last day of month
                    await cmdr.runCmdLine("cron add -d-2 -mDec {[graph:node='*' :type=d3]}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime = datetime.datetime(year=2018, month=12, day=29, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(0, core.eval('graph:node:type=d3'))  # Not yet
                    unixtime += DAYSECS
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=d3'))
                    await cmdr.runCmdLine(f"cron del {guid}")

                    ##################

                    # Test month increment

                    await cmdr.runCmdLine("cron add -m +2 -d=4 {[graph:node='*' :type=month1]}")

                    unixtime = datetime.datetime(year=2019, month=2, day=4, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=month1'))

                    ##################

                    # Test year increment

                    await cmdr.runCmdLine("cron add -y +2 {[graph:node='*' :type=year1]}")
                    guid2 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    unixtime = datetime.datetime(year=2021, month=1, day=1, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=year1'))

                    # Make sure second-to-last day works for February
                    await cmdr.runCmdLine("cron add -m February -d=-2 {[graph:node='*' :type=year2]}")
                    unixtime = datetime.datetime(year=2021, month=2, day=27, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=year2'))

                    ##################

                    # Test 'at' command
                    outp.clear()
                    await cmdr.runCmdLine('at')
                    self.true(outp.expect('Adds a non-recurring'))

                    await cmdr.runCmdLine('at --not-a-real-flag')
                    self.true(outp.expect('the following arguments'))

                    await cmdr.runCmdLine('at {#foo} {#bar}')
                    self.true(outp.expect('only a single query'))

                    await cmdr.runCmdLine('at {#foo}')
                    self.true(outp.expect('at least'))

                    await cmdr.runCmdLine('at +1')
                    self.true(outp.expect('missing unit'))

                    await cmdr.runCmdLine('at +1parsec')
                    self.true(outp.expect('Trouble parsing'))

                    await cmdr.runCmdLine('at +1day')
                    self.true(outp.expect('Missing query'))

                    await cmdr.runCmdLine("at +5 minutes {[graph:node='*' :type=at1]}")
                    unixtime += 5 * MINSECS
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=at1'))

                    await cmdr.runCmdLine("at +1 day +7 days {[graph:node='*' :type=at2]}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    unixtime += DAYSECS
                    await self.agenlen(1, core.eval('graph:node:type=at2'))
                    unixtime += 6 * DAYSECS + 1
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(2, core.eval('graph:node:type=at2'))

                    await cmdr.runCmdLine("at 202104170415 {[graph:node='*' :type=at3]}")

                    unixtime = datetime.datetime(year=2021, month=4, day=17, hour=4, minute=15,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    await cmdr.runCmdLine('cron list')
                    await self.agenlen(1, core.eval('graph:node:type=at3'))
                    ##################

                    # Test 'stat' command

                    await cmdr.runCmdLine(f'cron stat xxx')
                    self.true(outp.expect('provided iden does not match any'))

                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect('last result:     finished successfully with 1 nodes'))
                    self.true(outp.expect('entries:         <None>'))
                    await cmdr.runCmdLine(f'cron stat {guid2[:6]}')
                    self.true(outp.expect("{'month': 1, 'hour': 0, 'minute': 0, 'dayofmonth': 1}"))

                    ##################

                    # Delete an expired at job
                    outp.clear()
                    await cmdr.runCmdLine(f"cron del {guid}")
                    self.true(outp.expect('Deleted cron job'))

                    ##################

                    # Test the aliases
                    outp.clear()
                    await cmdr.runCmdLine('cron add --hourly 15 {#bar}')
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect("{'minute': 15}"))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --daily 05:47 {#bar}')
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect("{'hour': 5, 'minute': 47"))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --monthly=-1:12:30 {#bar}')
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect("{'hour': 12, 'minute': 30, 'dayofmonth': -1}"))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --yearly 04:17:12:30 {#bar}')
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect("{'month': 4, 'hour': 12, 'minute': 30, 'dayofmonth': 17}"))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --yearly 04:17:12 {#bar}')
                    self.true(outp.expect('Failed to parse parameter'))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --daily xx:xx {#bar}')
                    self.true(outp.expect('Failed to parse ..ly parameter'))

                    outp.clear()
                    await cmdr.runCmdLine('cron add --hourly 1 -M 17 {#bar}')
                    self.true(outp.expect('may not use both'))
