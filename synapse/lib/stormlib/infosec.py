import math
import decimal

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes


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

CVSS2_STR = '2'
CVSS3_0_STR = '3.0'
CVSS3_1_STR = '3.1'

CVSS_VERSIONS = [
    CVSS2_STR,
    CVSS3_0_STR,
    CVSS3_1_STR,
]

CVSS_TAGS = {
    CVSS2_STR: 'CVSS2#',
    CVSS3_0_STR: 'CVSS:3.0/',
    CVSS3_1_STR: 'CVSS:3.1/',
}

CVSS_METRICS = {
    CVSS2_STR: {
        # ID,   valid values,                       reqd?   values

        # Base metrics
        'AV': (('L', 'A', 'N'), True, {'L': 0.395, 'A': 0.646, 'N': 1.0}),
        'AC': (('H', 'M', 'L'), True, {'H': 0.35, 'M': 0.61, 'L': 0.71}),
        'Au': (('M', 'S', 'N'), True, {'M': 0.45, 'S': 0.56, 'N': 0.704}),
        'C': (('N', 'P', 'C'), True, {'N': 0.0, 'P': 0.275, 'C': 0.660}),
        'I': (('N', 'P', 'C'), True, {'N': 0.0, 'P': 0.275, 'C': 0.660}),
        'A': (('N', 'P', 'C'), True, {'N': 0.0, 'P': 0.275, 'C': 0.660}),

        # Temporal metrics
        'E': (('U', 'POC', 'F', 'H', 'ND'), False, {'U': 0.85, 'POC': 0.9, 'F': 0.95, 'H': 1.0, 'ND': 1.0}),
        'RL': (('OF', 'TF', 'W', 'U', 'ND'), False, {'OF': 0.87, 'TF': 0.90, 'W': 0.95, 'U': 1.0, 'ND': 1.0}),
        'RC': (('UC', 'UR', 'C', 'ND'), False, {'UC': 0.90, 'UR': 0.95, 'C': 1.0, 'ND': 1.0}),

        # Environmental metrics
        'CDP': (('N', 'L', 'LM', 'MH', 'H', 'ND'), False, {'N': 0.0, 'L': 0.1, 'LM': 0.3, 'MH': 0.4, 'H': 0.5, 'ND': 0.0}),
        'TD': (('N', 'L', 'M', 'H', 'ND'), False, {'N': 0.0, 'L': 0.25, 'M': 0.75, 'H': 1.0, 'ND': 1.0}),
        'CR': (('L', 'M', 'H', 'ND'), False, {'L': 0.5, 'M': 1.0, 'H': 1.51, 'ND': 1.0}),
        'IR': (('L', 'M', 'H', 'ND'), False, {'L': 0.5, 'M': 1.0, 'H': 1.51, 'ND': 1.0}),
        'AR': (('L', 'M', 'H', 'ND'), False, {'L': 0.5, 'M': 1.0, 'H': 1.51, 'ND': 1.0}),
    },

    CVSS3_0_STR: {
        # ID,   valid values,               reqd?   values

        # Base metrics
        'AV': (('N', 'A', 'L', 'P'), True, {'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2}),
        'AC': (('L', 'H'), True, {'H': 0.44, 'L': 0.77}),
        'PR': (('N', 'L', 'H'), True, {'U': {'N': 0.85, 'L': 0.62, 'H': 0.27}, # If Scope is Unchanged
                                       'C': {'N': 0.85, 'L': 0.68, 'H': 0.5}}), # If Scope is Changed
        'UI': (('N', 'R'), True, {'N': 0.85, 'R': 0.62}),
        'S': (('U', 'C'), True, {'U': 6.42, 'C': 7.52}),
        'C': (('H', 'L', 'N'), True, {'N': 0.0, 'L': 0.22, 'H': 0.56}),
        'I': (('H', 'L', 'N'), True, {'N': 0.0, 'L': 0.22, 'H': 0.56}),
        'A': (('H', 'L', 'N'), True, {'N': 0.0, 'L': 0.22, 'H': 0.56}),

        # Temporal metrics
        'E': (('X', 'H', 'F', 'P', 'U'), False, {'X': 1.0, 'U': 0.91, 'P': 0.94, 'F': 0.97, 'H': 1.0}),
        'RL': (('X', 'U', 'W', 'T', 'O'), False, {'X': 1.0, 'O': 0.95, 'T': 0.96, 'W': 0.97, 'U': 1.0}),
        'RC': (('X', 'C', 'R', 'U'), False, {'X': 1.0, 'U': 0.92, 'R': 0.96, 'C': 1.0}),

        # Environmental metrics
        'CR': (('X', 'H', 'M', 'L'), False, {'X': 1.0, 'L': 0.5, 'M': 1.0, 'H': 1.5}),
        'IR': (('X', 'H', 'M', 'L'), False, {'X': 1.0, 'L': 0.5, 'M': 1.0, 'H': 1.5}),
        'AR': (('X', 'H', 'M', 'L'), False, {'X': 1.0, 'L': 0.5, 'M': 1.0, 'H': 1.5}),
        'MAV': (('X', 'N', 'A', 'L', 'P'), False, {'X': 1.0, 'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2}),
        'MAC': (('X', 'L', 'H'), False, {'X': 1.0, 'H': 0.44, 'L': 0.77}),
        'MPR': (('X', 'N', 'L', 'H'), False, {'U': {'N': 0.85, 'L': 0.62, 'H': 0.27}, # If Scope is Unchanged
                                              'C': {'N': 0.85, 'L': 0.68, 'H': 0.5}}), # If Scope is Changed
        'MUI': (('X', 'N', 'R'), False, {'X': 1.0, 'N': 0.85, 'R': 0.62}),
        'MS': (('X', 'U', 'C'), False, {'X': 1.0, 'U': 6.42, 'C': 7.52}),
        'MC': (('X', 'N', 'L', 'H'), False, {'X': 1.0, 'N': 0.0, 'L': 0.22, 'H': 0.56}),
        'MI': (('X', 'N', 'L', 'H'), False, {'X': 1.0, 'N': 0.0, 'L': 0.22, 'H': 0.56}),
        'MA': (('X', 'N', 'L', 'H'), False, {'X': 1.0, 'N': 0.0, 'L': 0.22, 'H': 0.56}),
    },

    CVSS3_1_STR: {},
}

# Copy the CVSS3.0 metrics to the CVSS3.1 key
CVSS_METRICS[CVSS3_1_STR] = CVSS_METRICS[CVSS3_0_STR]

CVSS_UNDEFINED = {
    CVSS2_STR: 'ND',
    CVSS3_0_STR: 'X',
    CVSS3_1_STR: 'X',
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
    CVSS2_STR: CVSS2_round,
    CVSS3_0_STR: CVSS3_0_round,
    CVSS3_1_STR: CVSS3_1_round,
}

def CVSS_get_coefficients(vdict, vers):
    ret = {}

    METRICS = CVSS_METRICS[vers]
    UNDEFINED = CVSS_UNDEFINED[vers]

    Scope = None
    ModifiedScope = None

    if vers in (CVSS3_0_STR, CVSS3_1_STR):
        Scope = vdict['S']

        ModifiedScope = vdict.get('MS', UNDEFINED)
        if ModifiedScope == UNDEFINED:
            ModifiedScope = Scope

    for metric in METRICS:
        # These are special case lookups using the Scope/ModifiedScope value,
        # handle them later
        if metric in ('PR', 'MPR'):
            continue

        val = vdict.get(metric, UNDEFINED)
        ret[metric] = METRICS[metric][2][val]

    # This block handles the special case lookups in CVSS3.0/CVSS3.1. Specifically:
    #   - The extra Scope/ModifiedScope extra lookup for PR/MPR
    #   - The "modified" values in the environment metrics that (if
    #     present) modify the base metrics.
    if vers in (CVSS3_0_STR, CVSS3_1_STR):
        PR = vdict.get('PR')
        ret['PR'] = METRICS['PR'][2][Scope][PR]

        MPR = vdict.get('MPR', UNDEFINED)
        if MPR == UNDEFINED:
            ret['MPR'] = ret['PR']
        else:
            ret['MPR'] = METRICS['MPR'][2][ModifiedScope][MPR]

        def set_modval(metric, base_metric):
            val = vdict.get(metric, UNDEFINED)
            if val == UNDEFINED:
                ret[metric] = ret[base_metric]
            else:
                ret[metric] = METRICS[metric][2][val]

        set_modval('MAV', 'AV')
        set_modval('MAC', 'AC')
        set_modval('MUI', 'UI')
        set_modval('MC', 'C')
        set_modval('MI', 'I')
        set_modval('MA', 'A')

    return ret

def CVSS2_calc(vdict):
    ROUND = CVSS_ROUND[CVSS2_STR]
    UNDEFINED = CVSS_UNDEFINED[CVSS2_STR]
    COEFFS = CVSS_get_coefficients(vdict, CVSS2_STR)

    def _base(Impact):
        AccessVector = COEFFS['AV']
        AccessComplexity = COEFFS['AC']
        Authentication = COEFFS['Au']

        Exploitability = 20 * AccessVector * AccessComplexity * Authentication

        fImpact = 1.176
        if Impact == 0:
            fImpact = 0.0

        return ((0.6 * Impact) + (0.4 * Exploitability) - 1.5) * fImpact

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v2/guide#3-2-1-Base-Equation
    ConfImpact = COEFFS['C']
    IntegImpact = COEFFS['I']
    AvailImpact = COEFFS['A']

    Impact = 10.41 * (1 - (1 - ConfImpact) * (1 - IntegImpact) * (1 - AvailImpact))

    BaseScore = ROUND(_base(Impact))

    # Calculate the temporal score per the equation listed here:
    # https://www.first.org/cvss/v2/guide#3-2-2-Temporal-Equation
    Exploitability = COEFFS['E']
    RemediationLevel = COEFFS['RL']
    ReportConfidence = COEFFS['RC']

    E = vdict.get('E', UNDEFINED)
    RL = vdict.get('RL', UNDEFINED)
    RC = vdict.get('RC', UNDEFINED)

    if (E, RL, RC) == (UNDEFINED, UNDEFINED, UNDEFINED):
        TemporalScore = None
    else:
        TemporalScore = ROUND(BaseScore * Exploitability * RemediationLevel * ReportConfidence)

    '''
    Calculate the environmental score per the equation listed here:
    https://www.first.org/cvss/v2/guide#3-2-3-Environmental-Equation
    '''
    ConfImpact = COEFFS['C']
    IntegImpact = COEFFS['I']
    AvailImpact = COEFFS['A']

    ConfReq = COEFFS['CR']
    IntegReq = COEFFS['IR']
    AvailReq = COEFFS['AR']

    AdjustedImpact = min(
        10.0,
        10.41 * (1.0 - (1.0 - ConfImpact * ConfReq) * (1.0 - IntegImpact * IntegReq) * (1.0 - AvailImpact * AvailReq))
    )

    Exploitability = COEFFS['E']
    RemediationLevel = COEFFS['RL']
    ReportConfidence = COEFFS['RC']

    AdjustedTemporal = ROUND(_base(AdjustedImpact) * Exploitability * RemediationLevel * ReportConfidence)

    CollateralDamagePotential = COEFFS['CDP']
    TargetDistribution = COEFFS['TD']

    EnvironmentalScore = ROUND((AdjustedTemporal + (10 - AdjustedTemporal) * CollateralDamagePotential) * TargetDistribution)

    return BaseScore, TemporalScore, EnvironmentalScore

def _CVSS3_calc(vdict, vers):

    ROUND = CVSS_ROUND[vers]
    UNDEFINED = CVSS_UNDEFINED[vers]
    COEFFS = CVSS_get_coefficients(vdict, vers)

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-1-Base-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.
    _Scope = vdict['S']

    _ModifiedScope = vdict.get('MS', UNDEFINED)
    if _ModifiedScope == UNDEFINED:
        _ModifiedScope = _Scope

    Confidentiality = COEFFS['C']
    Integrity = COEFFS['I']
    Availability = COEFFS['A']

    ISS = 1 - ((1 - Confidentiality) * (1 - Integrity) * (1 - Availability))

    if _Scope == 'U':
        Impact = 6.42 * ISS
    else:
        Impact = 7.52 * (ISS - 0.029) - 3.25 * (ISS - 0.02) ** 15

    AttackVector = COEFFS['AV']
    AttackComplexity = COEFFS['AC']
    PrivilegesRequired = COEFFS['PR']
    UserInteraction = COEFFS['UI']

    Exploitability = 8.22 * AttackVector * AttackComplexity * PrivilegesRequired * UserInteraction

    if Impact <= 0:
        BaseScore = 0.0
    else:
        if _Scope == 'U':
            BaseScore = ROUND(min(Impact + Exploitability, 10.0))
        else:
            BaseScore = ROUND(min(1.08 * (Impact + Exploitability), 10.0))

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-2-Temporal-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.

    E = vdict.get('E', UNDEFINED)
    RL = vdict.get('RL', UNDEFINED)
    RC = vdict.get('RC', UNDEFINED)

    if (E, RL, RC) == (UNDEFINED, UNDEFINED, UNDEFINED):
        TemporalScore = None

    else:
        ExploitCodeMaturity = COEFFS['E']
        RemediationLevel = COEFFS['RL']
        ReportConfidence = COEFFS['RC']

        TemporalScore = ROUND(BaseScore * ExploitCodeMaturity * RemediationLevel * ReportConfidence)

    # Calculate the base score per the equation listed here:
    # https://www.first.org/cvss/v3.1/specification-document#7-3-Environmental-Metrics-Equations

    # We use the CVSS3.1 spec because it's more clear than the CVSS3.0 spec
    # but the equations are the same.

    ConfidentialityRequirement = COEFFS['CR']
    ModifiedConfidentiality = COEFFS['MC']
    IntegrityRequirement = COEFFS['IR']
    ModifiedIntegrity = COEFFS['MI']
    AvailabilityRequirement = COEFFS['AR']
    ModifiedAvailability = COEFFS['MA']

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

    ModifiedAttackVector = COEFFS['MAV']
    ModifiedAttackComplexity = COEFFS['MAC']
    ModifiedPrivilegesRequired = COEFFS['MPR']
    ModifiedUserInteraction = COEFFS['MUI']

    ModifiedExploitability = (
        8.22 *
        ModifiedAttackVector *
        ModifiedAttackComplexity *
        ModifiedPrivilegesRequired *
        ModifiedUserInteraction
    )

    if ModifiedImpact <= 0:
        EnvironmentalScore = 0.0
    else:
        ExploitCodeMaturity = COEFFS['E']
        RemediationLevel = COEFFS['RL']
        ReportConfidence = COEFFS['RC']

        if _ModifiedScope == 'U':
            EnvironmentalScore = ROUND(
                ROUND(
                    min(ModifiedImpact + ModifiedExploitability, 10)) *
                ExploitCodeMaturity *
                RemediationLevel *
                ReportConfidence
            )

        else:
            EnvironmentalScore = ROUND(
                ROUND(
                    min(1.08 * (ModifiedImpact + ModifiedExploitability), 10)) *
                ExploitCodeMaturity *
                RemediationLevel *
                ReportConfidence
            )

    return BaseScore, TemporalScore, EnvironmentalScore

def CVSS3_0_calc(vdict):
    return _CVSS3_calc(vdict, CVSS3_0_STR)

def CVSS3_1_calc(vdict):
    return _CVSS3_calc(vdict, CVSS3_1_STR)

CVSS_CALC = {
    CVSS2_STR: CVSS2_calc,
    CVSS3_0_STR: CVSS3_0_calc,
    CVSS3_1_STR: CVSS3_1_calc,
}

def validate(vect, vers):
    '''
    Validate (as best as possible) the vector string. Look for issues such as:
        - No duplicated metrics
        - Invalid metrics
        - Invalid metric values
        - Missing mandatory metrics

    Returns a dictionary with the parsed metric:value pairs.
    '''

    missing = []
    badvals = []
    invalid = []

    TAG = CVSS_TAGS[vers]
    METRICS = CVSS_METRICS[vers]

    # Do some canonicalization of the vector for easier parsing
    _vect = vect
    _vect = _vect.strip('(')
    _vect = _vect.strip(')')

    if _vect.startswith(TAG):
        _vect = _vect[len(TAG):]

    try:
        # Parse out metrics
        mets_vals = [k.split(':') for k in _vect.split('/')]

        # Convert metrics into a dictionary
        vdict = dict(mets_vals)

    except ValueError:
        raise s_exc.BadDataValu(mesg=f'Provided vector {vect} malformed')

    # Check that each metric is only specified once
    if len(mets_vals) != len(set(k[0] for k in mets_vals)):
        seen = []
        repeated = []

        for met, val in mets_vals:
            if met in seen:
                repeated.append(met)

            seen.append(met)

        raise s_exc.BadDataValu(mesg=f'Provided vectors {vect} contains duplicate metrics: {repeated}')

    for metric in vdict:
        # Check that provided metrics are valid
        if metric not in METRICS:
            raise s_exc.BadDataValu(mesg=f'Provided vector {vect} contains invalid metrics: {invalid}')

    for metric, (valids, mandatory, _) in METRICS.items():
        # Check for mandatory metrics
        if mandatory and metric not in vdict:
            raise s_exc.BadDataValu(mesg=f'Provided vector {vect} missing mandatory metric(s): {metric}')

        # Check if metric value is valid
        val = vdict.get(metric, None)
        if metric in vdict and val not in valids:
            raise s_exc.BadDataValu(mesg=f'Provided vector {vect} contains invalid metric value: {metric}:{val}')

    return vdict

def roundup(x):
    return (math.ceil(x * 10) / 10.0)

@s_stormtypes.registry.registerLib
class CvssLib(s_stormtypes.Lib):
    '''
    A Storm library which implements CVSS score calculations.
    '''
    _storm_locals = (
        {'name': 'calculate', 'desc': 'Calculate the CVSS score values for an input risk:vuln node.',
         'type': {'type': 'function', '_funcname': 'calculate',
                  'args': (
                      {'name': 'node', 'type': 'storm:node',
                       'desc': 'A risk:vuln node from the Storm runtime.'},
                      {'name': 'save', 'type': 'boolean', 'default': True,
                       'desc': 'If true, save the computed scores to the node properties.'},
                      {'name': 'vers', 'type': 'str', 'default': '3.1',
                       'desc': 'The version of CVSS calculations to execute.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary containing the computed score and subscores.', }
        }},
        {'name': 'calculateFromProps', 'desc': 'Calculate the CVSS score values from a props dict.',
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
         'type': {'type': 'function', '_funcname': 'vectToProps',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'A CVSS vector string.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'A dictionary of risk:vuln secondary props.', }
        }},
        {'name': 'saveVectToNode', 'desc': 'Parse a CVSS v3.1 vector and record properties on a risk:vuln node.',
         'type': {'type': 'function', '_funcname': 'saveVectToNode',
                  'args': (
                      {'name': 'node', 'type': 'storm:node',
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
                            are: { ', '.join(CVSS_VERSIONS) }, None.''',
                       'default': None}
                  ),
                  'returns': {'type': 'dict',
                              'desc': '''
                                A dictionary with the detected version, base
                                score, temporal score, and environmental score. Example:

                                    { 'version': '3.1', 'base': 5.0, 'temporal': 4.4, 'environmental': 4.3 }
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

    async def vectToScore(self, vect, vers=None):
        vers = await s_stormtypes.tostr(vers, noneok=True)

        if vers not in CVSS_VERSIONS + [None]:
            raise s_exc.BadArg(mesg=f'Valid values for vers are: {CVSS_VERSIONS + [None]}.')

        detected = CVSS3_1_STR

        if vers is None:
            if 'Au:' in vect or vect.startswith('CVSS#2'):
                detected = CVSS2_STR

            elif vect.startswith('CVSS:3.0/'):
                detected = CVSS3_0_STR

            elif vect.startswith('CVSS:3.1/'):
                detected = CVSS3_1_STR

        else:
            detected = vers

        vdict = validate(vect, detected)

        calc = CVSS_CALC[detected]
        base, temporal, environmental = calc(vdict)

        return {
            'version': detected,
            'base': base,
            'temporal': temporal,
            'environmental': environmental
        }
