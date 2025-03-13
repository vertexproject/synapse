import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes

class StatsCountByCmd(s_storm.Cmd):
    '''
    Tally occurrences of values and display a bar chart of the results.

    Examples:

        // Show counts of geo:name values referenced by media:news nodes.
        media:news -(refs)> geo:name | stats.countby

        // Show counts of ASN values in a set of IPs.
        inet:ipv4#myips | stats.countby :asn

        // Show counts of attacker names for risk:compromise nodes.
        risk:compromise | stats.countby :attacker::name
    '''

    name = 'stats.countby'
    readonly = True

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('valu', nargs='?', default=s_common.novalu,
                          help='A relative property or variable to tally.')
        pars.add_argument('--reverse', default=False, action='store_true',
                          help='Display results in ascending instead of descending order.')
        pars.add_argument('--size', type='int', default=None,
                          help='Maximum number of bars to display.')
        pars.add_argument('--char', type='str', default='#',
                          help='Character to use for bars.')
        pars.add_argument('--bar-width', type='int', default=50,
                          help='Width of the bars to display.')
        pars.add_argument('--label-max-width', type='int', default=None,
                          help='Maximum width of the labels to display.')
        pars.add_argument('--yield', default=False, action='store_true',
                          dest='yieldnodes', help='Yield inbound nodes.')
        pars.add_argument('--by-name', default=False, action='store_true',
                          help='Print stats sorted by name instead of count.')
        return pars

    async def execStormCmd(self, runt, genr):

        labelwidth = await s_stormtypes.toint(self.opts.label_max_width, noneok=True)
        if labelwidth is not None and labelwidth < 0:
            mesg = f'Value for --label-max-width must be >= 0, got: {labelwidth}'
            raise s_exc.BadArg(mesg=mesg)

        barwidth = await s_stormtypes.toint(self.opts.bar_width)
        if barwidth < 0:
            mesg = f'Value for --bar-width must be >= 0, got: {barwidth}'
            raise s_exc.BadArg(mesg=mesg)

        byname = await s_stormtypes.tobool(self.opts.by_name)

        counts = collections.defaultdict(int)

        usenode = self.opts.valu is s_common.novalu

        async for node, path in genr:
            if self.opts.yieldnodes:
                yield node, path

            if usenode:
                valu = node.repr()
            else:
                valu = self.opts.valu
                if s_stormtypes.ismutable(valu):
                    raise s_exc.BadArg(mesg='Mutable values cannot be used for counting.')

                valu = await s_stormtypes.tostr(await s_stormtypes.toprim(valu))

            counts[valu] += 1

        if len(counts) == 0:
            await runt.printf('No values to display!')
            return

        if byname:
            # Try to sort numerically instead of lexicographically
            def coerce(indx):
                def wrapped(valu):
                    valu = valu[indx]
                    try:
                        return int(valu)
                    except ValueError:
                        return valu
                return wrapped

            values = list(sorted(counts.items(), key=coerce(0)))
            maxv = max(val[1] for val in values)

        else:
            values = list(sorted(counts.items(), key=lambda x: x[1]))
            maxv = values[-1][1]

        size = await s_stormtypes.toint(self.opts.size, noneok=True)
        char = (await s_stormtypes.tostr(self.opts.char))[0]
        reverse = self.opts.reverse

        if reverse:
            order = 1
            if size:
                values = values[:size]
        else:
            order = -1
            if size:
                values = values[len(values) - size:]

        namewidth = 0
        countwidth = 0
        for (name, count) in values:
            if (namelen := len(str(name))) > namewidth:
                namewidth = namelen

            if (countlen := len(str(count))) > countwidth:
                countwidth = countlen

        if labelwidth is not None:
            namewidth = min(labelwidth, namewidth)

        for (name, count) in values[::order]:

            barsize = int((count / maxv) * barwidth)
            bar = ''.ljust(barsize, char)
            line = f'{name[0:namewidth].rjust(namewidth)} | {count:>{countwidth}} | {bar}'

            await runt.printf(line)

@s_stormtypes.registry.registerLib
class LibStats(s_stormtypes.Lib):
    '''
    A Storm Library for statistics related functionality.
    '''
    _storm_locals = (
        {'name': 'tally', 'desc': 'Get a Tally object.',
         'type': {'type': 'function', '_funcname': 'tally',
                  'returns': {'type': 'stat:tally', 'desc': 'A new tally object.', }}},
    )
    _storm_lib_path = ('stats',)

    def getObjLocals(self):
        return {
            'tally': self.tally,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def tally(self):
        return StatTally(path=self.path)

@s_stormtypes.registry.registerType
class StatTally(s_stormtypes.Prim):
    '''
    A tally object.

    An example of using it::

        $tally = $lib.stats.tally()

        $tally.inc(foo)

        for $name, $total in $tally {
            $doStuff($name, $total)
        }

    '''
    _storm_typename = 'stat:tally'
    _storm_locals = (
        {'name': 'inc', 'desc': 'Increment a given counter.',
         'type': {'type': 'function', '_funcname': 'inc',
                  'args': (
                      {'name': 'name', 'desc': 'The name of the counter to increment.', 'type': 'str', },
                      {'name': 'valu', 'desc': 'The value to increment the counter by.', 'type': 'int', 'default': 1, },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'get', 'desc': 'Get the value of a given counter.',
         'type': {'type': 'function', '_funcname': 'get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the counter to get.', },
                  ),
                  'returns': {'type': 'int',
                              'desc': 'The value of the counter, or 0 if the counter does not exist.', }}},
        {'name': 'sorted', 'desc': 'Get a list of (counter, value) tuples in sorted order.',
         'type': {'type': 'function', '_funcname': 'sorted',
                  'args': (
                      {'name': 'byname', 'desc': 'Sort by counter name instead of value.',
                       'type': 'bool', 'default': False},
                      {'name': 'reverse', 'desc': 'Sort in descending order instead of ascending order.',
                       'type': 'bool', 'default': False},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'List of (counter, value) tuples in sorted order.'}}},
    )
    _ismutable = True

    def __init__(self, path=None):
        s_stormtypes.Prim.__init__(self, {}, path=path)
        self.counters = collections.defaultdict(int)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'inc': self.inc,
            'get': self.get,
            'sorted': self.sorted,
        }

    async def __aiter__(self):
        for name, valu in self.counters.items():
            yield name, valu

    def __len__(self):
        return len(self.counters)

    @s_stormtypes.stormfunc(readonly=True)
    async def inc(self, name, valu=1):
        name = await s_stormtypes.tostr(name)
        valu = await s_stormtypes.toint(valu)
        self.counters[name] += valu

    @s_stormtypes.stormfunc(readonly=True)
    async def get(self, name):
        name = await s_stormtypes.tostr(name)
        return self.counters.get(name, 0)

    def value(self):
        return dict(self.counters)

    async def iter(self):
        for item in tuple(self.counters.items()):
            yield item

    @s_stormtypes.stormfunc(readonly=True)
    async def sorted(self, byname=False, reverse=False):
        byname = await s_stormtypes.tobool(byname)
        reverse = await s_stormtypes.tobool(reverse)
        if byname:
            return list(sorted(self.counters.items(), reverse=reverse))
        else:
            return list(sorted(self.counters.items(), key=lambda x: x[1], reverse=reverse))
