import os
import pickle
import timeit
import cProfile
import itertools
import threading

from math import ceil
from binascii import hexlify
from time import perf_counter as now

import synapse.cortex as s_cortex

from numpy import random

NUM_PREEXISTING_TUFOS = 1000

NUM_TUFOS = 100000
NUM_ONE_AT_A_TIME_TUFOS = 100

HUGE_VAL_BYTES = 1000000
HUGE_VAL_RATE = 0.0001

LARGE_VAL_BYTES = 10000
LARGE_VAL_RATE = 0.005

MEDIUM_VAL_BYTES = 100
MEDIUM_VAL_RATE = .1949

SMALL_VAL_BYTES = 5
SMALL_VAL_RATE = .80

# what percent of properties will have integer value
INTEGER_VAL_RATE = .20

AVG_PROPS_PER_TUFO = 7
AVG_PROP_NAME_LEN = 11

NUM_THREADS = 4
NUM_FORMS = 20

def _addRows(rows, core, one_at_a_time=False):
    if one_at_a_time:
        for row in rows:
            core.addRows([row])
    else:
        core.addRows(rows)
        # core.flush()

def _getTufosByIdens(idens, core):
    core.getTufosByIdens(idens)

def _getTufoByPropVal(propvals, core):
    for p, v in propvals:
        core.getTufoByProp(p, v)

def random_normal(avg):
    ''' Returns a number with normal distribution around avg, the very fast way '''
    return random.randint(1, avg) + random.randint(0, avg + 1)

def random_string(avg):
    num_letters = random_normal(avg)
    return ''.join(chr(random.randint(ord('a'), ord('a') + 25)) for x in range(num_letters))

small_count = 0
medium_count = 0
large_count = 0
huge_count = 0

def random_val_len():
    global small_count, medium_count, large_count, huge_count
    x = random.random()
    prob = SMALL_VAL_RATE
    if x < prob:
        small_count += 1
        return SMALL_VAL_BYTES
    prob += MEDIUM_VAL_RATE
    if x < prob:
        medium_count += 1
        return MEDIUM_VAL_BYTES
    prob += LARGE_VAL_RATE
    if x < prob:
        large_count += 1
        return LARGE_VAL_BYTES
    huge_count += 1
    return HUGE_VAL_BYTES

def gen_random_form():
    num_props = random_normal(AVG_PROPS_PER_TUFO)
    props = [random_string(AVG_PROP_NAME_LEN) for x in range(num_props)]
    return props

def gen_random_tufo(form):
    iden = hexlify(random.bytes(16)).decode('utf8')
    props = {}
    for propname in form:
        if random.random() <= INTEGER_VAL_RATE:
            val = random.randint(-2 ** 62, 2 ** 63)
        else:
            val = random_string(random_val_len())
        props[propname] = val
    return (iden, props)

def _rows_from_tufo(tufo):
    timestamp = random.randint(1, 2 ** 63)
    rows = []
    iden = tufo[0]
    for p, v in tufo[1].items():
        rows.append((iden, p, v, timestamp))
    return rows

def flatten(iterable):
    return list(itertools.chain.from_iterable(iterable))

def _prepopulate_core(core, rows):
    core.addRows(rows)

def nth(iterable, n):
    "Returns the nth item or a default value"
    return next(itertools.islice(iterable, n, None))

def get_random_keyval(d):
    i = random.randint(0, len(d))
    key = nth(d.keys(), i)
    return (key, d[key])

