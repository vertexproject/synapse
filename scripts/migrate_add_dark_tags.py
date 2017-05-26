#!/usr/bin/env python
import sys
import synapse.cortex as s_cortex
import synapse.lib.tufo as s_tufo
import synapse.cores.common as s_cores_common
url = sys.argv[1]
print('Opening URL {}'.format(url))
core = s_cortex.openurl(url)  # type: s_cores_common.Cortex
print('Getting tags')
nodes = core.eval('syn:tag')
print('Got {} tags'.format(len(nodes)))
i = 0
# Order the tags.
tags = [node[1].get('syn:tag') for node in nodes]
tags.sort()
# Do model introspection to get tagged forms since we need to be able to pull nodes by tag.
tagforms = [(tag, tufo[1].get('syn:tagform:form')) for tag in tags
            for tufo in core.getTufosByProp('syn:tagform:tag', tag)
            if tufo[1].get('syn:tagform:form') != 'syn:tag']
print('Got {} tagforms'.format(len(tagforms)))
with core.getCoreXact() as xact:
    for tag, form in tagforms:
        tufos = core.getTufosByTag(form, tag)
        for tufo in tufos:
            if core.getTufoDarkTypes(tufo, 'tag'):
                # We've already processed the tags on this tufo
                print('Skipping: [{}]'.format(tufo[0]))
                continue
            ttags = s_tufo.tags(tufo)
            for ttag in ttags:
                core.addTufoDark(tufo, 'tag', ttag)
            print('Added dark tags to {}'.format(tufo[0]))
            i += 1
print('Added dark tags to {} nodes.'.format(i))
