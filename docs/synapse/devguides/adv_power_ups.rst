.. toctree::
    :titlesonly:

.. _dev_adv_power_ups:

Advanced Power-Up Development
#############################

An Advanced Power-Up is standalone application that extends the capabilities of the Cortex
by implementing a Storm Service (see :ref:`gloss-service`).
One common use case for creating an Advanced Power-Up is to add a Storm command that will run custom Python
to parse a file, translate the results into the Synapse datamodel, and then ingest them into the hypergraph.

In order to leverage core functionalities it is recommended that Storm services are created as Cell implementations.
For additional details see the `advanced-power-example repository`_, which contains an example that can be used
as a reference for building an Advanced Power-Up.

.. _advanced-power-example repository: https://github.com/vertexproject/advanced-powerup-example
