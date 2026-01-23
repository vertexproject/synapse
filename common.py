'''
Common utility functions for for_lexicon.
'''
import for_lexicon.exc as s_exc

def flatten(item):
    '''
    Normalize a primitive object for cryptographic signing.

    Args:
        item: The python primitive object to normalize.

    Notes:
        Only None, bool, int, bytes, strings, floats, lists, tuples and dictionaries are acceptable input.
        List objects will be converted to tuples.
        Dictionary objects must have keys which can be sorted.

    Returns:
        A new copy of the object.
    '''

    if item is None:
        return None

    if isinstance(item, (str, int, bytes, float)):
        return item

    if isinstance(item, (tuple, list)):
        return tuple([flatten(i) for i in item])

    if isinstance(item, dict):
        return {flatten(k): flatten(item[k]) for k in sorted(item.keys())}

    raise s_exc.BadDataValu(mesg=f'Unknown type: {type(item)}')
