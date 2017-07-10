
import os
import unittest

import synapse.lib.kafka as s_kafka

from synapse.tests.common import SynTest


class EventBusTest(SynTest):

    def test_eventbus_dist(self):
        topic = os.getenv('SYN_TEST_KAFKA_TOPIC')
        if not topic:
            raise unittest.SkipTest('no SYN_TEST_KAFKA_TOPIC')

        ebus = s_kafka.EventBus(topic, batch_size=0, group_id='syntest')

        def handler(event):
            self.assertEqual(event[0], 'foo')
            self.assertEqual(event[1], {'bar': 'baz'})
        ebus.on('foo', handler)

        self.seen = False
        waiter = ebus.waiter(1, 'foo')
        ebus.fire('foo', bar='baz')
        events = waiter.wait(timeout=3)
        event = events[0]
        self.assertEqual(event[0], 'foo')
        self.assertEqual(event[1], {'bar': 'baz'})
