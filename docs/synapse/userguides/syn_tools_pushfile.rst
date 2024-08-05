.. highlight:: none

.. _syn-tools-pushfile:

pushfile
========

The Synapse ``pushfile`` command can be used to upload files to a storage Axon (see Axon in the :ref:`devopsguide`) and optionally create an associated :ref:`type-file` node in a Cortex.

Large-scale file ingest / upload is best performed using an automated feed / module / API. However, ``pushfile`` can be useful for uploading one-off files.

Syntax
------

``pushfile`` is executed from an operating system command shell. The command usage is as follows:

::
  
  usage: synapse.tools.pushfile [-h] -a AXON [-c CORTEX] [-r] [-t TAGS] filenames [filenames ...]

Where:

- ``AXON`` is the telepath URL to a storage Axon.

- ``CORTEX`` is the optional path to a Cortex where a corresponding ``file:bytes`` node should be created.

  - **Note:** while this is an optional parameter, it doesn’t make much sense to store a file in an Axon that can’t be referenced from within a Cortex.

- ``TAGS`` is an optional list of tags to be applied to the ``file:bytes`` node created in the Cortex.

  - ``-t`` takes a comma separated list of tags.
  - The tag should be specified by name only (i.e., without the ``#`` character).
  
- ``-r`` recursively finds all files when a glob pattern is used for a file name.

- ``filenames`` is one or more names (with optional paths), or glob patterns, to the local file(s) to be uploaded.

  - If multiple file names are specified, any tag provided with the ``-t`` option will be added to **each** uploaded file.

Example
-------

Upload the file ``myreport.pdf`` to the specified Axon, create a ``file:bytes`` node in the specified Cortex, and tag the ``file:bytes`` node with the tag ``#sometag`` (replace the Axon and Cortex path below with the path to your Cortex. Note that the command is wrapped for readability):

::
  
  python -m synapse.tools.pushfile -a aha://axon... -c aha://cortex... -t sometag /home/user/reports/myreport.pdf
  
Executing the command will result in various status messages (lines are wrapped for readability):

::
  
  2019-07-03 11:46:30,567 [INFO] log level set to DEBUG
    [common.py:setlogging:MainThread:MainProcess]
  2019-07-03 11:46:30,568 [DEBUG] Using selector: EpollSelector 
    [selector_events.py:__init__:MainThread:MainProcess]
  
  adding tags: ['sometag']
  Uploaded [myreport.pdf] to axon
  file: myreport.pdf (2606351) added to core
    (sha256:229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0) as myreport.pdf

- ``adding tags: ['sometag']`` indicates the tag ``#sometag`` was applied to the ``file:bytes`` node.
- ``Uploaded [myreport.pdf] to axon`` indicates the file was successfully uploaded to the storage Axon.
- ``file: myreport.pdf (2606351) added to core (sha256:229cdde4...5cd40ab0) as myreport.pdf`` indicates the ``file:bytes`` node was created in the Cortex.

  - The message gives the new node’s primary property value (``sha256:229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0``) and also notes the ``:name`` secondary property value assigned to the node (``myreport.pdf``).
  - ``pushfile`` sets the ``file:bytes:name`` property to the base name of the local file being uploaded.

If a given file already exists in the Axon (deconflicted based on the file’s SHA256 hash), ``pushfile`` will not re-upload the file. However, the command will still process any other options, including:

- creating the ``file:bytes`` node in the Cortex if it does not already exist.
- applying any specified tag.
- setting (or overwriting) the ``:name`` property on any existing ``file:bytes`` node with the base name of the local file specified.

For example (lines wrapped for readability):

::
  
  python -m synapse.tools.pushfile -a aha://axon...
    -c aha://cortex... -t anothertag,athirdtag
      /home/user/reports/anotherreport.pdf
  
  2019-07-03 11:59:03,366 [INFO] log level set to DEBUG
    [common.py:setlogging:MainThread:MainProcess]
  2019-07-03 11:59:03,367 [DEBUG] Using selector: EpollSelector
    [selector_events.py:__init__:MainThread:MainProcess]
  
  adding tags: ['anothertag'. 'athirdtag']
  Axon already had [anotherreport.pdf]
  file: anotherreport.pdf (2606351) added to core
    (sha256:229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0)
      as anotherreport.pdf

Note the status indicating the Axon already had the specified file. Similarly, the status noting the ``file:bytes`` node was added to the Cortex lists the same SHA256 hash as our first upload (i.e., ``anotherreport.pdf`` has the same SHA256 hash as ``myreport.pdf``) and indicates the ``:name`` property has been updated (as ``anotherreport.pdf``).

The ``file:bytes`` node for the uploaded report can now be viewed in the specified Cortex by lifting (see :ref:`storm-ref-lift`) the file using the SHA256 / primary property value from the ``pushfile`` status output:

::
  
  file:bytes=sha256:229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0
  
  file:bytes=sha256:229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0
      .created = 2019/07/03 18:46:40.542
      :md5 = 23a14d3a4508628e7e09a4c4868dfb17
      :mime = ??
      :name = anotherrepport.pdf
      :sha1 = 99b6b984988581cae681f65b92198ed77609bd11
      :sha256 = 229cdde419ba9549023de39c6a0ca8af74b45fade2d7a22cdc4105a75cd40ab0
      :size = 2606351
      #anothertag
      #athirdtag
      #sometag
  complete. 1 nodes in 3 ms (333/sec).

Viewing the node’s properties, we see that Synapse has set the ``:name`` property and has calculated and set the MD5, SHA1, and SHA256 hash secondary property values, as well as the file’s size in bytes. Similarly the two tags from our two example ``pushfile`` commands have been added to the node.

Alternatively, a glob pattern could be used to upload all PDF files in a given directory:

::

  python -m synapse.tools.pushfile -a aha://axon...
    -c aha://cortex... -t anothertag,athirdtag
      /home/user/reports/*.pdf
 
