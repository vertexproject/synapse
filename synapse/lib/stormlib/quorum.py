import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class QuorumMergesLib(s_stormtypes.Lib):
    '''
    A Storm library for accessing quorum merge requests.
    '''
    _storm_lib_path = ('quorum', 'merge')

    _storm_locals = (
        {'name': 'list', 'desc': 'List pending merge requests.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'todo', 'type': 'bool', 'default': False,
                       'desc': 'Only emit merge requests which require input from the current user.'},
                  ),
                  'returns': {'name': 'yields', 'type': 'list',
                              'desc': 'A tuple of the view and merge summary.'}
         }},
    )

    _storm_query = '''
    function __voted(votes) {
        for $vote in $votes {
            if ($vote.user = $lib.user.iden) {
                return((true))
            }
        }
        return((false))
    }

    function __canvote(roles) {
        for $role in $lib.auth.users.get().roles() {
            if $roles.has($role.iden) { return((true)) }
        }
        return((false))
    }

    function list(todo=(false)) {
        for $view in $lib.view.list() {
            $summary = $view.getMergeRequestSummary()
            if (not $summary) { continue }
            if ($todo) {
                if ($summary.merging) { continue }
                if ($summary.merge.creator = $lib.user.iden) { continue }
                if ($__voted($summary.votes)) { continue }
                if (not $__canvote($summary.quorum.roles)) { continue }
            }
            emit ($view, $summary)
        }
    }
    '''

stormcmds = (
    {
        'name': 'quorum.merge.list',
        'descr': 'List all the views which currently have a pending merge request.',
        'cmdargs': (
            ('--todo', {'help': 'Only return merges which need approval from the current user.',
                       'action': 'store_true'}),
        ),
        'storm': '''
            function main(cmdopts) {
                $rows = ([])
                for ($view, $summary) in $lib.quorum.merge.list(todo=$cmdopts.todo) {

                    $creator = $lib.auth.users.get($summary.merge.creator).name
                    if (not $creator) { $creator = $summary.merge.creator }

                    $created = $lib.repr(time, $summary.merge.created)

                    $updated = ""
                    if $summary.merge.updated { $updated = $lib.repr(time, $summary.merge.updated) }

                    $rows.append(($view.iden, $view.get(name), $creator, $created, $updated))
                }

                if (not $rows) {
                    if $cmdopts.todo {
                        $lib.print("Nothing to do. Go grab some coffee!")
                    } else {
                        $lib.print("No pending merge requests.")
                    }
                    return()
                }

                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "view", "width": 32},
                        {"name": "name", "width": 40},
                        {"name": "creator", "width": 18},
                        {"name": "created", "width": 24},
                        {"name": "updated", "width": 24},
                    ],
                    "separators": {
                        "row:outline": false,
                        "column:outline": false,
                        "header:row": "#",
                        "data:row": "",
                        "column": "",
                    },
                }))

                $lib.print($printer.header())

                for $row in $rows {
                    $lib.print($printer.row($row))
                }
                return()
            }
            $main($cmdopts)
        ''',
    },
)
