'''
Module which implements the synapse module API/convention.
'''
import logging

import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps

coremods = (
    ('synapse.models.base.BaseModule', {}),
    ('synapse.models.files.FileModule', {}),
    ('synapse.models.geopol.PolModule', {}),
    ('synapse.models.inet.InetModule', {}),
    ('synapse.models.gov.cn.GovCnModule', {}),
    ('synapse.models.gov.us.GovUsModule', {}),
    ('synapse.models.gov.intl.GovIntlModule', {}),
    ('synapse.models.material.MatModule', {}),
    ('synapse.models.language.LangModule', {}),
    ('synapse.models.crypto.CryptoModule', {}),
)
