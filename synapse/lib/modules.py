'''
Module which implements the synapse module API/convention.
'''
import logging

import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps

coremods = (
    ('synapse.models.syn.SynModule', {}),
    ('synapse.models.base.BaseModule', {}),
    ('synapse.models.files.FileModule', {}),
    ('synapse.models.geospace.GeoModule', {}),
    ('synapse.models.geopol.PolModule', {}),
    ('synapse.models.inet.InetModule', {}),
    ('synapse.models.material.MatModule', {}),
    ('synapse.models.language.LangModule', {}),
    ('synapse.models.crypto.CryptoModule', {}),
    ('synapse.models.gov.cn.GovCnModule', {}),
)
