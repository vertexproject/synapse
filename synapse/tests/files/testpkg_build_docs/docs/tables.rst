:orphan:

Tables
======

Exercises the ``_pandoc_filter`` table rewrite path. The filter walks every
``Table`` node in the AST and replaces it with a ``RawBlock`` markdown that
emits a tight pipe-table preserving code spans, bold runs, literal pipes,
anonymous hyperlinks, and the array-suffix link decoration.

+-------------+-----------------------+----------+---------+-------------------------------------------+
| Property    | Type                  | Required | Default | Description                               |
+=============+=======================+==========+=========+===========================================+
| ``name``    | ``string``            | **-**    |         | The name.                                 |
+-------------+-----------------------+----------+---------+-------------------------------------------+
| ``mode``    | ``a`` | ``b`` | ``c`` |          | ``a``   | One of ``a``, ``b`` or ``c``.             |
+-------------+-----------------------+----------+---------+-------------------------------------------+
| ``target``  | `Foo <#foo>`__        |          |         | See `Foo <#foo>`__ for details.           |
+-------------+-----------------------+----------+---------+-------------------------------------------+
| ``targets`` | `Foo <#foo>`__\ \[\]  |          |         | An array of `Foo <#foo>`__\ \[\] entries. |
+-------------+-----------------------+----------+---------+-------------------------------------------+
