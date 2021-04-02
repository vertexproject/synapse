import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

CVSS31 = {
  'AV': {'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2},
  'AC': {'H': 0.44, 'L': 0.77},
  'PR': {'U': {'N': 0.85, 'L': 0.62, 'H': 0.27}, # These values are used if Scope is Unchanged
         'C': {'N': 0.85, 'L': 0.68, 'H': 0.5}}, # These values are used if Scope is Changed
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
                  'returns': {'type': 'dict', 'desc': 'The name of the newly created backup.', }
        }},
    )
    _storm_lib_path = ('infosec', 'cvss',)

    def getObjLocals(self):
        return {
            'calculate': self.calculate,
            #'vectToProps':
            #'propsToVect':
        }

    async def calculate(self, node, save=True, vers='3.1'):

        vers = await s_stormtypes.tostr(vers)
        wait = await s_stormtypes.tobool(save)

        if vers != '3.1':
            raise s_exc

        if not isinstance(node, s_stormtypes.Node):
            raise s_exc

        # unwrap the storm node...
        node = node.valu
        if node.ndef[0] != 'risk:vuln':
            raise s_exc

        AV = node.get('cvss:av')
        AC = node.get('cvss:ac')
        PR = node.get('cvss:pr')
        UI = node.get('cvss:ui')
        S = node.get('cvss:s')
        C = node.get('cvss:c')
        _I = node.get('cvss:i')
        A = node.get('cvss:a')

        score = None
        basescore = None
        temporalscore = None
        environmentalscore = None

        if all((AV, AC, PR, UI, S, C, I, A)):

            iscbase = 1.0 - ((1.0 - CVSS31['C'][C]) * (1.0 - CVSS31['I'][_I]) * (1.0 - CVSS31['A'][A]))

            if S == 'U':
                impact = 6.42 * iscbase
            else:
                impact = (7.52 * (iscbase - 0.029)) - (3.25 * ((iscbase - 0.02)**15))

            exploitability = 8.22 * CVSS31['AV'][AV] * CVSS31['AC'][AC] * CVSS31['PR'][PR] * CVSS31['UI'][UI]

            if impact <= 0:
                basescore = 0
            elif S == 'U':
                basescore = min(roundup(impact * exploitability), 10.0)
            else:
                basescore = min(roundup(1.08 * impact * exploitability), 10.0)

            score = basescore

            E = node.get('cvss:e')
            RL = node.get('cvss:rl')
            RC = node.get('cvss:rc')

            if all((basescore, E, RL, RC)):

                expfactor = CVSS31['E'][E] * CVSS31['RL'][RL] * CVSS31['RC'][RC]

                temporalscore = roundup(basescore * expfactor)
                score = temporalscore

                MAV = node.get('cvss:mav')
                MAC = node.get('cvss:mac')
                MPR = node.get('cvss:mpr')
                MUI = node.get('cvss:mui')

                MS = node.get('cvss:ms')
                MC = node.get('cvss:mc')
                MI = node.get('cvss:mi')
                MA = node.get('cvss:ma')
                CR = node.get('cvss:cr')
                IR = node.get('cvss:ir')
                AR = node.get('cvss:ar')

                if all((MAV, MAC, MPR, MUI, MS, MC, MI, MA, CR, IR, AR)):

                    modiscbase = min(1.0 - (
                        (1.0 - (CVSS31['MC'][MC] * CVSS31['CR'][CR])) *
                        (1.0 - (CVSS31['MI'][MI] * CVSS31['IR'][IR])) *
                        (1.0 - (CVSS31['MA'][MA] * CVSS31['AR'][AR]))
                    ), 0.915)

                    modexploit = 8.22 * CVSS31['MAV'][MAV] * CVSS31['MAC'][MAC] * CVSS31['MPR'][MPR] * CVSS31['MUI'][MUI]

                    if MS == 'U':
                        modimpact = 6.42 * modiscbase
                    else:
                        modimpact = 7.52 * (modiscbase - 0.029) - (3.25 * ((modiscbase * 0.9731 - 0.02) ** 13))

                    if modimpact <= 0:
                        envscore = 0
                    elif MS == 'U':
                        environmentalscore = roundup(roundup(min(modimpact + modexploit, 10.0)) * expfactor)
                    else:
                        environmentalscore = roundup(roundup(min(1.08 * (modimpact + modexploit), 10.0)) * expfactor)

                    score = environmentalscore

        if save:
            if score is not None:
                await node.set('cvss:score', score)

            if basescore is not None:
                await node.set('cvss:score:base', basescore)

            if temporalscore is not None:
                await node.set('cvss:score:temporal', temporalscore)

            if environmentalscore is not None:
                await node.set('cvss:score:environmental', environmentalscore)

        return {
            'ok': True,
            'version': '3.1',
            'score': score,
            'scores': {
                'base': basescore,
                'temporal': temporalscore,
                'environmental': environmentalscore,
            },
        }
