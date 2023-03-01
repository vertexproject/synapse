from .plugin import StormPlugin

def coverage_init(reg, options):
    plugin = StormPlugin(options)
    reg.add_configurer(plugin)
    reg.add_file_tracer(plugin)
