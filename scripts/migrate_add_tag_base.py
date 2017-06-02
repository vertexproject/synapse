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
import synapse.telepath as s_telepath

logger = logging.getLogger(__name__)

def upgrade_tagbase_xact(core, nodes):
    '''
    Wrap the upgrade of a local cortex in a transaction.
    '''
    with core.getCoreXact() as xact:
        upgrade_tagbase_no_xact(core, nodes)

def upgrade_tagbase_no_xact(core, nodes):
    '''
    Upgrade a set of tag nodes to have syn:tag:base properties.
    '''
    node_count = 0
    for node in nodes:
        tag = node[1].get('syn:tag')
        if not tag:
            continue
        if 'syn:tag:base' in node[1]:
            logger.debug('Skipping: [%s]', tag)
            continue
        parts = tag.split('.')
        base = parts[-1]
        logger.debug('Setting syn:tag:base for [%s] to [%s]', tag, base)
        core.setTufoProps(node, base=base)
        node_count += 1
    logger.debug('Migrated %s tag nodes.', node_count)

def get_nodes_to_migrate(core):
    logger.info('Getting tag nodes to migrate')
    nodes = core.eval('syn:tag -syn:tag:base')
    return nodes

# noinspection PyMissingOrEmptyDocstring
def main(options):  # pragma: no cover
    if not options.verbose:
        logging.disable(logging.DEBUG)

    url = options.core
    logger.info('Opening URL %s', url)
    core = s_cortex.openurl(url)
    nodes = get_nodes_to_migrate(core)
    is_telepath = s_telepath.isProxy(core)
    if is_telepath:
        nodes = list(nodes)
    if not nodes:
        logger.info('No nodes to upgrade.')
        return 0
    logger.info('Got {} tags'.format(len(nodes)))
    # Order the nodes.
    nodes.sort(key=lambda x: x[1].get('syn:tag'))

    if is_telepath:
        upgrade_tagbase_no_xact(core, nodes)
    else:
        upgrade_tagbase_xact(core, nodes)
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
