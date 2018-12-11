import datetime
import functools

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cli as s_cli
import synapse.lib.cmd as s_cmd
import synapse.lib.syntax as s_syntax
import synapse.lib.trigger as s_trigger

StatHelp = '''
Gives detailed information about a single cron job.

Syntax:
    cron stat <iden prefix>

Notes:
    Any prefix that matches exactly one valid cron job iden is accepted.
'''

DelHelp = '''
Deletes a single cron job.

Syntax:
    cron del <iden prefix>

Notes:
    Any prefix that matches exactly one valid cron job iden is accepted.
'''

ListHelp = '''
List existing cron jobs in a cortex.

Syntax:
    cron list

Example:
    cli> cron list
    user       iden        one-time?  Is running? times started   Last start timeLast finish time storm query
'''

ModHelp = '''
Changes an existing trigger's query.

Syntax:
    trigger mod <iden prefix> <new query>

Notes:
    Any prefix that matches exactly one valid trigger iden is accepted.
'''

AddHelp = '''
Add a recurring cron job to a cortex.

Syntax:
    trigger add [optional arguments] {query}

    --minute, -m int[,int...][=]
    --hour, -h
    --day, -d
    --month, -M
    --year, -y

Notes:
    All times are interpreted as UTC.

    All arguments are interpreted as the job period, unless the value ends in
    an equals sign, in which case the argument is interpreted as the recurrence
    period.  Only one recurrence period parameter may be specified.

    Currently, a fixed unit must not be larger than a specified recurrence
    period.  i.e. '--hour 7= --minute 15' (every 15 minutes from 7-8am?) is not
    supported.

    Value values for fixed hours are 0-23 on a 24-hour clock where midnight is 0.

    If the --day parameter value ends in '=' and is an integer, it is
    interpreted as a fixed day of the month.  A negative integer may be
    specified to count from the end of the month with -1 meaning the last day
    of the month.  All fixed day values are clamped to valid days, so for
    example '-d 31' will run on February 28.

    If the fixed day parameter is a value in ([Mon, Tue, Wed, Thu, Fri, Sat,
    Sun] if locale is set to English) it is interpreted as a fixed day of the
    week.  If the parameter value does not end in an '=', then it is
    interpreted as an recurrence interval of that many days.

    If no non-equals-sign-ending parameter is specified, the recurrence period
    defaults to the unit larger than all the fixed parameters.   e.g. '-m 5='
    means every hour at 5 minutes past, and -h 3=, -m 1= means 3:01 every day.

    At least one optional parameter must be provided.

    All parameters accept multiple comma-separated values.  If multiple
    parameters have multiple values, all combinations of those values are used.

    All fixed units not specified lower than the recurrence period default to
    the lowest valid value, e.g. -M 2 will be scheduled at 12:00am the first of
    every other month.  One exception is the largest fixed value is day of the week, then the default
    period is set to be a week.

    A month period with a day of week or day of month fixed value is not currently supported.

    Fixed-value year (i.e. --year 2019=) is not supported.  See the 'at'
    command for one-time cron jobs.

Examples:
    Run a query every last day of the month at 3 am
    cron -h 3= -d -1=

    Run a query every 8 hours
    cron -h 8

    Run a query every Wednesday and Sunday at midnight and noon
    cron -h 0,12= -d Wed,Sun= {}

    Run a query every other day at 3:57pm
    cron -d 2 -m 57= -h 15
'''

