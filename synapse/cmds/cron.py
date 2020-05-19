import time
import types
import calendar
import datetime
import functools

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cli as s_cli
import synapse.lib.cmd as s_cmd
import synapse.lib.time as s_time
import synapse.lib.parser as s_parser

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
    cron del|rm <iden prefix>

Notes:
    Any prefix that matches exactly one valid cron job iden is accepted.
'''

ListHelp = '''
List existing cron jobs in a cortex.

Syntax:
    cron list|ls

Example:
    user       iden       en? rpt? now? err? # start last start       last end         query
    root       029ce7bd.. Y   Y    N           17863 2019-06-11T21:47 2019-06-11T21:47 exec foo
    root       06b46533.. Y   Y    N           18140 2019-06-11T21:48 2019-06-11T21:48 exec bar
'''

ModHelp = '''
Changes an existing cron job's query.

Syntax:
    cron mod|edit <iden prefix> <new query>

Notes:
    Any prefix that matches exactly one valid cron iden is accepted.
'''

EnableHelp = '''
Enable an existing cron job.

Syntax:
    cron enable <iden prefix>

Notes:
    Any prefix that matches exactly one valid cron iden is accepted.
'''

DisableHelp = '''
Disable an existing cron job.

Syntax:
    cron disable <iden prefix>

Notes:
    Any prefix that matches exactly one valid cron iden is accepted.
'''

AddHelp = '''
Add a recurring cron job to a cortex.

Syntax:
    cron add [optional arguments] {query}

    --minute, -M int[,int...][=]
    --hour, -H
    --day, -d
    --month, -m
    --year, -y

       *or:*

    [--hourly <min> |
     --daily <hour>:<min> |
     --monthly <day>:<hour>:<min> |
     --yearly <month>:<day>:<hour>:<min>]

Notes:
    All times are interpreted as UTC.

    All arguments are interpreted as the job period, unless the value ends in
    an equals sign, in which case the argument is interpreted as the recurrence
    period.  Only one recurrence period parameter may be specified.

    Currently, a fixed unit must not be larger than a specified recurrence
    period.  i.e. '--hour 7 --minute +15' (every 15 minutes from 7-8am?) is not
    supported.

    Value values for fixed hours are 0-23 on a 24-hour clock where midnight is 0.

    If the --day parameter value does not start with in '+' and is an integer, it is
    interpreted as a fixed day of the month.  A negative integer may be
    specified to count from the end of the month with -1 meaning the last day
    of the month.  All fixed day values are clamped to valid days, so for
    example '-d 31' will run on February 28.

    If the fixed day parameter is a value in ([Mon, Tue, Wed, Thu, Fri, Sat,
    Sun] if locale is set to English) it is interpreted as a fixed day of the
    week.

    Otherwise, if the parameter value starts with a '+', then it is interpreted
    as an recurrence interval of that many days.

    If no plus-sign-starting parameter is specified, the recurrence period
    defaults to the unit larger than all the fixed parameters.   e.g. '-M 5'
    means every hour at 5 minutes past, and -H 3, -M 1 means 3:01 every day.

    At least one optional parameter must be provided.

    All parameters accept multiple comma-separated values.  If multiple
    parameters have multiple values, all combinations of those values are used.

    All fixed units not specified lower than the recurrence period default to
    the lowest valid value, e.g. -m +2 will be scheduled at 12:00am the first of
    every other month.  One exception is the largest fixed value is day of the
    week, then the default period is set to be a week.

    A month period with a day of week fixed value is not currently supported.

    Fixed-value year (i.e. --year 2019) is not supported.  See the 'at'
    command for one-time cron jobs.

    As an alternative to the above options, one may use exactly one of
    --hourly, --daily, --monthly, --yearly with a colon-separated list of
    fixed parameters for the value.  It is an error to use both the individual
    options and these aliases at the same time.

