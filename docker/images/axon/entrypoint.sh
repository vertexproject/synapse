#!/bin/bash
python -O -m synapse.servers.axon /vertex/storage

HEALTHCHECK --start-period=10s --retries=1 --timeout=10s --interval=30s CMD python -m synapse.tools.healthcheck -c cell:///vertex/storage/