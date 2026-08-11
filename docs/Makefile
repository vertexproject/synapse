# Minimal makefile for the Markdown documentation build (Sphinx-free). Builds
# this bundle's docs/synapse/ source tree directly into its canonical,
# COMMITTED bundle directory (../synapse/assets/docs) via
# synapse.tools.utils.doc -- the same builder synapse.tools.storm.pkg.doc
# uses for a Storm package's own docs/ tree, minus the pkgdef lookup, since
# this bundle has none of its own. See synapse/contributing/doc_mastering.md
# for the full docs/-vs-committed split this build relies on.
#
# This is the standalone entry point for this repo alone (the OSS synapse
# mirror has no monorepo docs/Makefile to discover/build every bundle at
# once -- see the parent repo's docs/Makefile for that), so it may not
# reference anything outside synsrc/.
SOURCEDIR := $(CURDIR)
REPODIR   := $(abspath ..)

export SYN_CORTEX_READPOOL_SIZE=0
export SYN_CORTEX_HEALTH_SYSCTL_CHECKS=false

docs:
	python -m synapse.tools.utils.doc $(SOURCEDIR)/synapse $(REPODIR)/synapse/assets/docs

# Retained alias -- the build output is Markdown, not HTML (Sphinx-era name).
html: docs

.PHONY: docs html