class TestData:
    def __init__(self, test_data_fn):
        start = now()
        if os.path.isfile(test_data_fn):
            print("Reading test data...")
            self.prepop_rows, self.idens, self.props, self.rows = \
                pickle.load(open(test_data_fn, 'rb'))
        else:
            print("Generating test data...")
            random.seed(4)  # 4 chosen by fair dice roll.  Guaranteed to be random
            forms = [gen_random_form() for x in range(NUM_FORMS)]
            # FIXME:  don't use random.choice!!! Super duper slow
            self.prepop_rows = flatten(_rows_from_tufo(gen_random_tufo(random.choice(forms)))
                                       for x in range(NUM_PREEXISTING_TUFOS))
            tufos = [gen_random_tufo(random.choice(forms)) for x in range(NUM_TUFOS)]
            self.idens = [t[0] for t in tufos]
            self.props = [get_random_keyval(t[1]) for t in tufos]
            random.shuffle(self.idens)
            random.shuffle(self.props)

            self.rows = flatten(_rows_from_tufo(x) for x in tufos)
            pickle.dump((self.prepop_rows, self.idens, self.props, self.rows),
                        open(test_data_fn, 'wb'))

        print("Test data generation took: %.2f" % (now() - start))
        print('addRows: # Tufos:%8d, # Rows: %8d' % (NUM_TUFOS, len(self.rows)))
        print('len count: small:%d, medium:%d, large:%d, huge:%d' %
              (small_count, medium_count, large_count, huge_count))

def _run_x(func, data, num_threads, *args, **kwargs):
    chunk_size = ceil(len(data) / num_threads)
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    threads = [threading.Thread(target=func, args=[chunks[x]] + list(args), kwargs=kwargs)
               for x in range(num_threads)]
    for i in range(num_threads):
        threads[i].start()
    for i in range(num_threads):
        threads[i].join()

def do_it(cmd, data_str, num_threads, globals, number, repeat, divisor):
    if num_threads == 1:
        times = timeit.repeat('%s(%s, core)' % (cmd, data_str), globals=globals, number=number, repeat=repeat)
    else:
        times = timeit.repeat('_run_x(%s, %s, %s, core=core)' % (cmd, data_str, num_threads), globals=globals,
                              number=number, repeat=repeat)
    print_time(cmd, times, divisor)

def profile_it(cmd, globals, number, repeat, divisor):
    cProfile.runctx(cmd, globals, {}, filename='lmdb_02.prof')

def benchmark_cortex(test_data, url, cleanup_func, num_threads=1):
    core = s_cortex.openurl(url)
    _prepopulate_core(core, test_data.prepop_rows)
    g = {'_addRows': _addRows, '_getTufosByIdens': _getTufosByIdens, 'core': core,
         'test_data': test_data, '_getTufoByPropVal': _getTufoByPropVal, '_run_x': _run_x}
    do_it('_addRows', 'test_data.rows', num_threads, g, 1, 1, len(test_data.rows))
    if cleanup_func:
        del core
        core = s_cortex.openurl(url)
        g['core'] = core
    do_it('_getTufosByIdens', 'test_data.idens', num_threads, g, 2, 5, NUM_TUFOS)
    do_it('_getTufoByPropVal', 'test_data.props', num_threads, g, 2, 5, NUM_TUFOS)

    if cleanup_func:
        cleanup_func()

def print_time(label, times, divisor):
    t = min(times)
    print('%50s:   %8.2f (max=%7.2f) %7d %10.6f' % (label, t, max(times), divisor, t / divisor))

LMDB_FILE = 'test.lmdb'
SQLITE_FILE = 'test.sqlite'

def cleanup_lmdb():
    try:
        os.remove(LMDB_FILE)
        os.remove(LMDB_FILE + '-lock')
    except OSError:
        pass

def cleanup_sqlite():
    try:
        os.remove('test.sqlite')
    except OSError:
        pass

def benchmark_all(which_runs, num_threads):
    runs = (
        ('ram://', None),
        ('sqlite:///:memory:', None),
        ('sqlite:///' + SQLITE_FILE, cleanup_sqlite),
        ('lmdb:///%s?lmdb:mapsize=536870912&lmdb:mapslack=536870912' % LMDB_FILE, cleanup_lmdb)
    )

    test_data = TestData('testdata')
    for i, (url, cleanup_func) in enumerate(runs):
        if i not in which_runs:
            continue
        print('%s-threaded benchmarking: %s' % (num_threads, url))
        benchmark_cortex(test_data, url, cleanup_func, num_threads)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('which_runs', type=int, nargs='*', default=(0, 1, 2, 3))
    parser.add_argument('--num-threads', type=int, default=1)
    opts = parser.parse_args()
    benchmark_all(opts.which_runs, opts.num_threads)
