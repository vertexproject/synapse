import sys
import json

import packaging.version as p_version
import packaging.specifiers as p_specifiers

PANDOC_API_REQVERS = '>=1.23.0,<1.24.0'

def walk(elem):
    '''
    Walk the pandoc AST, yielding (type, content) tuples.
    Ref: https://pandoc.org/using-the-pandoc-api.html#walking-the-ast
    '''

    if isinstance(elem, list):
        for subelem in elem:
            yield from walk(subelem)
        return

    if isinstance(elem, dict):
        if 't' in elem:
            yield elem['t'], elem.get('c')
        for v in elem.values():
            yield from walk(v)
        return

def main():
    '''
    A pandoc filter reads the intermediate JSON-formatted AST generated from the source, makes any modifications,
    and then writes the JSON-formatted AST to be used to generate the target.

    Ref: https://pandoc.org/filters.html

    Usage:

       pandoc -f rst -t markdown --filter ./synapse/tools/pkg/pandoc_filter.py -o foo.md foo.rst
    '''

    ast = json.load(sys.stdin)

    spec = p_specifiers.SpecifierSet(PANDOC_API_REQVERS)
    vers = p_version.Version('.'.join(str(part) for part in ast['pandoc-api-version']))
    if vers not in spec:
        raise Exception(f'Pandoc API version {vers} does not match required version {PANDOC_API_REQVERS}')

    for type_, content in walk(ast['blocks']):

        if type_ != 'DefinitionList':
            continue

        # An RST term with multiple definitions gets combined into one -> split
        # ( Only Para types should get split )
        for term, defs in content:

            newdefs = []
            newdef = []

            for def_ in defs[0]:

                if def_['t'] == 'Para' and newdef:
                    # we are on a new paragraph so save the
                    # previous term/def group
                    newdefs.append(newdef.copy())
                    newdef.clear()

                newdef.append(def_)

            if newdef:
                newdefs.append(newdef.copy())

            defs.clear()
            defs.extend(newdefs)

    sys.stdout.write(json.dumps(ast))

    return 0

if __name__ == '__main__':
    sys.exit(main())
