Ingest - Parsing JSON
=====================

JSON is a very commonly encountered data format, since it is so portable and easy to use. JSON support is provided via
the built-in `json`_ module. For this, we'll look at a more complicated example - a blob of information about a social
media account for a user at the made up site, ``socialnetwork.ninja``.

The data we want to ingest can be seen below:

.. literalinclude:: ../examples/ingest_structured_nested_data.json
    :language: json

There are several nodes we can create here from this data. First, the site and user can be made into a ``inet:netuser``
form, and we can set some time-based properties there. We have some friendships which are noted, which we'll consider to be
bidirectional relationships, and which we can use the ``inet:follows`` node type to represent. Similarly, the user has some
organizations they are a part of on the site which can be treated as ``inet:netmemb`` nodes. Lastly, there is some post
information from the user which we can use to make ``inet:netpost`` nodes.  We'll look at each of these
separately, then together as a single document.

.. literalinclude:: ../examples/ingest_structured_nested_def.json
    :lines: 11-52

The above definition shows the extraction of a few vars from the json object, using their names as the path. This sets
the variables ``domain``, ``user``, ``account_created`` and ``last_login``.  Those are used to create the
``inet:netuser`` node for the user.

The following sections require the "iter" directive, which is used to iterate over a set of data which is structured
in a object.  This allows us to handle nested data structures in a clean fashion. There is one important concept to
consider when dealing with "iter" directives - variable scope.  When an iter is encounted, the Ingest process enters
into a new scope and the variables set in the parent section are available to the child scopes.  When an iter is
exhausted, it leaves the scope and the variables it set are no longer available.

A simple iter, going over the user's organizations, can be seen below:

.. literalinclude:: ../examples/ingest_structured_nested_def.json
    :lines: 53-74

Since we are iterating over the list of strings, if we want to set that string as a variable we can do so with the path
set to the value ``0`` (not ``"0"`` as in the CSV example). Since we're in a child scope, we still have access the
parent "vars", so we can use those when making the ``inet:netmemb`` nodes.  This is seen in the template string::

    "template": "({{domain}}/{{user}},{{domain}}/{{org}})"

This makes the string form of the ``inet:netmemb`` comp type using the ``org`` var extracted during the current iter,
and the ``domain`` and ``user`` vars from the parent.

Likewise, the ``domain`` and ``user`` are reused again in the iter which is used to make the ``inet:follows`` nodes.

.. literalinclude:: ../examples/ingest_structured_nested_def.json
    :lines: 75-101

In the above example, we're making two ``inet:follows`` nodes for each friend, under the assumption that the friend
relationship of ``socialnetwork.ninja`` is bi-directional. This is important since the ``inet:follows`` node itself
is a one-way relationship (think of a Twitter follow), not a a two-way relationship.

Next, we need to iterate over the dictionary objects containing the users posts.  That is seen below:

.. literalinclude:: ../examples/ingest_structured_nested_def.json
    :lines: 102-133

The big difference in this section is that, unlike the previous two, we are accessing variables like in the
parent scope (using key names). We then create the ``inet:netpost`` in a similar manner to other sections, in order to
make those nodes.

Putting this all together gives us the following ingest document:

.. literalinclude:: ../examples/ingest_structured_nested_def.json
    :language: json

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/examples/ingest_structured_nested_def.json

After ingesting this, we can see the various nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser:site=socialnetwork.ninja
    inet:netuser = socialnetwork.ninja/alicethefriend
    inet:netuser = socialnetwork.ninja/bobtheuser
    inet:netuser = socialnetwork.ninja/mallorythespy
    (3 results)
    cli> ask --props inet:netuser=socialnetwork.ninja/bobtheuser inet:netuser->inet:follows:follower show:cols(inet:follows:follower, inet:follows:followee)
    socialnetwork.ninja/bobtheuser  socialnetwork.ninja/mallorythespy
    socialnetwork.ninja/bobtheuser socialnetwork.ninja/alicethefriend
    (2 results)
    cli> ask --props inet:netuser=socialnetwork.ninja/bobtheuser inet:netuser->inet:netpost:netuser
    inet:netpost = 0e89cf5db1fd8c426daa8b01e58cd2dd
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = hallo!
        :time = 2017/05/02 01:06:03.000
    inet:netpost = 16a550ca28e7e62e0b47b482cc02b58e
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = Just got back from the concert
     had a great time
        :time = 2017/08/17 01:02:03.000
    inet:netpost = e6b5d03f398a02548d9201efbdc58a06
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = Just did hax with nine bit bytes @ defcon
        :time = 2017/08/01 02:03:04.000
    (3 results)

When ingesting data in this format, it is common to also apply tags to a ingest definition. This can be useful
for adding additional analytical data or categorization to the nodes as they are created in the Cortex. This can be done
by adding a "tags" directive in line with other ingest directives.  An example of modifying the above ingest to add a
``#src.socialnetwork`` tag can be seen highlighted below:

.. literalinclude:: ../examples/ingest_structured_nested_def2.json
    :language: json
    :emphasize-lines: 11-13

This will add the ``#src.socialnetwork`` tag to all of the nodes created directly by the ingest process. This ingest
can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/examples/ingest_structured_nested_def2.json

Then we can lift nodes from this ingest via tags. The following example shows lifting all of the ``inet:netuser`` nodes
made with this ingest::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser*tag=src.socialnetwork
    inet:netuser = socialnetwork.ninja/bobtheuser
        #src.socialnetwork (added 2017/08/17 23:53:30.024)
    (1 results)

This result may seem odd - in the previous query ``ask inet:netuser:site=socialnetwork.ninja`` we had three
``inet:netuser`` accounts found; but ``ask inet:netuser*tag=src.socialnetwork`` only gave us one account. This is
because we only created one ``inet:netuser`` account directly in the ingest definition, the other accounts were created
as a result of creating the ``inet:netfollows`` nodes. If we wanted to be thorough, we could also create the
``inet:netuser`` accounts as well. See the highlighted section of the updated ingest below:

.. literalinclude:: ../examples/ingest_structured_nested_def3.json
    :language: json
    :emphasize-lines: 82-87

This updated ingest will make the ``inet:netuser`` nodes for the friends and tag them prior to making the
``inet:netfollows`` nodes.  It can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/examples/ingest_structured_nested_def3.json

Repeating our earlier Storm query gives us all three ``inet:netuser`` nodes::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser*tag=src.socialnetwork
    inet:netuser = socialnetwork.ninja/alicethefriend
        #src.socialnetwork (added 2017/08/17 23:59:57.797)
    inet:netuser = socialnetwork.ninja/bobtheuser
        #src.socialnetwork (added 2017/08/17 23:53:30.024)
    inet:netuser = socialnetwork.ninja/mallorythespy
        #src.socialnetwork (added 2017/08/17 23:59:57.797)
    (3 results)

.. _`json`: https://docs.python.org/3/library/json.html
