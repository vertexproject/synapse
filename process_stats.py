import os
import sys
import glob
import argparse

import numpy as np  # standard convention for this library
import matplotlib.pyplot as m_plt

import synapse.common as s_common

import synapse.lib.json as s_json

def get_fn_prefix(bn):
    l, r = bn.rsplit('_', 1)

    return l[:-17]

def aggregate_raw_data(raw_data):
    '''
    Aggregate raw data into a workable hierarchy.

    Args:
        raw_data:

    Notes:
        Data is aggregated into the following hierarachy:
        1. Prefix
        2. Config name
        3. Experiment name.

        The num_iters value, workfactor, and count (per experiment) are all asserted to be equal.
        Unequal data cannot be combined into the same prefix-config-experiment name set.

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
    print('Inplace data crunching')
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

    Charts are made with the following hierarchies
    1. For each prefix, for each experiment, show the mean times across all the configs.
    2. For each experiment, for each config, show the mean times across all the prefixes.

    Error bars are inserted into chars as standard deviation values.

    Args:
        agg_data:
        outdir:

    Returns:
        None
    '''
    p2e2c2d = {}
    e2c2p2d = {}
    for prefix, configdata in agg_data.items():
        for config, aggdata in configdata.items():
            for exp_name, exp_agg_results in aggdata.get('results').items():
                np_pertimes = exp_agg_results.get('np_pertimes')

                # rollup Set 1
                e2c2d = p2e2c2d.setdefault(prefix, {})
                c2d = e2c2d.setdefault(exp_name, {})

                c2d[config] = np_pertimes
                e2c2d[exp_name] = c2d

                # rollup Set 2
                c2p2d = e2c2p2d.setdefault(exp_name, {})
                p2d = c2p2d.setdefault(config, {})

                p2d[prefix] = np_pertimes
                c2p2d[config] = p2d

    # Generate first set of charts.
    print('Making first set of charts.')
    for prefix, e2c2d in p2e2c2d.items():
        for exp_name, c2d in e2c2d.items():
            configs = sorted(c2d.keys())

            means = [np.mean(c2d.get(c)) for c in configs]
            stds = [np.std(c2d.get(c)) for c in configs]
            x_pos = np.arange(len(configs))

            # Make our plots...

            fig, ax = m_plt.subplots()
            ax.bar(x_pos, means, yerr=stds, align='center',
                   alpha=0.5, ecolor='black', capsize=10)
            ax.set_ylabel('time units. Lower is better.')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(configs)
            fig.autofmt_xdate()
            ax.set_title(f'{prefix} -> {exp_name}')
            ax.yaxis.grid(True)

            # Save the figure and show
            fp = s_common.genpath(outdir, f'{prefix}_{exp_name}.png')
            m_plt.savefig(fp)
            m_plt.close(fig)

    print('Making second set of charts.')
    for exp_name, c2p2d in e2c2p2d.items():
        for config, p2d in c2p2d.items():
            prefixes = sorted(p2d.keys())

            means = [np.mean(p2d.get(p)) for p in prefixes]
            stds = [np.std(p2d.get(p)) for p in prefixes]
            x_pos = np.arange(len(prefixes))

            # Make our plots...

            fig, ax = m_plt.subplots()
            ax.bar(x_pos, means, yerr=stds, align='center',
                   alpha=0.5, ecolor='black', capsize=10)
            ax.set_ylabel('time units. Lower is better.')
            ax.set_xticks(x_pos)
            ax.set_xticklabels(prefixes)
            fig.autofmt_xdate()
            ax.set_title(f'{exp_name} -> {config}')
            ax.yaxis.grid(True)

            # Save the figure and show
            fp = s_common.genpath(outdir, f'{exp_name}_{config}.png')
            m_plt.savefig(fp)
            m_plt.close(fig)

    print('Done making charts.')

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
        ldta = s_json.jsload(fp)
        ldta.setdefault('prefix', pref)
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
