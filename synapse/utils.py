import importlib

class FeatureNotEnabledException(Exception):
    pass

class FeatureNotEnabled:
    def __init__(self, module_name):
        self.module_name = module_name

    def __getattribute__(self, name):
        if name == 'module_name':
            return object.__getattribute__(self, name)
        else:
            raise FeatureNotEnabledException('{}.{} not enabled due to missing dependencies for {}'
                                             .format(self.module_name, name, self.module_name))

def importOptionalModule(module_name):
    try:
        module_or_stub = importlib.import_module(module_name)
    except ImportError:
        module_or_stub = FeatureNotEnabled(module_name)
    return module_or_stub
