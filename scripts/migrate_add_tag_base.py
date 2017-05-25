# Cortex migration script for migrating a cortex without tag:base values set.
import sys
import synapse.cortex as s_cortex
url = sys.argv[1]
print('Opening URL {}'.format(url))
core = s_cortex.openurl(url)
print('Getting tags')
nodes = core.eval('syn:tag -syn:tag:base')
print('Got {} tags'.format(len(nodes)))
i = 0
# Order the nodes.
nodes.sort(key=lambda x: x[1].get('syn:tag'))
with core.getCoreXact() as xact:
    for node in nodes:
        tag = node[1].get('syn:tag')
        if 'syn:tag:base' in node[1]:
            print('Skipping: [{}]'.format(tag))
            continue
        parts = tag.split('.')
        base = parts[-1]
        print('Setting syn:tag:base for [{}] to [{}]'.format(tag, base))
        core.setTufoProps(node, base=base)
        i += 1
print('Migrated {} tag nodes.'.format(i))
