import synapse.lib.auth as s_auth

class Membrane:

    def __init__(self, name, rules, fn):
        self.name = name
        self.rules = s_auth.Rules(rules)
        self.rule_names = set([rule[1][0] for rule in rules])  # the set of strings to register handlers for
        self.fn = fn

    def filt(self, mesg):
        if self.rules.allow(mesg):
            return self.fn(mesg)
