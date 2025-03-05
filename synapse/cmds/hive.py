import os
import shlex
import pprint
import asyncio
import tempfile
import functools
import subprocess

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cmd as s_cmd
import synapse.lib.cli as s_cli
import synapse.lib.json as s_json

ListHelp = '''
Lists all the keys underneath a particular key in the hive.

Syntax:
    hive ls|list [path]

Notes:
    If path is not specified, the root is listed.
'''

GetHelp = '''
Display or save to file the contents of a key in the hive.

Syntax:
    hive get [--file] [--json] {path}
'''

DelHelp = '''
Deletes a key in the cell's hive.

Syntax:
    hive rm|del {path}

Notes:
    Delete will recursively delete all subkeys underneath path if they exist.
'''

EditHelp = '''
Edits or creates a key in the cell's hive.

Syntax:
    hive edit|mod {path} [--string] ({value} | --editor | -f {filename})

Notes:
    One may specify the value directly on the command line, from a file, or use an editor.  For the --editor option,
    the environment variable VISUAL or EDITOR must be set.
'''

class HiveCmd(s_cli.Cmd):
    '''
Manipulates values in a cell's Hive.

A Hive is a hierarchy persistent storage mechanism typically used for configuration data.
'''
    _cmd_name = 'hive'

    _cmd_syntax = (
        ('line', {'type': 'glob'}),  # type: ignore
    )

    def _make_argparser(self):

        parser = s_cmd.Parser(prog='hive', outp=self, description=self.__doc__)

        subparsers = parser.add_subparsers(title='subcommands', required=True, dest='cmd',
                                           parser_class=functools.partial(s_cmd.Parser, outp=self))

        parser_ls = subparsers.add_parser('list', aliases=['ls'], help="List entries in the hive", usage=ListHelp)
        parser_ls.add_argument('path', nargs='?', help='Hive path')

        parser_get = subparsers.add_parser('get', help="Get any entry in the hive", usage=GetHelp)
        parser_get.add_argument('path', help='Hive path')
        parser_get.add_argument('-f', '--file', default=False, action='store',
                                help='Save the data to a file.')
        parser_get.add_argument('--json', default=False, action='store_true', help='Emit output as json')

        parser_rm = subparsers.add_parser('del', aliases=['rm'], help='Delete a key in the hive', usage=DelHelp)
        parser_rm.add_argument('path', help='Hive path')

        parser_edit = subparsers.add_parser('edit', aliases=['mod'], help='Sets/creates a key', usage=EditHelp)
        parser_edit.add_argument('--string', action='store_true', help="Edit value as a single string")
        parser_edit.add_argument('path', help='Hive path')
        group = parser_edit.add_mutually_exclusive_group(required=True)
        group.add_argument('value', nargs='?', help='Value to set')
        group.add_argument('--editor', default=False, action='store_true',
                           help='Opens an editor to set the value')
        group.add_argument('--file', '-f', help='Copies the contents of the file to the path')

        return parser

    async def runCmdOpts(self, opts):
        line = opts.get('line')
        if line is None:
            self.printf(self.__doc__)
            return

        core = self.getCmdItem()

        try:
            opts = self._make_argparser().parse_args(shlex.split(line))
        except s_exc.ParserExit:
            return

        handlers = {
            'list': self._handle_ls,
            'ls': self._handle_ls,
            'del': self._handle_rm,
            'rm': self._handle_rm,
            'get': self._handle_get,
            'edit': self._handle_edit,
            'mod': self._handle_edit,
        }
        await handlers[opts.cmd](core, opts)

    @staticmethod
    def parsepath(path):
        ''' Turn a slash-delimited path into a list that hive takes '''
        return path.split('/')

    async def _handle_ls(self, core, opts):
        path = self.parsepath(opts.path) if opts.path is not None else None
        keys = await core.listHiveKey(path=path)
        if keys is None:
            self.printf('Path not found')
            return
        for key in keys:
            self.printf(key)

    async def _handle_get(self, core, opts):
        path = self.parsepath(opts.path)

        valu = await core.getHiveKey(path)
        if valu is None:
            self.printf(f'{opts.path} not present')
            return

        if opts.json:
            rend = s_json.dumps(valu, indent=True, sort_keys=True)
            prend = rend.decode()
        elif isinstance(valu, str):
            rend = valu.encode()
            prend = valu
        elif isinstance(valu, bytes):
            rend = valu
            prend = pprint.pformat(valu)
        else:
            rend = s_json.dumps(valu, indent=True, sort_keys=True)
            prend = pprint.pformat(valu)

        if opts.file:
            with s_common.genfile(opts.file) as fd:
                fd.truncate(0)
                fd.write(rend)
            self.printf(f'Saved the hive entry [{opts.path}] to {opts.file}')
            return

        self.printf(f'{opts.path}:\n{prend}')

    async def _handle_rm(self, core, opts):
        path = self.parsepath(opts.path)
        await core.popHiveKey(path)

    async def _handle_edit(self, core, opts):
        path = self.parsepath(opts.path)

        if opts.value is not None:
            if opts.value[0] not in '([{"':
                data = opts.value
            else:
                data = s_json.loads(opts.value)
            await core.setHiveKey(path, data)
            return
        elif opts.file is not None:
            with open(opts.file) as fh:
                s = fh.read()
                if len(s) == 0:
                    self.printf('Empty file.  Not writing key.')
                    return
                data = s if opts.string else s_json.loads(s)
                await core.setHiveKey(path, data)
                return

        editor = os.getenv('VISUAL', (os.getenv('EDITOR', None)))
        if editor is None or editor == '':
            self.printf('Environment variable VISUAL or EDITOR must be set for --editor')
            return
        tnam = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as fh:
                old_valu = await core.getHiveKey(path)
                if old_valu is not None:
                    if opts.string:
                        if not isinstance(old_valu, str):
                            self.printf('Existing value is not a string, therefore not editable as a string')
                            return
                        data = old_valu
                    else:
                        try:
                            data = s_json.dumps(old_valu, indent=True, sort_keys=True).decode()
                        except s_exc.MustBeJsonSafe:
                            self.printf('Value is not JSON-encodable, therefore not editable.')
                            return
                    fh.write(data)
                tnam = fh.name
            while True:
                retn = subprocess.call(f'{editor} {tnam}', shell=True)
                if retn != 0:  # pragma: no cover
                    self.printf('Editor failed with non-zero code.  Aborting.')
                    return
                with open(tnam) as fh:
                    rawval = fh.read()
                    if len(rawval) == 0:  # pragma: no cover
                        self.printf('Empty file.  Not writing key.')
                        return
                    try:
                        valu = rawval if opts.string else s_json.loads(rawval)
                    except s_exc.BadJsonText as e:  # pragma: no cover
                        self.printf(f'JSON decode failure: [{e}].  Reopening.')
                        await asyncio.sleep(1)
                        continue

                    # We lose the tuple/list distinction in the telepath round trip, so tuplify everything to compare
                    if (opts.string and valu == old_valu) or (not opts.string and s_common.tuplify(valu) == old_valu):
                        self.printf('Valu not changed.  Not writing key.')
                        return
                    await core.setHiveKey(path, valu)
                    break

        finally:
            if tnam is not None:
                os.unlink(tnam)
