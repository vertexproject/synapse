cvss2 = '2'
cvss3_0 = '3.0'
cvss3_1 = '3.1'

versions = [
    cvss2,
    cvss3_0,
    cvss3_1,
]

tags = {
    cvss2: 'CVSS2#',
    cvss3_0: 'CVSS:3.0/',
    cvss3_1: 'CVSS:3.1/',
}

# Note: Metrics (the keys) of these dictionaries are ordered based on the order
# they should appear in the normalized vector string. If you add a new CVSS
# version, make sure the metrics are ordered as you want them to be normalized.
metrics = {
    cvss2: {
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

    cvss3_0: {
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

    cvss3_1: {},
}

# Copy the CVSS3.0 metrics to the CVSS3.1 key
metrics[cvss3_1] = metrics[cvss3_0]

undefined = {
    cvss2: 'ND',
    cvss3_0: 'X',
    cvss3_1: 'X',
}
