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
