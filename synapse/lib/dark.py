import synapse.common as s_common
'''
Tools to help implement dark rows
'''

def genDarkRows(iden, name, valus):
    '''
    Generate dark rows in bulk for a given set of values.

    This can be used generate rows in order to do bulk insertion of rows into
    a Cortex without the overhead of continually going through the
    addTufoDark() API.

    Args:
        iden (str): Iden to reverse.
        name (str): Dark row name.
        valus : Iterator to generate values to make in the rows. May be any
                data type which may stored in a Cortex.

    Example:
        Example use with a core::

            rows = list(genDarkRows('1234', 'hidden', ['garden', 'server', 'clown])
            core.addRows(rows)

    Yields:
        tuple: A cortex row, containing a iden, prop, value and timestamp.
    '''
    dark = iden[::-1]
    dark_name = '_:dark:%s' % name
    _now = s_common.now()
    for valu in valus:
        yield (dark, dark_name, valu, _now)
