'''
The synapse distributed key-value hypergraph analysis framework.
'''
import os
import msgpack
import tornado
import logging

logger = logging.getLogger(__name__)

if msgpack.version < (0,4,2):
    raise Exception('synapse requires msgpack >= 0.4.2')

if tornado.version_info < (3,2,2):
    raise Exception('synapse requires tornado >= 3.2.2')

version = (0,0,19)
verstring = '.'.join([ str(x) for x in version ])

import synapse.lib.modules as s_modules

# load all the synapse builtin modules
# the built-in cortex modules...
BASE_MODELS = (
    ('synapse.models.syn.SynMod', {}),
    ('synapse.models.dns.DnsMod', {}),
    ('synapse.models.orgs.OuMod', {}),
    ('synapse.models.inet.InetMod', {}),
    ('synapse.models.person.PsMod', {}),
    ('synapse.models.telco.TelMod', {}),
    ('synapse.models.files.FileMod', {}),
    ('synapse.models.geopol.PolMod', {}),
    ('synapse.models.biology.BioMod', {}),
    ('synapse.models.finance.FinMod', {}),
    ('synapse.models.infotech.ItMod', {}),
    ('synapse.models.media.MediaMod', {}),
    ('synapse.models.money.MoneyMod', {}),
    ('synapse.models.compsci.CsciMod', {}),
    ('synapse.models.geospace.GeoMod', {}),
    ('synapse.models.gov.cn.GovCnMod', {}),
    ('synapse.models.gov.us.GovUsMod', {}),
    ('synapse.models.material.MatMod', {}),
    ('synapse.models.crypto.CryptoMod', {}),
    ('synapse.models.language.LangMod', {}),
    ('synapse.models.temporal.TimeMod', {}),
    ('synapse.models.chemistry.ChemMod', {}),
    ('synapse.models.science.SciModMod', {}),
    ('synapse.models.gov.intl.GovIntlMod', {}),
)

for mod, conf in BASE_MODELS:
    modpath = mod.rsplit('.', 1)[0]
    s_modules.load(modpath)

# Rebuild the datamodel's typelib now that we have loaded builtin models.
import synapse.datamodel as s_datamodel
s_datamodel.rebuildTlib()

mods = os.getenv('SYN_MODULES')
if mods:
    for name in mods.split(','):
        try:
            s_modules.load(name)
        except Exception as e:
            logger.warning('SYN_MODULES failed: %s (%s)' % (name,e))

# load any modules which register dyndeps aliases...
# ( order matters...)
import synapse.axon
import synapse.cortex
#import synapse.cores.common as s_cores_common