class Cron(s_cli.Cmd):
    '''
Manages cron jobs in a cortex.  Cron jobs are rules persistently stored in a
cortex such that storm queries automatically run on a time schedule.   Cron
jobs maybe be recurring or one-time.

A subcommand is required.  Use 'cron -h' for more detailed help.  '''
    _cmd_name = 'at'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),
    )

    async def _match_idens(self, core, prefix):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        idens = [iden for iden, trig in await core.listCronJobs()]
        matches = [iden for iden in idens if s_common.ehex(iden).startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized cron job')
        else:
            self.printf('Error: provided iden matches more than one cron job')
        return None

    def _make_argparser(self):

        parser = s_cmd.Parser(prog='trigger', outp=self, description=self.__doc__)

        subparsers = parser.add_subparsers(title='subcommands', required=True, dest='cmd',
                                           parser_class=functools.partial(s_cmd.Parser, outp=self))

        subparsers.add_parser('list', help="List cron jobs you're allowed to manipulate", usage=ListHelp)

        parser_del = subparsers.add_parser('del', help='delete a trigger', usage=DelHelp)
        parser_del.add_argument('prefix', help='Trigger iden prefix')
        parser_add = subparsers.add_parser('add', help='add a cron job', usage=AddHelp)
        parser_add.add_argument('--minute', '-m')
        parser_add.add_argument('--hour', '-h')
        parser_add.add_argument('--day', '-d')
        parser_add.add_argument('--month', '-M')
        parser_add.add_argument('--year', '-y')
        parser_add.add_argument('query', help='Storm query in curly braces')

        parser_del = subparsers.add_parser('del', help='delete a cron job', usage=DelHelp)
        parser_del.add_argument('prefix', help='Trigger iden prefix')

        parser_mod = subparsers.add_parser('mod', help='change an existing cron jobquery', usage=ModHelp)
        parser_mod.add_argument('prefix', help='Trigger iden prefix')
        parser_mod.add_argument('query', help='Storm query in curly braces')

        parser_stat = subparsers.add_parser('mod', help='details an existing cron job', usage=ModHelp)
        parser_stat.add_argument('prefix', help='Trigger iden prefix')
        return parser

    @staticmethod
    def _validate_incval(self, incunit, incval):
        pass

    async def _handle_add(self, core, opts):
        incunit = None
        incval = None
        reqdict = {}
        valinfo = {
            'month': (1, 'year'),
            'day': (1, 'month'),
            'hour': (0, 'day'),
            'minute': (0, 'hour'),
        }
        dayofweekreq = None
        dayofmonth = None

        for optname in ('year', 'month', 'day', 'hour', 'minute'):
            optval = opts.get(optname)

            if optval is None:
                if incunit is None:
                    continue
                reqdict[optname] = valinfo[optname][0]

            if optval[-1] != '=':
                if incunit is not None:
                    self.printf('Error: may not provide more than 1 recurrence parameter')
                    return
                if reqdict:
                    self.printf('Error: fixed unit may not be larger than recurrence unit')
                    return
                incunit = optname
                incval = self._parse_incval(optname, optval)
                if incval is None:
                    return
                continue

            if optname == 'year':
                self.printf('Error: year may not be a fixed value')
                return

            if optname == 'day':
                # Both fixed day options actual get encoded in the recurring part
                reqkey, reqval = self._parse_req(optname, optval)
                if incunit is not None:
                    self.printf('May not provide a recurrence value with day of week or day of month')
                    return
                if reqdict:
                    self.printf('Error: may not fix month or year with day of week or day of month')
                    return
                dayunit, dayval = self._parse_day(optval)
                if key is None:
                    return
                incunit = dayunit
                incval = dayval

            reqkey, reqval = self._parse_req(optname, optval)
            if reqval is None:
                return
            reqdict[reqkey] = reqval

        # Set the default incunit, incval if necessary
        if incunit is None:
            if not defval:
                self.printf('Must provide at least one optional argument')
                return
            requnit = next(iter(reqdict))
            incunit = valinfo[requnit][1]
            incval = 1

        # Remove the curly braces
        query = query[1:-1]

        await core.addCronJob(query, reqdict, incunit, incval)

    @staticmethod
    def _format_timestamp(ts):
        # N.B. normally better to use fromtimestamp with UTC timezone, but we don't want timezone to print out
        return datetime.datetime.utcfromtimestamp(ts).isoformat(timespec='minutes')

    async def _handle_list(self, core, opts):
        cronlist = await core.listCronJobs()

        if not cronlist:
            self.printf('No cron jobs found')
            return
        self.printf(
            f'{"user":10} {"iden":12} {"recurs?":1} {"now?":1} '
            '{"# start":2} {"last start":16} {"last end":16} {"query"}')

        for iden, cron in cronlist:
            idenf = s_common.ehex(iden)[:8] + '..'
            user = cron.get('user') or '<None>'
            query = cron.get('storm') or '<missing>'
            isrecur = 'Y' if cron.recur else 'N'
            isrunning = 'Y' if cron.isrunning else 'N'
            startcount = cron.get('startcount') or 0
            laststart = cron.get('laststarttime')
            lastend = cron.get('lastfinishtime')
            laststart = 'Never' if laststart is None else self._format_timestamp(laststart)
            lastend = 'Never' if lastend is None else self._format_timestamp(laststart)

            self.printf(
                f'{user:10} {idenf:12} {isrecur:7} {isrunning:1} {startcount:2} {laststart:16} {lastend:16} {query}')

    async def _handle_mod(self, core, opts):
        prefix = opts.prefix
        query = opts.query
        if not query.startswith('{'):
            self.printf('Expected second argument to start with {')
            return
        # remove the curly braces
        query = query[1:-1]
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.updateCron(iden, query)
        self.printf(f'Modified cron job {s_common.ehex(iden)}')

    async def _handle_del(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.delCronJob(iden)
        self.printf(f'Deleted cron job {s_common.ehex(iden)}')

    async def _handle_stat(self, core, opts):
        ''' Prints details about a particular cron job. Not actually a different API call '''
        prefix = opts.prefix
        crondict = await core.listCronJobs()
        idens = crondict.keys()
        matches = [iden for iden in idens if s_common.ehex(iden).startswith(prefix)]
        if len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized cron job')
        elif len(matches) > 1:
            self.printf('Error: provided iden matches more than one cron job')

        cron = crondict[matches[0]]

        idenf = s_common.ehex(iden)
        user = cron.get('user') or '<None>'
        query = cron.get('storm') or '<missing>'
        isrecur = 'Y' if cron.recur else 'N'
        startcount = cron.get('startcount') or 0
        recs = cron.get('recs', [])
        laststart = cron.get('laststarttime')
        lastend = cron.get('lastfinishtime')
        laststart = 'Never' if laststart is None else self._format_timestamp(laststart)
        lastend = 'Never' if lastend is None else self._format_timestamp(laststart)

        self.printf(f'iden:            {idenf}')
        self.printf(f'user:            {user}')
        self.printf(f'recurring:       {isrecur}')
        self.printf(f'# starts:        {startcount}')
        self.printf(f'last start time: {laststart}')
        self.printf(f'last end time:   {lastend}')
        self.printf(f'query:           {query}')
        if not recs:
            self.printf(f'combos:      None')
        else:
            self.printf(f'combos:          {"incunit":10} {"incval":4} {"reqdict"}')
            for reqdict, incunit, incval in recs:
                self.printf(f'                 {incunit:10} {incval:4} {reqdict}')

    async def runCmdOpts(self, opts):
        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        parseinfo = await s_syntax.getRemoteParseInfo(core)
        argv = s_syntax.Parser(parseinfo, line).stormcmd()
        try:
            opts = self._make_argparser().parse_args(argv)
        except s_exc.ParserExit:
            return

        handlers = {
            'add': self._handle_add,
            'list': self._handle_list,
            'mod': self._handle_mod,
            'del': self._handle_del,
            'stat': self._handle_stat
        }
        await handlers[opts.cmd](core, opts)

class At(s_cli.Cmd):
    '''
Adds a non-recurring cron job that will execute a Storm query at one or more
specified times.

List/details/deleting cron jobs created with 'at' use the same commands as other
cron jobs:  cron list/stat/del respectively.

Syntax: at (ISO 8601|+time delta)+ {query}

Notes: This command accepts one or more time specifications followed by exactly
one storm query in curly braces.  Each time specification may be in ISO-8601
datetime format (e.g. 2018-12-10T14:35:49.626722) or simply HH:MM.  Note that
seconds and fractions of seconds will be ignore in the specification.

    All times are immediately converted into UTC, so any daylight saving
    changes between now and the specified time will not be accounted for.

    The other option for time specification is a relative time from now.  This
    consists of an integer followed by a single character out of m,h,d,M,Y
    corresponding to minutes, hours, days, months, and years.


Examples:
    # Run a storm query in 5 minutes
    at +5m {[inet:ipv4=1]}

    # Run a storm query tomorrow and in a week
    at +1d +7d {[inet:ipv4=1]}

    # Run a query at the end of the year Zulu
    at 2018-12-31Z23:59 15:30 {[inet:ipv4=1]}
'''
    _cmd_name = 'at'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),
    )

    def _make_argparser(self):

        parser = s_cmd.Parser(prog='at', outp=self, description=self.__doc__)
        parser.add_argument('args', metavar='times', nargs='+', help='ISO 8601 | +number[mhdMY] | {query} | HH:MM)'
        return parser
