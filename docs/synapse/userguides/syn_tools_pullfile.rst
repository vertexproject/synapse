.. highlight:: none

.. _syn-tools-pullfile:

pullfile
========

The Synapse ``pullfile`` command can be used to retrieve (download) one or more files from a storage Axon (see Axon in the :ref:`devopsguide`).

Syntax
------

``pullfile`` is executed from an operating system command shell. The command usage is as follows:

::
  
  usage: synapse.tools.pullfile [-h] -a AXON [-o OUTPUT] [-l HASHES]


Where:

- ``AXON`` is the telepath URL to a storage Axon.

- ``OUTPUT`` is the optional directory path where the downloaded file(s) should be written.

  - If no option is specified, the file(s) will be written to the current working directory.
  - It is not possible to specify multiple ``-o`` options with a single ``pullfile`` command (i.e., a different ``-o`` option with each ``-l HASH``, for example). If multiple ``-o`` options are specified, the last ``OUTPUT`` path specified will be used.
  - Files saved locally are named using their SHA256 hash value.

- ``HASHES`` is the SHA256 hash(es) of the file(s) to be retrieved.

  - Multiple hashes can be specified, but each must be listed with its own ``-l`` option (i.e., ``-l HASH_0 -l HASH_1 ... -l HASH_n``).

Example
-------

Download the two files with the specified SHA256 hashes from the specified Axon to the local ``/home/user/Documents`` directory (replace the Axon path below with the path to your Axon. Note that the command is wrapped for readability):

::
  
  python -m synapse.tools.pullfile -a aha://axon...
    -o /home/user/Documents
    -l 229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0
    -l 52c672f45adacca4878461c1bdd5800af8518e675819a0bdcd5c64a72075a478

Executing the command will result in various status messages showing the query and successful retrieval of the file(s):

::
  
  Fetching 229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0 to file
  Fetched 229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0 to file
  Fetching 52c672f45adacca4878461c1bdd5800af8518e675819a0bdcd5c64a72075a478 to file
  Fetched 52c672f45adacca4878461c1bdd5800af8518e675819a0bdcd5c64a72075a478 to file

