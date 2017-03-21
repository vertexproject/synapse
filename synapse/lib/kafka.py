
import contextlib
import json
import logging
import threading

import synapse.eventbus

logger = logging.getLogger(__name__)


class EventBus(synapse.eventbus.EventBus):
    """
    A persistent event bus backed by an Apache Kafka topic.

    https://kafka.apache.org
    """

    def __init__(self, topic, **configs):
        """
        See kafka-python documentation for configuration.

        http://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html
        http://kafka-python.readthedocs.io/en/master/apidoc/KafkaProducer.html
        """
        super().__init__()

        from kafka import KafkaProducer
        self.consumer = EventConsumer(super().dist, topic, **configs)
        self.producer = KafkaProducer(**{k: v for k, v in configs.items()
                                         if k in KafkaProducer.DEFAULT_CONFIG})
        self.topic = topic

        self.onfini(self.consumer.stop)
        self.consumer.start()

    def dist(self, event):
        """
        Distribute an event tuple.

        This only sends the event to the topic. Matching event handlers will
        fire asynchronously when the event is consumed from the topic.
        """
        value = json.dumps(event).encode('utf-8')
        self.producer.send(self.topic, value=value)


class EventConsumer(threading.Thread):

    def __init__(self, handler, topic, **configs):
        """
        Constructor

        handler - lambda event: pass
        topic - str

        See kafka-python documentation for configuration.

        http://kafka-python.readthedocs.io/en/master/apidoc/KafkaConsumer.html
        """
        from kafka import KafkaConsumer
        super().__init__()
        self.configs = {k: v for k, v in configs.items()
                        if k in KafkaConsumer.DEFAULT_CONFIG}
        self.daemon = True
        self.handler = handler
        self.stopped = threading.Event()
        self.topic = topic

    def run(self):
        """
        Consume messages from Kafka until the thread is stopped.
        """
        from kafka import KafkaConsumer
        while not self.stopped.is_set():
            try:
                consumer = KafkaConsumer(self.topic, **self.configs)
                logger.debug('consuming from kafka topic %s' % (self.topic))
                with contextlib.closing(consumer) as consumer:
                    for message in consumer:
                        event = json.loads(message.value.decode('utf-8'))
                        self.handler(event)
                        if self.stopped.is_set():
                            break
            except Exception as e:
                logger.exception(e)

    def stop(self):
        """
        Stop consuming messages from Kafka.
        """
        self.stopped.set()
