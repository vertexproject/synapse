import re

import synapse.data as s_data
import synapse.cortex as s_cortex
import synapse.lib.datfile as s_datfile

from synapse.common import *

tldlist = list(s_data.get('iana.tlds'))

tldlist.sort(key=lambda x: len(x))
tldlist.reverse()

tldcat = '|'.join(tldlist)
fqdn_re = r'((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))' % tldcat

scrape_types = [
    ('hash:md5',    r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{32})(?:[^A-Za-z0-9]|$))',{}),
    ('hash:sha1',   r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{40})(?:[^A-Za-z0-9]|$))',{}),
    ('hash:sha256', r'(?=(?:[^A-Za-z0-9]|^)([A-Fa-f0-9]{64})(?:[^A-Za-z0-9]|$))',{}),

    ('inet:url',    r'\w+://[^ \'"\t\n\r\f\v]+',{}),
    ('inet:ipv4',   r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)',{}),
    ('inet:tcp4',   r'((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):[0-9]{1,5})',{}),
    ('inet:fqdn',   r'(?:[^a-z0-9_.-]|^)((?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|$)' % tldcat, {}),
    ('inet:email',  r'(?:[^a-z0-9_.+-]|^)([a-z0-9_\.\-+]{1,256}@(?:[a-z0-9_-]{1,63}\.){1,10}(?:%s))(?:[^a-z0-9_.-]|$)' % tldcat, {} ),
]

regexes = { name:re.compile(rule,re.IGNORECASE) for (name,rule,opts) in scrape_types }

def scrape(text, data=None):
    '''
    Scrape types from a blob of text and return an ingest compatible dict.
    '''
    if data == None:
        data = {}

    for ptype,rule,info in scrape_types:
        regx = regexes.get(ptype)
        for valu in regx.findall(text):
            yield (ptype,valu)

def getsync(text, tags=()):

    ret = []

    core = s_cortex.openurl('ram://')
    with s_cortex.openurl('ram://'):

        core.setConfOpt('enforce',1)
        core.on('core:sync', ret.append)

        for form,valu in scrape(text):
            tufo = core.formTufoByFrob(form,valu)
            for tag in tags:
                core.addTufoTag(tufo,tag)

    return ret

if __name__ == '__main__':

    import sys

    data = {}

    for path in sys.argv[1:]:
        byts = reqbytes(path)
        text = byts.decode('utf8')
        data = scrape(text,data=data)

    #FIXME options for taging all / tagging forms / form props

    print( json.dumps( {'format':'syn','data':data} ) )
#
    #print( repr( data ) )

#def scanForEmailAddresses(txt):
    #return [ m[0] for m in email_regex.findall(txt) ]
