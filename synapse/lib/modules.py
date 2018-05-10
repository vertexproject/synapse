'''
Module which implements the synapse module API/convention.
'''
import logging

import synapse.exc as s_exc
import synapse.dyndeps as s_dyndeps

coremods = (
    'synapse.models.dns.DnsModule',
    'synapse.models.orgs.OuModule',
    'synapse.models.syn.SynModule',
    'synapse.models.base.BaseModule',
    'synapse.models.person.PsModule',
    'synapse.models.files.FileModule',
    'synapse.models.geospace.GeoModule',
    'synapse.models.geopol.PolModule',
    'synapse.models.telco.TelcoModule',
    'synapse.models.inet.InetModule',
    'synapse.models.material.MatModule',
    'synapse.models.language.LangModule',
    'synapse.models.crypto.CryptoModule',
    'synapse.models.gov.cn.GovCnModule',
    'synapse.models.gov.us.GovUsModule',
    'synapse.models.gov.intl.GovIntlModule',
)
