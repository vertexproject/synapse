'''
The synapse distributed key-value hypergraph analysis framework.
'''
import os
import sys
import msgpack
import tornado
import logging
import multiprocessing

logger = logging.getLogger(__name__)

if (sys.version_info.major, sys.version_info.minor) < (3, 4):  # pragma: no cover
    raise Exception('synapse is not supported on Python versions < 3.4')

if msgpack.version < (0, 5, 0):  # pragma: no cover
    raise Exception('synapse requires msgpack >= 0.5.0')

if tornado.version_info < (3, 2, 2):  # pragma: no cover
    raise Exception('synapse requires tornado >= 3.2.2')

from synapse.lib.version import version, verstring

# load all the synapse builtin modules
# the built-in cortex modules...
BASE_MODULES = (
    ('synapse.models.syn.SynMod', {}),
    ('synapse.models.dns.DnsMod', {}),
    ('synapse.models.orgs.OuMod', {}),
    ('synapse.models.base.BaseMod', {}),
    ('synapse.models.inet.InetMod', {}),
    ('synapse.models.mime.MimeMod', {}),
    ('synapse.models.person.PsMod', {}),
    ('synapse.models.telco.TelMod', {}),
    ('synapse.models.files.FileMod', {}),
    ('synapse.models.geopol.PolMod', {}),
    ('synapse.models.biology.BioMod', {}),
    ('synapse.models.finance.FinMod', {}),
    ('synapse.models.infotech.ItMod', {}),
    ('synapse.models.media.MediaMod', {}),
    ('synapse.models.money.MoneyMod', {}),
    ('synapse.models.science.SciMod', {}),
    ('synapse.models.geospace.GeoMod', {}),
    ('synapse.models.gov.cn.GovCnMod', {}),
    ('synapse.models.gov.us.GovUsMod', {}),
    ('synapse.models.material.MatMod', {}),
    ('synapse.models.crypto.CryptoMod', {}),
    ('synapse.models.language.LangMod', {}),
    ('synapse.models.temporal.TimeMod', {}),
    ('synapse.models.chemistry.ChemMod', {}),
    ('synapse.models.gov.intl.GovIntlMod', {}),
)

##############################################
# setup glob here to avoid import loops...
import synapse.glob as s_glob
import synapse.lib.net as s_net
import synapse.lib.sched as s_sched
import synapse.lib.threads as s_threads

tmax = multiprocessing.cpu_count() * 8

s_glob.plex = s_net.Plex()
s_glob.pool = s_threads.Pool(maxsize=tmax)
s_glob.sched = s_sched.Sched(pool=s_glob.pool)
##############################################

import synapse.lib.modules as s_modules
for mod, conf in BASE_MODULES:
    s_modules.load_ctor(mod, conf)

# Register any CoreModules from envars
mods = os.getenv('SYN_CORE_MODULES')
if mods:
    for name in mods.split(','):
        name = name.strip()
        try:
            s_modules.load_ctor(name, {})
        except Exception as e:
            logger.warning('SYN_CORE_MODULES failed: %s (%s)' % (name, e))

# Register any synapse modules from envars
mods = os.getenv('SYN_MODULES')
if mods:
    for name in mods.split(','):
        name = name.strip()
        try:
            s_modules.load(name)
        except Exception as e:
            logger.warning('SYN_MODULES failed: %s (%s)' % (name, e))

# Rebuild the datamodel's typelib now that we have loaded
# builtin and envar modules.
import synapse.datamodel as s_datamodel
s_datamodel.rebuildTlib()

# load any modules which register dyndeps aliases...
import synapse.cortex
