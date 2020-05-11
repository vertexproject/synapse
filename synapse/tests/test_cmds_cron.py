import asyncio
import logging
import datetime
from datetime import timezone as tz
from unittest import mock

import synapse.lib.cmdr as s_cmdr
import synapse.lib.provenance as s_provenance

import synapse.tests.utils as s_t_utils

MINSECS = 60
HOURSECS = 60 * MINSECS
DAYSECS = 24 * HOURSECS

logger = logging.getLogger(__name__)

class CmdCronTest(s_t_utils.SynTest):

    async def test_cron(self):
        MONO_DELT = 1543827303.0
        unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=0, tzinfo=tz.utc).timestamp()
        s_provenance.reset()

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        loop = asyncio.get_running_loop()

        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime):
            async with self.getTestCoreAndProxy() as (realcore, core):

                outp = self.getTestOutp()
                async with await s_cmdr.getItemCmdr(core, outp=outp) as cmdr:

                    async def waitForCron(guid):
                        '''
                        Because the wall clock is "frozen" for this test unless we manually advance it, we can't sleep
                        non-zero amounts.  However, we are running in the same asyncio loop as the agenda.  Just
                        sleep(0) in a loop until the cron job is not running anymore
                        '''
                        for _ in range(30):
                            await asyncio.sleep(0)
                            crons = await core.listCronJobs()
                            cron = [c for c in crons if c.get('iden') == guid][0]
                            if not cron['isrunning']:
                                break
                        else:
                            # the cron job didn't finish after ten sleeps?!
                            self.true(0)

                    # Various silliness

                    await cmdr.runCmdLine('cron')
                    self.true(outp.expect('Manages cron jobs in a cortex'))
                    await cmdr.runCmdLine('cron timemachine')
                    self.true(outp.expect('invalid choice'))

                    await cmdr.runCmdLine('cron list')
                    self.true(outp.expect('No cron jobs found'))

                    await cmdr.runCmdLine('cron ls')
                    self.true(outp.expect('No cron jobs found'))

                    outp.clear()

                    await cmdr.runCmdLine("cron add -M+1,beeroclock {[graph:node='*' :type=m1]}")
                    self.true(outp.expect('failed to parse parameter'))

                    await cmdr.runCmdLine("cron add -m nosuchmonth -d=-2 {#foo}")
                    self.true(outp.expect('failed to parse fixed parameter'))

                    outp.clear()
                    await cmdr.runCmdLine("cron add -m 8nosuchmonth -d=-2 {#foo}")
                    self.true(outp.expect('failed to parse fixed parameter'))

                    await cmdr.runCmdLine("cron add -d Mon -m +3 {#foo}")
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

                    # add a mechanism on which we can wait...
                    await realcore.nodes('$lib.queue.add(foo)')

                    async def getNextFoo():
                        return await asyncio.wait_for(realcore.callStorm('''
                            $foo = $lib.queue.get(foo)
                            ($offs, $retn) = $foo.get()
                            $foo.cull($offs)
                            return($retn)
                        '''), timeout=5)

                    ##################
                    # Start simple: add a cron job that creates a node every minute
                    outp.clear()
                    await cmdr.runCmdLine("cron add -M +1 {$lib.queue.get(foo).put(bar)}")
                    self.true(outp.expect('Created cron job'))
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += 60
                    self.eq('bar', await getNextFoo())

                    await cmdr.runCmdLine('cron list')
                    self.true(outp.expect('(bar)'))

                    # Make sure it ran
                    await cmdr.runCmdLine(f"cron mod {guid[:6]} {{$lib.queue.get(foo).put(baz)}}")
                    self.true(outp.expect('Modified cron job'))
                    await cmdr.runCmdLine(f"cron edit xxx {{[graph:node='*' :type=m2]}}")
                    self.true(outp.expect('does not match'))
                    await cmdr.runCmdLine(f"cron mod xxx yyy")
                    self.true(outp.expect('expected second argument to start with {'))

                    # Make sure the old one didn't run and the new query ran
                    unixtime += 60
                    self.eq('baz', await getNextFoo())

                    outp.clear()

                    # Delete the job
                    await cmdr.runCmdLine(f"cron del {guid}")
                    self.true(outp.expect('Deleted cron job'))
                    await cmdr.runCmdLine(f"cron del xxx")
                    self.true(outp.expect('does not match'))
                    await cmdr.runCmdLine(f"cron rm xxx")
                    self.true(outp.expect('does not match'))

                    # Make sure deleted job didn't run
                    unixtime += 60
                    await asyncio.sleep(0)
                    self.eq(0, await realcore.callStorm('return($lib.queue.get(foo).size())'))

                    # Test fixed minute, i.e. every hour at 17 past
                    unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=10,
                                                 tzinfo=tz.utc).timestamp()
                    await cmdr.runCmdLine("cron add -M 17 {$lib.queue.get(foo).put(faz)}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += 7 * MINSECS

                    self.eq('faz', await getNextFoo())
                    await cmdr.runCmdLine(f"cron del {guid}")

                    ##################

                    # Test day increment
                    await cmdr.runCmdLine("cron add -d +2 {$lib.queue.get(foo).put(d1)}")
                    self.true(outp.expect('Created cron job'))
                    guid1 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += DAYSECS

                    # Make sure it *didn't* run
                    await asyncio.sleep(0)
                    self.eq(0, await realcore.callStorm('return($lib.queue.get(foo).size())'))

                    unixtime += DAYSECS

                    self.eq('d1', await getNextFoo())

                    unixtime += DAYSECS * 2

                    outp.clear()
                    self.eq('d1', await getNextFoo())
                    await cmdr.runCmdLine(f"cron del {guid1}")
                    outp.expect('Deleted cron job')

                    ##################

                    # Test fixed day of week: every Monday and Thursday at 3am
                    unixtime = datetime.datetime(year=2018, month=12, day=11, hour=7, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # A Tuesday

                    outp.clear()
                    await cmdr.runCmdLine("cron add -H 3 -d Mon,Thursday {$lib.queue.get(foo).put(d2)}")
                    self.true(outp.expect('Created cron job'))

                    guid2 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    unixtime = datetime.datetime(year=2018, month=12, day=12, hour=3, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # Now Wednesday

                    outp.clear()
                    await cmdr.runCmdLine(f'cron stat {guid2}')
                    self.true(outp.expect('last start time: Never'))

                    unixtime = datetime.datetime(year=2018, month=12, day=13, hour=3, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('d2', await getNextFoo())

                    outp.clear()
                    await cmdr.runCmdLine(f'cron stat {guid2}')
                    self.true(outp.expect('last start time: 2018'))
                    self.true(outp.expect('dayofweek       0'))

                    outp.clear()
                    await cmdr.runCmdLine(f"cron del {guid2}")
                    outp.expect('Deleted cron job')

                    await cmdr.runCmdLine("cron add -H 3 -d Noday {[graph:node='*' :type=d2]}")
                    self.true(outp.expect('failed to parse day value "Noday"'))

                    ##################

                    # Test fixed day of month: second-to-last day of month
                    await cmdr.runCmdLine("cron add -d-2 -mDec {$lib.queue.get(foo).put(d3)}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime = datetime.datetime(year=2018, month=12, day=29, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    unixtime += DAYSECS

                    self.eq('d3', await getNextFoo())

                    outp.clear()
                    await cmdr.runCmdLine(f"cron del {guid}")
                    outp.expect('Deleted cron job')

                    ##################

                    # Test month increment

                    outp.clear()
                    await cmdr.runCmdLine("cron add -m +2 -d=4 {$lib.queue.get(foo).put(month1)}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    self.true(outp.expect('Created cron job'))

                    unixtime = datetime.datetime(year=2019, month=2, day=4, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('month1', await getNextFoo())

                    outp.clear()
                    await cmdr.runCmdLine(f"cron del {guid}")
                    outp.expect('Deleted cron job')

                    ##################

                    # Test year increment

                    outp.clear()
                    await cmdr.runCmdLine("cron add -y +2 {$lib.queue.get(foo).put(year1)}")
                    guid2 = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]
                    self.true(outp.expect('Created cron job'))

                    unixtime = datetime.datetime(year=2021, month=1, day=1, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday
                    self.eq('year1', await getNextFoo())

                    outp.clear()
                    await cmdr.runCmdLine(f'cron stat {guid2[:6]}')
                    self.true(outp.expect("{'month': 1, 'hour': 0, 'minute': 0, 'dayofmonth': 1}"))

                    outp.clear()
                    await cmdr.runCmdLine(f"cron del {guid2}")
                    outp.expect('Deleted cron job')

                    # Make sure second-to-last day works for February
                    outp.clear()
                    await cmdr.runCmdLine("cron add -m February -d=-2 {$lib.queue.get(foo).put(year2)}")
                    self.true(outp.expect('Created cron job'))

                    unixtime = datetime.datetime(year=2021, month=2, day=27, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('year2', await getNextFoo())

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

                    await cmdr.runCmdLine("at +5 minutes {$lib.queue.get(foo).put(at1)}")

                    unixtime += 5 * MINSECS

                    self.eq('at1', await getNextFoo())

                    await cmdr.runCmdLine("at +1 day +7 days {$lib.queue.get(foo).put(at2)}")
                    guid = outp.mesgs[-1].strip().rsplit(' ', 1)[-1]

                    unixtime += DAYSECS

                    await waitForCron(guid)

                    self.eq('at2', await getNextFoo())

                    unixtime += 6 * DAYSECS + 1

                    self.eq('at2', await getNextFoo())

                    await cmdr.runCmdLine("at 202104170415 {$lib.queue.get(foo).put(at3)}")

                    unixtime = datetime.datetime(year=2021, month=4, day=17, hour=4, minute=15,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('at3', await getNextFoo())
                    outp.clear()

                    ##################

                    # Test 'stat' command
                    await cmdr.runCmdLine(f'cron stat xxx')
                    self.true(outp.expect('provided iden does not match any'))

                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect('last result:     finished successfully with 0 nodes'))
                    self.true(outp.expect('entries:         <None>'))

                    ##################

                    # Test 'enable' 'disable' commands
                    await cmdr.runCmdLine(f'cron enable xxx')
                    self.true(outp.expect('provided iden does not match any'))
                    outp.clear()

                    await cmdr.runCmdLine(f'cron disable xxx')
                    self.true(outp.expect('provided iden does not match any'))
                    outp.clear()

                    await cmdr.runCmdLine(f'cron disable {guid[:6]}')
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect(f'enabled:         N'))
                    outp.clear()
                    await cmdr.runCmdLine(f'cron enable {guid[:6]}')
                    await cmdr.runCmdLine(f'cron stat {guid[:6]}')
                    self.true(outp.expect(f'enabled:         Y'))
                    outp.clear()

                    ###################

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

                # Test manipulating cron jobs as another user
                bond = await realcore.auth.addUser('bond')

                async with realcore.getLocalProxy(user='bond') as tcore:
                    toutp = self.getTestOutp()
                    tcmdr = await s_cmdr.getItemCmdr(tcore, outp=toutp)

                    await tcmdr.runCmdLine('cron list')
                    self.true(toutp.expect('No cron jobs found'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron disable {guid[:6]}')
                    self.true(toutp.expect('provided iden does not match'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron enable {guid[:6]}')
                    self.true(toutp.expect('provided iden does not match'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron edit {guid[:6]} {{#foo}}')
                    self.true(toutp.expect('provided iden does not match'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron del {guid[:6]}')
                    self.true(toutp.expect('provided iden does not match'))

                    # Give explicit perm
                    await core.addUserRule(bond.iden, (True, ('cron', 'get')))

                    toutp.clear()
                    await tcmdr.runCmdLine('cron list')
                    self.true(toutp.expect('root'))

                    await core.addUserRule(bond.iden, (True, ('cron', 'set')))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron disable {guid[:6]}')
                    self.true(toutp.expect('Disabled cron job'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron enable {guid[:6]}')
                    self.true(toutp.expect('Enabled cron job'))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron edit {guid[:6]} {{#foo}}')
                    self.true(toutp.expect('Modified cron job'))

                    await core.addUserRule(bond.iden, (True, ('cron', 'del')))

                    toutp.clear()
                    await tcmdr.runCmdLine(f'cron del {guid[:6]}')
                    self.true(toutp.expect('Deleted cron job'))
