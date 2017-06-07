#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
synapse - migrate_add_tag_base.py
Created on 6/1/17.

Cortex migration script for migrating a cortex without tag:base values set.
'''
# Stdlib
import argparse
import logging
import sys
# Third Party Code
import synapse.cortex as s_cortex
import synapse.lib.tufo as s_tufo
import synapse.telepath as s_telepath
import synapse.cores.common as s_cores_common

logger = logging.getLogger(__name__)


def upgrade_dark_tags_xact(core, nodes):
    '''
    Wrap the upgrade of a local cortex in a transaction.
    '''
    with core.getCoreXact() as xact:
        upgrade_dark_tags_no_xact(core, nodes)

def upgrade_dark_tags_no_xact(core, tagforms):
    '''
    Upgrade a set of nodes defined by tag, form values to have dark tags.
    '''
    node_count = 0
    for tag, form in tagforms:
        tufos = core.getTufosByTag(form, tag)
        for tufo in tufos:
            if core.getTufoDarkValus(tufo, 'tag'):
                # We've probably already processed the tags on this tufo
                logger.debug('Skipping: [%s]', tufo[0])
                continue
            ttags = s_tufo.tags(tufo)
            for ttag in ttags:
                core.addTufoDark(tufo, 'tag', ttag)
            logger.debug('Added dark tags to [%s]', tufo[0])
            node_count += 1
    logger.info('Added dark tags to {} nodes.'.format(node_count))

# noinspection PyMissingOrEmptyDocstring
def main(options):  # pragma: no cover
    if not options.verbose:
        logging.disable(logging.DEBUG)

    url = options.core
    logger.info('Opening URL %s', url)
    core = s_cortex.openurl(url)  # type: s_cores_common.Cortex
    tag_nodes = core.eval('syn:tag')
    logger.info('Got {} tag nodes'.format(len(tag_nodes)))
    tags = [node[1].get('syn:tag') for node in tag_nodes]
    tags.sort()
    # Do model introspection to get tagged forms since we need to be able to pull nodes by tag.
    tagforms = [(tag, tufo[1].get('syn:tagform:form')) for tag in tags
                for tufo in core.getTufosByProp('syn:tagform:tag', tag)
                if tufo[1].get('syn:tagform:form') != 'syn:tag']
    logger.info('Got {} tagforms'.format(len(tagforms)))
    if s_telepath.isProxy(core):
        upgrade_dark_tags_no_xact(core, tagforms)
    else:
        upgrade_dark_tags_xact(core, tagforms)
    logger.info('Done upgrading nodes.')
    return 0

# noinspection PyMissingOrEmptyDocstring
def makeargpaser():  # pragma: no cover
    parser = argparse.ArgumentParser(description="Migration script for adding syn:tag:base values to nodes.")
    parser.add_argument('-c', '--core', dest='core', required=True, type=str, action='store',
                        help='Cortex to upgrade')
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Enable verbose output')
    return parser

def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    p = makeargpaser()
    opts = p.parse_args()
    main(opts)

if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