Examples:
    Run a query every last day of the month at 3 am
    cron add -H 3 -d-1 {#foo}

    Run a query every 8 hours
    cron add -H +8 {#foo}

    Run a query every Wednesday and Sunday at midnight and noon
    cron add -H 0,12 -d Wed,Sun {#foo}

    Run a query every other day at 3:57pm
    cron add -d +2 -M 57 -H 15 {#foo}
'''

class Cron(s_cli.Cmd):
    '''
Manages cron jobs in a cortex.

Cron jobs are rules persistently stored in a cortex such that storm queries
automatically run on a time schedule.

Cron jobs may be be recurring or one-time.  Use the 'at' command to add
one-time jobs.

A subcommand is required.  Use 'cron -h' for more detailed help.  '''
    _cmd_name = 'cron'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),  # type: ignore
    )

    async def _match_idens(self, core, prefix):
        '''
        Returns the iden that starts with prefix.  Prints out error and returns None if it doesn't match
        exactly one.
        '''
        idens = [cron['iden'] for cron in await core.listCronJobs()]
        matches = [iden for iden in idens if iden.startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized cron job')
        else:
            self.printf('Error: provided iden matches more than one cron job')
        return None

    def _make_argparser(self):

        parser = s_cmd.Parser(prog='cron', outp=self, description=self.__doc__)

        subparsers = parser.add_subparsers(title='subcommands', required=True, dest='cmd',
                                           parser_class=functools.partial(s_cmd.Parser, outp=self))

        subparsers.add_parser('list', aliases=['ls'], help="List cron jobs you're allowed to manipulate",
                              usage=ListHelp)

        parser_add = subparsers.add_parser('add', help='add a cron job', usage=AddHelp)
        parser_add.add_argument('--minute', '-M')
        parser_add.add_argument('--hour', '-H')
        parser_add.add_argument('--day', '-d', help='day of week, day of month or number of days')
        parser_add.add_argument('--month', '-m')
        parser_add.add_argument('--year', '-y')
        group = parser_add.add_mutually_exclusive_group()
        group.add_argument('--hourly')
        group.add_argument('--daily')
        group.add_argument('--monthly')
        group.add_argument('--yearly')
        parser_add.add_argument('query', help='Storm query in curly braces')

        parser_del = subparsers.add_parser('del', aliases=['rm'], help='delete a cron job', usage=DelHelp)
        parser_del.add_argument('prefix', help='Cron job iden prefix')

        parser_stat = subparsers.add_parser('stat', help='details a cron job', usage=StatHelp)
        parser_stat.add_argument('prefix', help='Cron job iden prefix')

        parser_mod = subparsers.add_parser('mod', aliases=['edit'], help='change an existing cron job', usage=ModHelp)
        parser_mod.add_argument('prefix', help='Cron job iden prefix')
        parser_mod.add_argument('query', help='New Storm query in curly braces')

        parser_en = subparsers.add_parser('enable', help='enable an existing cron job', usage=EnableHelp)
        parser_en.add_argument('prefix', help='Cron job iden prefix')

        parser_dis = subparsers.add_parser('disable', help='disable an existing cron job', usage=DisableHelp)
        parser_dis.add_argument('prefix', help='Cron job iden prefix')

        return parser

    @staticmethod
    def _parse_weekday(val):
        ''' Try to match a day-of-week abbreviation, then try a day-of-week full name '''
        val = val.title()
        try:
            return list(calendar.day_abbr).index(val)
        except ValueError:
            try:
                return list(calendar.day_name).index(val)
            except ValueError:
                return None

    @staticmethod
    def _parse_incval(incunit, incval):
        ''' Parse a non-day increment value. Should be an integer or a comma-separated integer list. '''
        try:
            retn = [int(val) for val in incval.split(',')]
        except ValueError:
            return None

        return retn[0] if len(retn) == 1 else retn

    @staticmethod
    def _parse_req(requnit, reqval):
        ''' Parse a non-day fixed value '''
        assert reqval[0] != '='

        try:
            retn = []
            for val in reqval.split(','):
                if requnit == 'month':
                    if reqval[0].isdigit():
                        retn.append(int(reqval))  # must be a month (1-12)
                    else:
                        try:
                            retn.append(list(calendar.month_abbr).index(val.title()))
                        except ValueError:
                            retn.append(list(calendar.month_name).index(val.title()))
                else:
                    retn.append(int(val))
        except ValueError:
            return None

        if not retn:
            return None

        return retn[0] if len(retn) == 1 else retn

    @staticmethod
    def _parse_day(optval):
        ''' Parse a --day argument '''
        isreq = not optval.startswith('+')
        if not isreq:
            optval = optval[1:]

        try:
            retnval = []
            unit = None
            for val in optval.split(','):
                if not val:
                    raise ValueError
                if val[-1].isdigit():
                    newunit = 'dayofmonth' if isreq else 'day'
                    if unit is None:
                        unit = newunit
                    elif newunit != unit:
                        raise ValueError
                    retnval.append(int(val))
                else:
                    newunit = 'dayofweek'
                    if unit is None:
                        unit = newunit
                    elif newunit != unit:
                        raise ValueError

                    weekday = Cron._parse_weekday(val)
                    if weekday is None:
                        raise ValueError
                    retnval.append(weekday)
            if len(retnval) == 0:
                raise ValueError
        except ValueError:
            return None, None
        if len(retnval) == 1:
            retnval = retnval[0]
        return unit, retnval

    def _parse_alias(self, opts):
        retn = types.SimpleNamespace()
        retn.query = opts.query

        if opts.hourly is not None:
            retn.hour = '+1'
            retn.minute = str(int(opts.hourly))
            return retn

        if opts.daily is not None:
            fields = time.strptime(opts.daily, '%H:%M')
            retn.day = '+1'
            retn.hour = str(fields.tm_hour)
            retn.minute = str(fields.tm_min)
            return retn

        if opts.monthly is not None:
            day, rest = opts.monthly.split(':', 1)
            fields = time.strptime(rest, '%H:%M')
            retn.month = '+1'
            retn.day = day
            retn.hour = str(fields.tm_hour)
            retn.minute = str(fields.tm_min)
            return retn

        if opts.yearly is not None:
            fields = opts.yearly.split(':')
            if len(fields) != 4:
                raise ValueError(f'Failed to parse parameter {opts.yearly}')
            retn.year = '+1'
            retn.month, retn.day, retn.hour, retn.minute = fields
            return retn

        return None

    async def _handle_add(self, core, opts):
        incunit = None
        incval = None
        reqdict = {}
        valinfo = {  # unit: (minval, next largest unit)
            'month': (1, 'year'),
            'dayofmonth': (1, 'month'),
            'hour': (0, 'day'),
            'minute': (0, 'hour'),
        }

        if not opts.query.startswith('{'):
            self.printf('Error: query parameter must start with {')
            return

        try:
            alias_opts = self._parse_alias(opts)
        except ValueError as e:
            self.printf(f'Error: Failed to parse ..ly parameter: {" ".join(e.args)}')
            return

        if alias_opts:
            if opts.year or opts.month or opts.day or opts.hour or opts.minute:
                self.printf('Error: may not use both alias (..ly) and explicit options at the same time')
                return
            opts = alias_opts

        for optname in ('year', 'month', 'day', 'hour', 'minute'):
            optval = getattr(opts, optname, None)

            if optval is None:
                if incunit is None and not reqdict:
                    continue
                # The option isn't set, but a higher unit is.  Go ahead and set the required part to the lowest valid
                # value, e.g. so -m 2 would run on the *first* of every other month at midnight
                if optname == 'day':
                    reqdict['dayofmonth'] = 1
                else:
                    reqdict[optname] = valinfo[optname][0]
                continue

            isreq = not optval.startswith('+')

            if optname == 'day':
                unit, val = self._parse_day(optval)
                if val is None:
                    self.printf(f'Error: failed to parse day value "{optval}"')
                    return
                if unit == 'dayofweek':
                    if incunit is not None:
                        self.printf('Error: May not provide a recurrence value with day of week')
                        return
                    if reqdict:
                        self.printf('Error: may not fix month or year with day of week')
                        return
                    incunit, incval = unit, val
                elif unit == 'day':
                    incunit, incval = unit, val
                else:
                    assert unit == 'dayofmonth'
                    reqdict[unit] = val
                continue

            if not isreq:
                if incunit is not None:
                    self.printf('Error: may not provide more than 1 recurrence parameter')
                    return
                if reqdict:
                    self.printf('Error: fixed unit may not be larger than recurrence unit')
                    return
                incunit = optname
                incval = self._parse_incval(optname, optval)
                if incval is None:
                    self.printf('Error: failed to parse parameter')
                    return
                continue

            if optname == 'year':
                self.printf('Error: year may not be a fixed value')
                return

            reqval = self._parse_req(optname, optval)
            if reqval is None:
                self.printf(f'Error: failed to parse fixed parameter "{optval}"')
                return
            reqdict[optname] = reqval

        # If not set, default (incunit, incval) to (1, the next largest unit)
        if incunit is None:
            if not reqdict:
                self.printf('Error: must provide at least one optional argument')
                return
            requnit = next(iter(reqdict))  # the first key added is the biggest unit
            incunit = valinfo[requnit][1]
            incval = 1

        # Remove the curly braces
        query = opts.query[1:-1]
        cdef = {'storm': query,
                'reqs': reqdict,
                'incunit': incunit,
                'incvals': incval,
                }
        newcdef = await core.addCronJob(cdef)
        self.printf(f'Created cron job {newcdef["iden"]}')

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
            f'{"user":10} {"iden":10} {"en?":3} {"rpt?":4} {"now?":4} {"err?":4} '
            f'{"# start":7} {"last start":16} {"last end":16} {"query"}')

        for cron in cronlist:
            iden = cron.get('iden')

            idenf = iden[:8] + '..'
            user = cron.get('username') or '<None>'
            query = cron.get('query') or '<missing>'
            isrecur = 'Y' if cron.get('recur') else 'N'
            isrunning = 'Y' if cron.get('isrunning') else 'N'
            enabled = 'Y' if cron.get('enabled') else 'N'
            startcount = cron.get('startcount') or 0
            laststart = cron.get('laststarttime')
            laststart = 'Never' if laststart is None else self._format_timestamp(laststart)
            lastend = cron.get('lastfinishtime')
            lastend = 'Never' if lastend is None else self._format_timestamp(lastend)
            result = cron.get('lastresult')
            iserr = 'X' if result is not None and not result.startswith('finished successfully') else ' '

            self.printf(
                f'{user:10} {idenf:10} {enabled:3} {isrecur:4} {isrunning:4} {iserr:4} '
                f'{startcount:7} {laststart:16} {lastend:16} {query}')

    async def _handle_mod(self, core, opts):
        prefix = opts.prefix
        query = opts.query
        if not query.startswith('{'):
            self.printf('Error:  expected second argument to start with {')
            return
        # remove the curly braces
        query = query[1:-1]
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.updateCronJob(iden, query)
        self.printf(f'Modified cron job {iden}')

    async def _handle_enable(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.enableCronJob(iden)
        self.printf(f'Enabled cron job {iden}')

    async def _handle_disable(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.disableCronJob(iden)
        self.printf(f'Disabled cron job {iden}')

    async def _handle_del(self, core, opts):
        prefix = opts.prefix
        iden = await self._match_idens(core, prefix)
        if iden is None:
            return
        await core.delCronJob(iden)
        self.printf(f'Deleted cron job {iden}')

    async def _handle_stat(self, core, opts):
        ''' Prints details about a particular cron job. Not actually a different API call '''
        prefix = opts.prefix
        crons = await core.listCronJobs()
        idens = [cron['iden'] for cron in crons]
        matches = [iden for iden in idens if iden.startswith(prefix)]
        if len(matches) == 0:
            self.printf('Error: provided iden does not match any valid authorized cron job')
            return
        elif len(matches) > 1:
            self.printf('Error: provided iden matches more than one cron job')
            return

        iden = matches[0]
        cron = [cron for cron in crons if cron.get('iden') == iden][0]

        user = cron.get('username') or '<None>'
        query = cron.get('query') or '<missing>'
        isrecur = 'Yes' if cron.get('recur') else 'No'
        enabled = 'Yes' if cron.get('enabled') else 'No'
        startcount = cron.get('startcount') or 0
        recs = cron.get('recs', [])
        laststart = cron.get('laststarttime')
        lastend = cron.get('lastfinishtime')
        laststart = 'Never' if laststart is None else self._format_timestamp(laststart)
        lastend = 'Never' if lastend is None else self._format_timestamp(lastend)
        lastresult = cron.get('lastresult') or '<None>'

        self.printf(f'iden:            {iden}')
        self.printf(f'user:            {user}')
        self.printf(f'enabled:         {enabled}')
        self.printf(f'recurring:       {isrecur}')
        self.printf(f'# starts:        {startcount}')
        self.printf(f'last start time: {laststart}')
        self.printf(f'last end time:   {lastend}')
        self.printf(f'last result:     {lastresult}')
        self.printf(f'query:           {query}')
        if not recs:
            self.printf(f'entries:         <None>')
        else:
            self.printf(f'entries:         {"incunit":10} {"incval":6} {"required"}')
            for reqdict, incunit, incval in recs:
                reqdict = reqdict or '<None>'
                incunit = '<None>' if incunit is None else incunit
                incval = '<None>' if incval is None else incval
                self.printf(f'                 {incunit:10} {incval:6} {reqdict}')

    async def runCmdOpts(self, opts):

        s_common.deprecated('cmdr> cron')

        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        argv = s_parser.Parser(line).cmdrargs()
        try:
            opts = self._make_argparser().parse_args(argv)
        except s_exc.ParserExit:
            return

        handlers = {
            'add': self._handle_add,
            'del': self._handle_del,
            'rm': self._handle_del,
            'disable': self._handle_disable,
            'enable': self._handle_enable,
            'list': self._handle_list,
            'ls': self._handle_list,
            'mod': self._handle_mod,
            'edit': self._handle_mod,
            'stat': self._handle_stat,
        }
        await handlers[opts.cmd](core, opts)

class At(s_cli.Cmd):
    '''
Adds a non-recurring cron job.

It will execute a Storm query at one or more specified times.

List/details/deleting cron jobs created with 'at' use the same commands as
other cron jobs:  cron list/stat/del respectively.

Syntax:
    at (time|+time delta)+ {query}

Notes:
    This command accepts one or more time specifications followed by exactly
    one storm query in curly braces.  Each time specification may be in synapse
    time delta format (e.g + 1 day) or synapse time format (e.g.
    20501217030432101).  Seconds will be ignored, as cron jobs' granularity is
    limited to minutes.

    All times are interpreted as UTC.

    The other option for time specification is a relative time from now.  This
    consists of a plus sign, a positive integer, then one of 'minutes, hours,
    days'.

    Note that the record for a cron job is stored until explicitly deleted via
    "cron del".

Examples:
    # Run a storm query in 5 minutes
    at +5 minutes {[inet:ipv4=1]}

    # Run a storm query tomorrow and in a week
    at +1 day +7 days {[inet:ipv4=1]}

    # Run a query at the end of the year Zulu
    at 20181231Z2359 {[inet:ipv4=1]}
'''
    _cmd_name = 'at'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),  # type: ignore
    )

    def _make_argparser(self):
        parser = s_cmd.Parser(prog='at', outp=self, description=self.__doc__)
        parser.add_argument('args', nargs='+', help='date | delta| {query})')
        return parser

    async def runCmdOpts(self, opts):

        s_common.deprecated('cmdr> at')

        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        argv = s_parser.Parser(line).cmdrargs()
        # Currently, using an argparser is overkill for this command.  Using for future extensibility (and help).
        try:
            opts = self._make_argparser().parse_args(argv)
        except s_exc.ParserExit:
            return

        query = None
        consumed_next = False

        tslist = []
        # TODO: retrieve time from cortex in case of wrong cmdr time
        now = time.time()

        for pos, arg in enumerate(opts.args):
            try:
                if consumed_next:
                    consumed_next = False
                    continue

                if arg.startswith('{'):
                    if query is not None:
                        self.printf('Error: only a single query is allowed')
                        return
                    query = arg[1:-1]
                    continue

                if arg.startswith('+'):
                    if arg[-1].isdigit():
                        if pos == len(opts.args) - 1:
                            self.printf('Time delta missing unit')
                            return
                        arg = f'{arg} {opts.args[pos + 1]}'
                        consumed_next = True
                    ts = now + s_time.delta(arg) / 1000.0
                    tslist.append(ts)
                    continue

                ts = s_time.parse(arg) / 1000.0
                tslist.append(ts)
            except (ValueError, s_exc.BadTypeValu):
                self.printf(f'Error: Trouble parsing "{arg}"')
                return

        if query is None:
            self.printf('Error: Missing query argument')
            return

        def _ts_to_reqdict(ts):
            dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
            return {
                'minute': dt.minute,
                'hour': dt.hour,
                'dayofmonth': dt.day,
                'month': dt.month,
                'year': dt.year
            }

        if not tslist:
            self.printf('Error: at least one requirement must be provided')
            return

        reqdicts = [_ts_to_reqdict(ts) for ts in tslist]

        cdef = {'storm': query,
                'reqs': reqdicts,
                'incunit': None,
                'incvals': None,
                }

        newcdef = await core.addCronJob(cdef)
        self.printf(f'Created cron job {newcdef["iden"]}')
