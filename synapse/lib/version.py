'''
Synapse utilites for dealing with Semvar versioning.
This includes the Synapse version information.
'''

##############################################################################
# The following are touched during the release process by bumpversion.
# Do not modify these directly.
version = (0, 0, 27)
verstring = '.'.join([str(x) for x in version])
