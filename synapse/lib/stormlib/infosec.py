import math
import decimal

import synapse.exc as s_exc
import synapse.data as s_data
import synapse.common as s_common

import synapse.lib.chop as s_chop
import synapse.lib.coro as s_coro
import synapse.lib.config as s_config
import synapse.lib.stormtypes as s_stormtypes

import synapse.lookup.cvss as s_cvss


# used as a reference implementation:
# https://www.first.org/cvss/calculator/cvsscalc31.js

CVSS31 = {
  'AV': {'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2},
  'AC': {'H': 0.44, 'L': 0.77},
  'PR': {'U': {'N': 0.85, 'L': 0.62, 'H': 0.27},  # These values are used if Scope is Unchanged
         'C': {'N': 0.85, 'L': 0.68, 'H': 0.5}},  # These values are used if Scope is Changed
  'UI': {'N': 0.85, 'R': 0.62},
  'S': {'U': 6.42, 'C': 7.52},
  'C': {'N': 0, 'L': 0.22, 'H': 0.56},
  'I': {'N': 0, 'L': 0.22, 'H': 0.56},
  'A': {'N': 0, 'L': 0.22, 'H': 0.56},
  'E': {'X': 1, 'U': 0.91, 'P': 0.94, 'F': 0.97, 'H': 1},
  'RL': {'X': 1, 'O': 0.95, 'T': 0.96, 'W': 0.97, 'U': 1},
  'RC': {'X': 1, 'U': 0.92, 'R': 0.96, 'C': 1},
  'CR': {'X': 1, 'L': 0.5, 'M': 1, 'H': 1.5},
  'IR': {'X': 1, 'L': 0.5, 'M': 1, 'H': 1.5},
  'AR': {'X': 1, 'L': 0.5, 'M': 1, 'H': 1.5},
}

vect2prop = {
    'AV': 'cvss:av',
    'AC': 'cvss:ac',
    'PR': 'cvss:pr',
    'UI': 'cvss:ui',
    'S': 'cvss:s',
    'C': 'cvss:c',
    'I': 'cvss:i',
    'A': 'cvss:a',
    'E': 'cvss:e',
    'RL': 'cvss:rl',
    'RC': 'cvss:rc',
    'CR': 'cvss:cr',
    'IR': 'cvss:ir',
    'AR': 'cvss:ar',
    'MS': 'cvss:ms',
    'MC': 'cvss:mc',
    'MI': 'cvss:mi',
    'MA': 'cvss:ma',
    'MAV': 'cvss:mav',
    'MAC': 'cvss:mac',
    'MPR': 'cvss:mpr',
    'MUI': 'cvss:mui',
}

CTX = decimal.Context(rounding=decimal.ROUND_HALF_UP)

def CVSS2_round(x):
    d = decimal.Decimal(str(x))
    return float(d.quantize(decimal.Decimal('0.1'), context=CTX))

def CVSS3_0_round(x):
    '''
    Round up to the nearest one decimal place. From the JS reference implementation:
    https://www.first.org/cvss/calculator/cvsscalc30.js
    '''
    return (math.ceil(x * 10) / 10.0)

def CVSS3_1_round(x):
    '''
    Round up to the nearest one decimal place. From the JS reference implementation:
    https://www.first.org/cvss/calculator/cvsscalc31.js
    '''
    i = int(x * 100000)

    if i % 10000 == 0:
        return i / 100000

    return (math.floor(i / 10000) + 1) / 10.0

CVSS_ROUND = {
    s_cvss.cvss2: CVSS2_round,
    s_cvss.cvss3_0: CVSS3_0_round,
    s_cvss.cvss3_1: CVSS3_1_round,
}

def CVSS_get_coefficients(vdict, vers):
    ret = {}

    metrics = s_cvss.metrics[vers]
    undefined = s_cvss.undefined[vers]

    Scope = None
    ModifiedScope = None

    if vers in (s_cvss.cvss3_0, s_cvss.cvss3_1):
        Scope = vdict['S']

        ModifiedScope = vdict.get('MS', undefined)
        if ModifiedScope == undefined:
            ModifiedScope = Scope

    for metric in metrics:
        # These are special case lookups using the Scope/ModifiedScope value,
        # handle them later
        if metric in ('PR', 'MPR'):
            continue

        val = vdict.get(metric, undefined)
        ret[metric] = metrics[metric][2][val]

    # This block handles the special case lookups in CVSS3.0/CVSS3.1. Specifically:
    #   - The extra Scope/ModifiedScope extra lookup for PR/MPR
    #   - The "modified" values in the environment metrics that (if
    #     present) modify the base metrics.
    if vers in (s_cvss.cvss3_0, s_cvss.cvss3_1):
        PR = vdict.get('PR')
        ret['PR'] = metrics['PR'][2][Scope][PR]

        MPR = vdict.get('MPR', undefined)
        if MPR == undefined:
            ret['MPR'] = ret['PR']
        else:
            ret['MPR'] = metrics['MPR'][2][ModifiedScope][MPR]

        def set_modval(metric, base_metric):
            val = vdict.get(metric, undefined)
            if val == undefined:
                ret[metric] = ret[base_metric]
            else:
                ret[metric] = metrics[metric][2][val]

        set_modval('MAV', 'AV')
        set_modval('MAC', 'AC')
        set_modval('MUI', 'UI')
        set_modval('MC', 'C')
        set_modval('MI', 'I')
        set_modval('MA', 'A')

    return ret

def CVSS2_calc(vdict):
    round = CVSS_ROUND[s_cvss.cvss2]
    undefined = s_cvss.undefined[s_cvss.cvss2]
    coeffs = CVSS_get_coefficients(vdict, s_cvss.cvss2)

    OverallScore = None

    def _base(Impact):
        AccessVector = coeffs['AV']
        AccessComplexity = coeffs['AC']
        Authentication = coeffs['Au']

        Exploitability = 20 * AccessVector * AccessComplexity * Authentication

        fImpact = 1.176
        if Impact == 0:
            fImpact = 0.0

        return ((0.6 * Impact) + (0.4 * Exploitability) - 1.5) * fImpact

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v2/guide#3-2-1-Base-Equation
    ConfImpact = coeffs['C']
    IntegImpact = coeffs['I']
    AvailImpact = coeffs['A']

    Impact = 10.41 * (1 - (1 - ConfImpact) * (1 - IntegImpact) * (1 - AvailImpact))

    BaseScore = round(_base(Impact))
    OverallScore = BaseScore

    # Calculate the temporal score per the equation listed here:
    # https://www.first.org/cvss/v2/guide#3-2-2-Temporal-Equation
    Exploitability = coeffs['E']
    RemediationLevel = coeffs['RL']
    ReportConfidence = coeffs['RC']

    E = vdict.get('E', undefined)
    RL = vdict.get('RL', undefined)
    RC = vdict.get('RC', undefined)

    TemporalMetrics = (E, RL, RC)

    if TemporalMetrics.count(undefined) == len(TemporalMetrics):
        TemporalScore = None
    else:
        TemporalScore = round(BaseScore * Exploitability * RemediationLevel * ReportConfidence)

    '''
    Calculate the environmental score per the equation listed here:
    https://www.first.org/cvss/v2/guide#3-2-3-Environmental-Equation
    '''
    ConfImpact = coeffs['C']
    IntegImpact = coeffs['I']
    AvailImpact = coeffs['A']

    ConfReq = coeffs['CR']
    IntegReq = coeffs['IR']
    AvailReq = coeffs['AR']

    AdjustedImpact = min(
        10.0,
        10.41 * (1.0 - (1.0 - ConfImpact * ConfReq) * (1.0 - IntegImpact * IntegReq) * (1.0 - AvailImpact * AvailReq))
    )

    Exploitability = coeffs['E']
    RemediationLevel = coeffs['RL']
    ReportConfidence = coeffs['RC']

    AdjustedTemporal = _base(AdjustedImpact) * Exploitability * RemediationLevel * ReportConfidence

    CollateralDamagePotential = coeffs['CDP']
    TargetDistribution = coeffs['TD']

    CDP = vdict.get('CDP', undefined)
    TD = vdict.get('TD', undefined)
    CR = vdict.get('CR', undefined)
    IR = vdict.get('IR', undefined)
    AR = vdict.get('AR', undefined)

    EnvironmentalMetrics = (CDP, TD, CR, IR, AR)

    if EnvironmentalMetrics.count(undefined) == len(EnvironmentalMetrics):
        EnvironmentalScore = None
    else:
        EnvironmentalScore = round((AdjustedTemporal + (10 - AdjustedTemporal) * CollateralDamagePotential) * TargetDistribution)

    if TemporalScore:
        OverallScore = TemporalScore

    if EnvironmentalScore:
        OverallScore = EnvironmentalScore

    return BaseScore, TemporalScore, EnvironmentalScore, OverallScore

def _CVSS3_calc(vdict, vers):

    round = CVSS_ROUND[vers]
    undefined = s_cvss.undefined[vers]
    coeffs = CVSS_get_coefficients(vdict, vers)

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-1-Base-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.
    _Scope = vdict['S']

    _ModifiedScope = vdict.get('MS', undefined)
    if _ModifiedScope == undefined:
        _ModifiedScope = _Scope

    Confidentiality = coeffs['C']
    Integrity = coeffs['I']
    Availability = coeffs['A']

    ISS = 1 - ((1 - Confidentiality) * (1 - Integrity) * (1 - Availability))

    if _Scope == 'U':
        Impact = 6.42 * ISS
    else:
        Impact = 7.52 * (ISS - 0.029) - 3.25 * (ISS - 0.02) ** 15

    AttackVector = coeffs['AV']
    AttackComplexity = coeffs['AC']
    PrivilegesRequired = coeffs['PR']
    UserInteraction = coeffs['UI']

    Exploitability = 8.22 * AttackVector * AttackComplexity * PrivilegesRequired * UserInteraction

    if Impact <= 0:
        BaseScore = 0.0
    else:
        if _Scope == 'U':
            BaseScore = round(min(Impact + Exploitability, 10.0))
        else:
            BaseScore = round(min(1.08 * (Impact + Exploitability), 10.0))

    OverallScore = BaseScore

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-2-Temporal-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.

    E = vdict.get('E', undefined)
    RL = vdict.get('RL', undefined)
    RC = vdict.get('RC', undefined)

    TemporalMetrics = (E, RL, RC)

    if TemporalMetrics.count(undefined) == len(TemporalMetrics):
        TemporalScore = None

    else:
        ExploitCodeMaturity = coeffs['E']
        RemediationLevel = coeffs['RL']
        ReportConfidence = coeffs['RC']

        TemporalScore = round(BaseScore * ExploitCodeMaturity * RemediationLevel * ReportConfidence)

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-3-Environmental-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.

    ConfidentialityRequirement = coeffs['CR']
    ModifiedConfidentiality = coeffs['MC']
    IntegrityRequirement = coeffs['IR']
    ModifiedIntegrity = coeffs['MI']
    AvailabilityRequirement = coeffs['AR']
    ModifiedAvailability = coeffs['MA']

    MISS = min(
        1.0 - ((1.0 - ConfidentialityRequirement * ModifiedConfidentiality) *
                (1.0 - IntegrityRequirement * ModifiedIntegrity) *
                (1.0 - AvailabilityRequirement * ModifiedAvailability)
        ),
        0.915
    )

    if _ModifiedScope == 'U':
        ModifiedImpact = 6.42 * MISS
    else:
        ModifiedImpact = 7.52 * (MISS - 0.029) - 3.25 * (MISS * 0.9731 - 0.02) ** 13

    ModifiedAttackVector = coeffs['MAV']
    ModifiedAttackComplexity = coeffs['MAC']
    ModifiedPrivilegesRequired = coeffs['MPR']
    ModifiedUserInteraction = coeffs['MUI']

    ModifiedExploitability = (
        8.22 *
        ModifiedAttackVector *
        ModifiedAttackComplexity *
        ModifiedPrivilegesRequired *
        ModifiedUserInteraction
    )

    MAV = vdict.get('MAV', undefined)
    MAC = vdict.get('MAC', undefined)
    MPR = vdict.get('MPR', undefined)
    MUI = vdict.get('MUI', undefined)
    MS = vdict.get('MS', undefined)
    MC = vdict.get('MC', undefined)
    MI = vdict.get('MI', undefined)
    MA = vdict.get('MA', undefined)
    CR = vdict.get('CR', undefined)
    IR = vdict.get('IR', undefined)
    AR = vdict.get('AR', undefined)

    EnvironmentalMetrics = (MAV, MAC, MPR, MUI, MS, MC, MI, MA, CR, IR, AR)

    if EnvironmentalMetrics.count(undefined) == len(EnvironmentalMetrics):
        EnvironmentalScore = None

    elif ModifiedImpact <= 0:
        EnvironmentalScore = 0.0

    else:
        ExploitCodeMaturity = coeffs['E']
        RemediationLevel = coeffs['RL']
        ReportConfidence = coeffs['RC']

        if _ModifiedScope == 'U':
            EnvironmentalScore = round(
                round(
                    min(ModifiedImpact + ModifiedExploitability, 10)) *
                ExploitCodeMaturity *
                RemediationLevel *
                ReportConfidence
            )

        else:
            EnvironmentalScore = round(
                round(
                    min(1.08 * (ModifiedImpact + ModifiedExploitability), 10)) *
                ExploitCodeMaturity *
                RemediationLevel *
                ReportConfidence
            )

    if TemporalScore:
        OverallScore = TemporalScore

    if EnvironmentalScore:
        OverallScore = EnvironmentalScore

    return BaseScore, TemporalScore, EnvironmentalScore, OverallScore

def CVSS3_0_calc(vdict):
    return _CVSS3_calc(vdict, s_cvss.cvss3_0)

def CVSS3_1_calc(vdict):
    return _CVSS3_calc(vdict, s_cvss.cvss3_1)

CVSS_CALC = {
    s_cvss.cvss2: CVSS2_calc,
    s_cvss.cvss3_0: CVSS3_0_calc,
    s_cvss.cvss3_1: CVSS3_1_calc,
}

def roundup(x):
    return (math.ceil(x * 10) / 10.0)

@s_stormtypes.registry.registerLib
class MitreAttackFlowLib(s_stormtypes.Lib):
    '''
    A Storm library which implements modeling MITRE ATT&CK Flow diagrams.
    '''
    _storm_lib_path = ('infosec', 'mitre', 'attack', 'flow')
    _storm_locals = (
        {'name': 'norm', 'desc': 'Normalize a MITRE ATT&CK Flow diagram in JSON format.',
         'type': {'type': 'function', '_funcname': '_norm',
                  'args': (
                      {'name': 'flow', 'type': 'data',
                       'desc': 'The MITRE ATT&CK Flow diagram in JSON format to normalize (flatten and sort).'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The normalized MITRE ATT&CK Flow diagram.', }
        }},
        {'name': 'ingest', 'desc': 'Ingest a MITRE ATT&CK Flow diagram in JSON format.',
         'type': {'type': 'function', '_funcname': '_storm_query',
                  'args': (
                      {'name': 'flow', 'type': 'data', 'desc': 'The JSON data to ingest.'},
                  ),
                  'returns': {'type': ['node', 'null'], 'desc': 'The it:mitre:attack:flow node representing the ingested attack flow diagram.'}}},

    )
    _storm_query = '''
        function ingest(flow) {
            // norm (validate, flatten, and sort)
            $flow = $lib.infosec.mitre.attack.flow.norm($flow)

            // Use the normed flow to generate the guid
            $guid = $lib.guid($flow)

            $objs_byid = ({})
            $objs_bytype = ({})

            for $obj in $flow.objects {
                $id = $obj.id
                $objs_byid.$id = $obj

                $type = $obj.type
                if (not $objs_bytype.$type) {
                    $objs_bytype.$type = ([])
                }
                $objs_bytype.$type.append($obj)
            }

            $attack_flow = $objs_bytype."attack-flow".0
            $created_by = $objs_byid.($attack_flow.created_by_ref)

            ($ok, $name) = $lib.trycast(ps:name, $created_by.name)
            if (not $ok) {
                $lib.warn(`Error casting contact name to ou:name: {$created_by.name}`)
                return()
            }

            ($ok, $contact_information) = $lib.trycast(inet:email, $created_by.contact_information)
            if (not $ok) {
                $lib.warn(`Error casting contact information to inet:email: {$created_by.contact_information}`)
                return()
            }

            [ it:mitre:attack:flow = $guid
                :name ?= $attack_flow.name
                :data = $flow
                :created ?= $attack_flow.created
                :updated ?= $attack_flow.modified
                :author:user ?= $lib.user.iden
                :author:contact = {[ ps:contact = (attack-flow, $name, $contact_information)
                                        :name = $name
                                        :email = $contact_information
                                    ]}
            ]

            return($node)
        }
    '''
    _validator = None

    def getObjLocals(self):
        return {
            'norm': self._norm,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _norm(self, flow):
        flow = await s_stormtypes.toprim(flow)

        if self.__class__._validator is None:
            schema = s_data.getJSON('attack-flow/attack-flow-schema-2.0.0')
            self.__class__._validator = s_config.getJsValidator(schema)

        flow = await s_coro.executor(self.__class__._validator, flow)
        flow = s_common.flatten(flow)
        flow['objects'] = sorted(flow.get('objects'), key=lambda x: x.get('id'))

        return flow

@s_stormtypes.registry.registerLib
class CvssLib(s_stormtypes.Lib):
    '''
    A Storm library which implements CVSS score calculations.
    '''
    _storm_locals = (
        {'name': 'calculate', 'desc': 'Calculate the CVSS score values for an input risk:vuln node.',
         'deprecated': {'eolvers': 'v3.0.0'},
         'type': {'type': 'function', '_funcname': 'calculate',
                  'args': (
                      {'name': 'node', 'type': 'node',
                       'desc': 'A risk:vuln node from the Storm runtime.'},
                      {'name': 'save', 'type': 'boolean', 'default': True,
                       'desc': 'If true, save the computed scores to the node properties.'},
                      {'name': 'vers', 'type': 'str', 'default': '3.1',
                       'desc': 'The version of CVSS calculations to execute.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing the computed score and subscores.', }
        }},
        {'name': 'calculateFromProps', 'desc': 'Calculate the CVSS score values from a props dict.',
         'deprecated': {'eolvers': 'v3.0.0'},
         'type': {'type': 'function', '_funcname': 'calculateFromProps',
                  'args': (
                      {'name': 'props', 'type': 'dict',
                       'desc': 'A props dictionary.'},
                      {'name': 'vers', 'type': 'str', 'default': '3.1',
                       'desc': 'The version of CVSS calculations to execute.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing the computed score and subscores.', }
        }},
        {'name': 'vectToProps', 'desc': 'Parse a CVSS v3.1 vector and return a dictionary of risk:vuln props.',
         'deprecated': {'eolvers': 'v3.0.0'},
         'type': {'type': 'function', '_funcname': 'vectToProps',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'A CVSS vector string.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary of risk:vuln secondary props.', }
        }},
        {'name': 'saveVectToNode', 'desc': 'Parse a CVSS v3.1 vector and record properties on a risk:vuln node.',
         'deprecated': {'eolvers': 'v3.0.0'},
         'type': {'type': 'function', '_funcname': 'saveVectToNode',
                  'args': (
                      {'name': 'node', 'type': 'node',
                       'desc': 'A risk:vuln node to record the CVSS properties on.'},
                      {'name': 'text', 'type': 'str', 'desc': 'A CVSS vector string.'},
                  ),
                  'returns': {'type': 'null', }
        }},
        {'name': 'vectToScore',
         'desc': '''
            Compute CVSS scores from a vector string.

            Takes a CVSS vector string, attempts to automatically detect the version
            (defaults to CVSS3.1 if it cannot), and calculates the base, temporal,
            and environmental scores.

            Raises:
                - BadArg: An invalid `vers` string is provided
                - BadDataValu: The vector string is invalid in some way.
                  Possible reasons are malformed string, duplicated
                  metrics, missing mandatory metrics, and invalid metric
                  values.''',
         'type': {'type': 'function', '_funcname': 'vectToScore',
                  'args': (
                      {'name': 'vect', 'type': 'str',
                       'desc': '''
                            A valid CVSS vector string.

                            The following examples are valid formats:

                                - CVSS 2 with version: `CVSS2#AV:L/AC:L/Au:M/C:P/I:C/A:N`
                                - CVSS 2 with parentheses: `(AV:L/AC:L/Au:M/C:P/I:C/A:N)`
                                - CVSS 2 without parentheses: `AV:L/AC:L/Au:M/C:P/I:C/A:N`
                                - CVSS 3.0 with version: `CVSS:3.0/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`
                                - CVSS 3.1 with version: `CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`
                                - CVSS 3.0/3.1 with parentheses: `(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L)`
                                - CVSS 3.0/3.1 without parentheses: `AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`'''},
                      {'name': 'vers',
                       'type': 'str',
                       'desc': f'''
                            A valid version string or None to autodetect the
                            version from the vector string. Accepted values
                            are: { ', '.join(s_cvss.versions) }, None.''',
                       'default': None}
                  ),
                  'returns': {'type': 'dict',
                              'desc': '''
                                A dictionary with the detected version, base score, temporal score,
                                environmental score, overall score, and normalized vector string.
                                The normalized vector string will have metrics ordered in
                                specification order and metrics with undefined values will be
                                removed. Example::

                                    {
                                        'version': '3.1',
                                        'score': 4.3,
                                        'base': 5.0,
                                        'temporal': 4.4,
                                        'environmental': 4.3,
                                        'normalized': 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L'
                                    }

                              '''}
        }},
    )
    _storm_lib_path = ('infosec', 'cvss',)

    def getObjLocals(self):
        return {
            'calculate': self.calculate,
            'vectToProps': self.vectToProps,
            'vectToScore': self.vectToScore,
            'saveVectToNode': self.saveVectToNode,
            'calculateFromProps': self.calculateFromProps,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def vectToProps(self, text):
        s_common.deprecated('$lib.infosec.cvss.vectToProps()', '2.137.0', '3.0.0')
        await self.runt.snap.warnonce('$lib.infosec.cvss.vectToProps() is deprecated.')
        return await self._vectToProps(text)

    async def _vectToProps(self, text):
        text = await s_stormtypes.tostr(text)
        props = {}

        try:
            for i, item in enumerate(text.split('/')):

                name, valu = item.split(':')

                if i == 0 and name == 'CVSS':
                    if valu == '3.1':
                        continue
                    raise s_exc.BadArg(mesg='Currently only version 3.1 is supported.', vers=valu)

                prop = vect2prop.get(name)
                if prop is None:
                    mesg = f'Invalid Vector Element: {name}'
                    raise s_exc.BadArg(mesg=mesg)

                props[prop] = valu

        except ValueError:
            mesg = f'Invalid CVSS Vector: {text}'
            raise s_exc.BadArg(mesg=mesg) from None

        return props

    async def saveVectToNode(self, node, text):
        s_common.deprecated('$lib.infosec.cvss.saveVectToNode()', '2.137.0', '3.0.0')
        await self.runt.snap.warnonce('$lib.infosec.cvss.saveVectToNode() is deprecated.')
        props = await self._vectToProps(text)
        for prop, valu in props.items():
            await node.set(prop, valu)

    async def calculate(self, node, save=True, vers='3.1'):

        save = await s_stormtypes.tobool(save)

        if node.ndef[0] != 'risk:vuln':
            mesg = '$lib.infosec.cvss.calculate() requires a risk:vuln node.'
            raise s_exc.BadArg(mesg=mesg)

        rval = await self.calculateFromProps(node.props, vers=vers)

        if save and rval.get('ok'):

            score = rval.get('score')
            if score is not None:
                await node.set('cvss:score', score)

            scores = rval.get('scores', {})

            basescore = scores.get('base')
            if basescore is not None:
                await node.set('cvss:score:base', basescore)

            temporalscore = scores.get('temporal')
            if temporalscore is not None:
                await node.set('cvss:score:temporal', temporalscore)

            environmentalscore = scores.get('environmental')
            if environmentalscore is not None:
                await node.set('cvss:score:environmental', environmentalscore)

        return rval

    @s_stormtypes.stormfunc(readonly=True)
    async def calculateFromProps(self, props, vers='3.1'):

        vers = await s_stormtypes.tostr(vers)

        if vers != '3.1':
            raise s_exc.BadArg(mesg='Currently only vers=3.1 is supported.')

        AV = props.get('cvss:av')
        AC = props.get('cvss:ac')
        PR = props.get('cvss:pr')
        UI = props.get('cvss:ui')
        S = props.get('cvss:s')
        C = props.get('cvss:c')
        _I = props.get('cvss:i')
        A = props.get('cvss:a')

        score = None
        impact = None
        basescore = None
        modimpact = None
        temporalscore = None
        exploitability = None
        environmentalscore = None

        if all((AV, AC, PR, UI, S, C, _I, A)):

            iscbase = 1.0 - ((1.0 - CVSS31['C'][C]) * (1.0 - CVSS31['I'][_I]) * (1.0 - CVSS31['A'][A]))

            if S == 'U':
                impact = 6.42 * iscbase
            else:
                impact = 7.52 * (iscbase - 0.029) - 3.25 * (iscbase - 0.02) ** 15

            exploitability = 8.22 * CVSS31['AV'][AV] * CVSS31['AC'][AC] * CVSS31['PR'][S][PR] * CVSS31['UI'][UI]

            if impact <= 0:
                basescore = 0
            elif S == 'U':
                basescore = min(roundup(impact + exploitability), 10.0)
            else:
                basescore = min(roundup(1.08 * (impact + exploitability)), 10.0)

            score = basescore

            if basescore:

                E = props.get('cvss:e')
                RL = props.get('cvss:rl')
                RC = props.get('cvss:rc')

                if all((E, RL, RC)):
                    expfactor = CVSS31['E'][E] * CVSS31['RL'][RL] * CVSS31['RC'][RC]
                    temporalscore = roundup(basescore * expfactor)
                    score = temporalscore
                else:
                    expfactor = CVSS31['E']['X'] * CVSS31['RL']['X'] * CVSS31['RC']['X']

                MAV = props.get('cvss:mav')
                MAC = props.get('cvss:mac')
                MPR = props.get('cvss:mpr')
                MUI = props.get('cvss:mui')

                MS = props.get('cvss:ms')
                MC = props.get('cvss:mc')
                MI = props.get('cvss:mi')
                MA = props.get('cvss:ma')
                CR = props.get('cvss:cr')
                IR = props.get('cvss:ir')
                AR = props.get('cvss:ar')

                if all((MAV, MAC, MPR, MUI, MS, MC, MI, MA, CR, IR, AR)):

                    if MAV == 'X': MAV = AV
                    if MAC == 'X': MAC = AC
                    if MPR == 'X': MPR = PR
                    if MUI == 'X': MUI = UI
                    if MS == 'X': MS = S
                    if MC == 'X': MC = C
                    if MI == 'X': MI = _I
                    if MA == 'X': MA = A

                    modiscbase = min(1.0 - (
                        (1.0 - (CVSS31['C'][MC] * CVSS31['CR'][CR])) *
                        (1.0 - (CVSS31['I'][MI] * CVSS31['IR'][IR])) *
                        (1.0 - (CVSS31['A'][MA] * CVSS31['AR'][AR]))
                    ), 0.915)

                    mav = CVSS31['AV'].get(MAV, 1)
                    mac = CVSS31['AC'].get(MAC, 1)
                    mpr = CVSS31['PR'][MS].get(MPR, 1)
                    mui = CVSS31['UI'].get(MUI, 1)

                    modexploit = 8.22 * mav * mac * mpr * mui

                    if MS == 'U':
                        modimpact = 6.42 * modiscbase
                    else:
                        modimpact = 7.52 * (modiscbase - 0.029) - 3.25 * (modiscbase * 0.9731 - 0.02) ** 13

                    if modimpact <= 0:
                        environmentalscore = 0
                    elif MS == 'U':
                        environmentalscore = roundup(roundup(min(modimpact + modexploit, 10.0)) * expfactor)
                    else:
                        environmentalscore = roundup(roundup(min(1.08 * (modimpact + modexploit), 10.0)) * expfactor)

                    score = environmentalscore

        rval = {
            'ok': True,
            'version': '3.1',
            'score': score,
            'scores': {
                'base': basescore,
                'temporal': temporalscore,
                'environmental': environmentalscore,
            },
        }

        if impact: rval['scores']['impact'] = round(impact, 1)
        if modimpact: rval['scores']['modifiedimpact'] = round(modimpact, 1)
        if exploitability: rval['scores']['exploitability'] = round(exploitability, 1)

        return rval

    @s_stormtypes.stormfunc(readonly=True)
    async def vectToScore(self, vect, vers=None):
        vers = await s_stormtypes.tostr(vers, noneok=True)

        if vers not in s_cvss.versions + [None]:
            raise s_exc.BadArg(mesg=f'Valid values for vers are: {s_cvss.versions + [None]}, got {vers}')

        detected = s_cvss.cvss3_1

        if vers is None:
            if 'Au:' in vect or vect.startswith('CVSS#2'):
                detected = s_cvss.cvss2

            elif vect.startswith('CVSS:3.0/'):
                detected = s_cvss.cvss3_0

            elif vect.startswith('CVSS:3.1/'):
                detected = s_cvss.cvss3_1

        else:
            detected = vers

        vdict = s_chop.cvss_validate(vect, detected)

        calc = CVSS_CALC[detected]
        base, temporal, environmental, overall = calc(vdict)

        return {
            'version': detected,
            'score': overall,

            'base': base,
            'temporal': temporal,
            'environmental': environmental,
            'normalized': s_chop.cvss_normalize(vdict, detected)
        }
