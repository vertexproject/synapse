
import contextlib
import json
import logging

import synapse.common as s_common
import synapse.eventbus as s_eventbus

logger = logging.getLogger(__name__)


class EventBus(s_eventbus.EventBus):
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
        self.configs = configs
        self.producer = KafkaProducer(**{k: v for k, v in configs.items()
                                         if k in KafkaProducer.DEFAULT_CONFIG})
        self.topic = topic
        self._consumer = self._consume()
        self.onfini(self._consumer.join)

    def dist(self, event):
        """
        Distribute an event tuple.

        This only sends the event to the topic. Matching event handlers will
        fire asynchronously when the event is consumed from the topic.
        """
        value = json.dumps(event).encode('utf-8')
        self.producer.send(self.topic, value=value)

    @s_common.firethread
    def _consume(self):
        """
        Consume messages from Kafka until the thread is stopped.
        """
        from kafka import KafkaConsumer
        while not self.isfini:
            try:
                consumer = KafkaConsumer(self.topic, **{k: v for k, v in self.configs.items()
                                                        if k in KafkaConsumer.DEFAULT_CONFIG})
                with contextlib.closing(consumer) as consumer:
                    for message in consumer:
                        event = json.loads(message.value.decode('utf-8'))
                        super().dist(event)
                        if self.isfini:
                            break
            except Exception as e:
                logger.exception(e)
