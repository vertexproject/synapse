import random
import os
import synapse.cortex as s_cortex
from time import perf_counter as now
import itertools


NUM_PREEXISTING_TUFOS = 10000

NUM_TUFOS = 100000
NUM_ONE_AT_A_TIME_TUFOS = NUM_TUFOS // 1000

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


def addRows_bench(core, rows, one_at_a_time=False, num_threads=1):
    if one_at_a_time:
        for row in rows:
            core.addRows([row])
    else:
        core.addRows(rows)


def random_normal(avg):
    ''' Returns a number with normal distribution around avg, the very fast way '''
    return random.randint(1, avg-1) + random.randint(0, avg)


def random_string(avg):
    num_letters = random_normal(avg)
    return ''.join(chr(random.randint(ord('a'), ord('a')+25)) for x in range(num_letters))


def random_val_len():
    x = random.random()
    prob = SMALL_VAL_RATE
    if x < prob:
        return SMALL_VAL_BYTES
    prob += MEDIUM_VAL_RATE
    if x < prob:
        return MEDIUM_VAL_BYTES
    prob += LARGE_VAL_RATE
    if x < prob:
        return LARGE_VAL_BYTES
    return HUGE_VAL_BYTES


def gen_random_tufo():
    iden = '%032x' % random.randint(0, 2**128)
    num_props = random_normal(AVG_PROPS_PER_TUFO)
    props = {}
    for p in range(num_props):
        if random.random() <= INTEGER_VAL_RATE:
            val = random.randint(-2 ** 62, 2 ** 63)
        else:
            val = random_string(random_val_len())
        props[random_string(AVG_PROP_NAME_LEN)] = val
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


class TestData:
    def __init__(self):
        print("Generating test data...")
        random.seed(4)  # 4 chosen by fair dice roll.  Guaranteed to be random
        start = now()
        self.prepop_rows = flatten(_rows_from_tufo(gen_random_tufo())
                                   for x in range(NUM_PREEXISTING_TUFOS))
        self.rows = flatten(_rows_from_tufo(gen_random_tufo()) for x in range(NUM_TUFOS))
        self.onerows = flatten(_rows_from_tufo(gen_random_tufo())
                               for x in range(NUM_ONE_AT_A_TIME_TUFOS))
        print("Test data generation took: %.2f" % (now() - start))
        print('addRows: # Tufos:%8d, # Rows: %8d' % (NUM_TUFOS, len(self.rows)))
        print('one at : # Tufos:%8d, # Rows: %8d' % (NUM_ONE_AT_A_TIME_TUFOS, len(self.onerows)))


def benchmark_cortex(test_data, url, cleanup_func, is_ephemeral):
    core = s_cortex.openurl(url)
    _prepopulate_core(core, test_data.prepop_rows)
    times = []
    times.append(('start', now(), 1))
    if not is_ephemeral:
        del core
        core = s_cortex.openurl(url)
        times.append(('openurl preexisting', now(), 1))

    addRows_bench(core, test_data.rows)
    times.append(('addRows', now(), NUM_TUFOS))
    addRows_bench(core, test_data.onerows, one_at_a_time=True)
    times.append(('addRows one at a time', now(), NUM_ONE_AT_A_TIME_TUFOS))

    if cleanup_func is not None:
        cleanup_func()
    display_times(times)


def display_times(times):
    prev = times[0][1]
    for desc, t, divisor in times[1:]:
        print('%30s:   %8.1f %7d %10.6f' % (desc, t - prev, divisor, (t-prev)/divisor))
        prev = t


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


def benchmark_all():
    urls = ('ram://', 'sqlite:///:memory:', 'sqlite:///' + SQLITE_FILE, 'lmdb:///' + LMDB_FILE)
    cleanup = (None, None, cleanup_sqlite, cleanup_lmdb)
    is_ephemeral = (True, True, False, False)
    test_data = TestData()
    for url, cleanup_func, is_ephem in zip(urls, cleanup, is_ephemeral):
        print('Benchmarking ', url)
        benchmark_cortex(test_data, url, cleanup_func, is_ephem)

if __name__ == '__main__':
    benchmark_all()
