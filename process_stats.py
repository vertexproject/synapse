import os
import sys
import glob
import argparse

from pprint import pprint

import numpy as np  # standard convention for this library
import matplotlib.pyplot as m_plt

import synapse.common as s_common

def get_fn_prefix(bn):
    l, r = bn.rsplit('_', 1)

    return l[:-17]

def aggregate_raw_data(raw_data):
    '''
    Aggregate raw data into a workable hierachy.

    Args:
        raw_data:

    Notes:
        Data is aggregated into the following hierarachy:
        1. Prefix
        2. Config name
        3. Experiment name.

        The num_iters value, workfactor, and count (per experiment) are all asserted to be equal.
        Unequal data cannot be combined into the same prefix-config-expreriment name set.

    Returns:
        dict: Dictionary of raw data.
    '''
    retn = {}
    for record in raw_data:
        niters = record.get('niters')
        results = record.get('results')
        workfactor = record.get('workfactor')
        prefix = record.get('prefix', 'NOPREFIX')
        config = record.get('configname', 'NOCONFIGNAME')
        # Preconditions
        assert niters is not None
        assert results is not None
        assert workfactor is not None

        config2aggs = retn.setdefault(prefix, {})
        aggdata = config2aggs.setdefault(config, {})
        assert aggdata.setdefault('niters', niters) == niters
        assert aggdata.setdefault('workfactor', workfactor) == workfactor
        agg_results = aggdata.setdefault('results', {})
        for exp_name, exp_results in results:
            exp_agg_results = agg_results.setdefault(exp_name, {})
            count = exp_results.get('count')
            tottimes = exp_results.get('tottimes')

            # We are using the tottiems value currently; as opposed to
            # aggregating the full set of data. This full set is captured
            # in the measurments key; but we've seen issues with the
            # first value of a given test being a consistent outlier in
            # past benchmark executions.

            assert count is not None
            assert tottimes is not None

            assert exp_agg_results.setdefault('count', count) == count
            exp_agg_tottimes = exp_agg_results.setdefault('tottimes', [])
            exp_agg_tottimes.extend(tottimes)

    return retn

def crunch_data(agg_data):
    '''
    Inplace computation of aggregate data per samples.

    This injects numpy arrays into agg_data.
    '''
    for prefix, configdata in agg_data.items():
        for config, aggdata in configdata.items():
            for exp_name, exp_agg_results in aggdata.get('results').items():
                # print(f'{prefix}|{config}|{exp_name}')
                count = exp_agg_results.get('count')
                tottimes = exp_agg_results.get('tottimes')
                pertimes = [m / count for m in tottimes]
                exp_agg_results['pertimes'] = pertimes
                np_pertimes = np.array(pertimes)
                exp_agg_results['np_pertimes'] = np_pertimes
                # print(f'{prefix}|{config}|{exp_name}|{np_pertimes.mean()}')

def make_graphs(agg_data, outdir):
    '''
    Make matplotlib bar charts for visualizing test differences.

    Args:
        agg_data:
        outdir:

    Returns:

    '''

    pass

def main(argv):
    pars = getParser()

    opts = pars.parse_args(argv)

    fps = sorted(list(glob.glob(os.path.join(opts.input, '*.json'))))
    raw_data = []
    prefs = set()
    for fp in fps:
        fn = os.path.basename(fp)
        pref = get_fn_prefix(fn)
        prefs.add(pref)
        ldta = s_common.jsload(fp)
        ldta['prefix'] = pref
        raw_data.append(ldta)

    agg_data = aggregate_raw_data(raw_data)

    s_common.gendir(opts.output)

    crunch_data(agg_data)
    make_graphs(agg_data, opts.output)

    return 0

def getParser():
    pars = argparse.ArgumentParser()

    pars.add_argument('-i', '--input', type=str, required=True,
                      help='Input directory of json files to parse.')
    pars.add_argument('-o', '--output', type=str, required=True,
                      help='Output directory to save graphs too.')
    return pars

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
