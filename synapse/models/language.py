import regex

import synapse.exc as s_exc
import synapse.lib.types as s_types

# A well-formed IETF BCP-47 (RFC 5646) language tag matcher. This validates the
# structure of a language tag (langtag / privateuse / irregular grandfathered) but
# does not validate subtags against the IANA Language Subtag Registry.
bcp47re = regex.compile(r'''
    ^
    (?:
        (?P<grandfathered>
            en-GB-oed | i-ami | i-bnn | i-default | i-enochian | i-hak | i-klingon |
            i-lux | i-mingo | i-navajo | i-pwn | i-tao | i-tay | i-tsu |
            sgn-BE-FR | sgn-BE-NL | sgn-CH-DE
        )
        |
        (?:
            (?P<language>
                [A-Za-z]{2,3} (?: - [A-Za-z]{3} ){0,3}
                | [A-Za-z]{4,8}
            )
            (?: - (?P<script> [A-Za-z]{4} ) )?
            (?: - (?P<region> [A-Za-z]{2} | [0-9]{3} ) )?
            (?: - (?: [A-Za-z0-9]{5,8} | [0-9][A-Za-z0-9]{3} ) )*
            (?: - (?: [0-9A-WY-Za-wy-z] (?: - [A-Za-z0-9]{2,8} )+ ) )*
            (?: - (?: x (?: - [A-Za-z0-9]{1,8} )+ ) )?
        )
        |
        (?: x (?: - [A-Za-z0-9]{1,8} )+ )
    )
    $
''', regex.VERBOSE | regex.IGNORECASE)

def bcp47recase(parts):
    '''
    Apply BCP-47 (RFC 5646 sec 2.1.1) canonical casing to a list of subtags.

    The first subtag (language) is lowercase, two letter subtags (region) are
    uppercase, four letter subtags (script) are title case, and all other subtags
    are lowercase. Once an extension or private use singleton is reached, the
    remaining subtags are all lowercase.
    '''
    retn = []
    tail = False
    for indx, part in enumerate(parts):

        lowr = part.lower()

        if tail or indx == 0:
            retn.append(lowr)
            continue

        if len(part) == 1:
            retn.append(lowr)
            tail = True
            continue

        if len(part) == 2 and part.isalpha():
            retn.append(lowr.upper())
            continue

        if len(part) == 4 and part.isalpha():
            retn.append(lowr.capitalize())
            continue

        retn.append(lowr)

    return '-'.join(retn)

class LangCode(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.setNormFunc(str, self._normPyStr)

    async def _normPyStr(self, valu, view=None):

        text = str(valu).strip()
        if not text:
            mesg = 'A lang:code must be a non-empty BCP-47 language tag.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        match = bcp47re.match(text)
        if match is None:
            mesg = f'[{valu}] is not a well-formed BCP-47 language tag.'
            raise s_exc.BadTypeValu(name=self.name, valu=valu, mesg=mesg)

        parts = text.split('-')
        norm = bcp47recase(parts)

        info = {}
        subs = {}

        if match.group('language') is not None:
            subs['language'] = (self.strtype.typehash, parts[0].lower(), {})

        if (scpt := match.group('script')) is not None:
            subs['script'] = (self.strtype.typehash, scpt.capitalize(), {})

        if (regn := match.group('region')) is not None:
            subs['region'] = (self.strtype.typehash, regn.upper(), {})

        if subs:
            info['subs'] = subs

        return norm, info

modeldefs = (
    {

        'interfaces': (
            ('lang:transcript', {
                'template': {'title': 'transcript'},
                'props': (

                    ('text', ('text', {}), {
                        'doc': 'The text of the {title}.'}),

                    ('lang', ('lang:language', {}), {
                        'doc': 'The language of the {title}.'}),
                ),
                'doc': 'An interface which applies to forms containing speech.'}),
        ),

        'types': (

            ('lang:phrase', ('text', {}), {
                'props': (),
                'doc': 'A small group of words which stand together as a concept.'}),

            ('lang:code', (None, {'ctor': 'synapse.models.language.LangCode'}), {
                'ex': 'pt-BR',
                'props': (

                    ('language', ('str:lower', {}), {
                        'computed': True,
                        'doc': 'The primary language subtag.'}),

                    ('script', ('str', {}), {
                        'computed': True,
                        'doc': 'The script subtag.'}),

                    ('region', ('str:upper', {}), {
                        'computed': True,
                        'doc': 'The region subtag.'}),
                ),
                'doc': 'An IETF BCP-47 language tag.'}),

            ('lang:idiom', ('guid', {}), {
                'props': (

                    ('desc', ('text', {}), {
                        'doc': 'A description of the meaning and origin of the idiom.'}),

                    ('phrase', ('lang:phrase', {}), {
                        'doc': 'The text of the idiom.'}),
                ),
                'doc': 'An idiomatic use of a phrase.'}),

            ('lang:hashtag', ('title', {'regex': r'^#[^\p{Z}#]+$'}), {
                # regex explanation:
                # - starts with pound
                # - one or more non-whitespace/non-pound character
                # The minimum hashtag is a pound with a single non-whitespace character
                'template': {'title': 'hashtag'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'props': (),
                'doc': 'A hashtag used in written text.'}),

            ('lang:name', ('base:name', {}), {
                'props': (),
                'doc': 'A name used to refer to a language.'}),

            ('lang:translation', ('guid', {}), {
                'props': (

                    ('time', ('time', {}), {
                        'doc': 'The time when the translation was completed.'}),

                    ('input', ('text', {}), {
                        'ex': 'hola',
                        'doc': 'The input text.'}),

                    ('input:lang', ('lang:language', {}), {
                        'doc': 'The input language.'}),

                    ('output', ('text', {}), {
                        'ex': 'hi',
                        'doc': 'The output text.'}),

                    ('output:lang', ('lang:language', {}), {
                        'doc': 'The output language.'}),

                    ('desc', ('text', {}), {
                        'ex': 'A standard greeting',
                        'doc': 'A description of the meaning of the output.'}),

                    ('engine', ('it:software', {}), {
                        'doc': 'The translation engine version used.'}),

                    ('translator', ('entity:actor', {}), {
                        'doc': 'The entity who translated the input.'}),
                ),
                'doc': 'A translation of text from one language to another.'}),

            ('lang:language', ('guid', {}), {
                'interfaces': (
                    ('edu:learnable', {}),
                ),
                'props': (

                    ('code', ('lang:code', {}), {
                        'doc': 'The language code for this language.'}),

                    ('name', ('lang:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the language.'}),

                    ('names', ('array', {'type': 'lang:name'}), {
                        'doc': 'An array of alternative names for the language.'}),
                ),
                'doc': 'A specific written or spoken language.'}),

        ),

    },
)
