# Optional extra args for ansible-test (leave unset for full suite)
SANITY_TARGETS ?=
INTEGRATION_TARGETS ?=
UNIT_TARGETS ?=

UNIT_PYTHON_VERSION ?= 3.12

# galaxy.yml is not included in the installed collection artifact; read it from the source tree.
GALAXY_YML ?= $(CURDIR)/galaxy.yml

# Where ansible-galaxy installs the collection when we're running from outside
# the ansible_collections/vmware/vmware tree.
INSTALLED_COLLECTION_ROOT ?= $(HOME)/.ansible/collections/ansible_collections/vmware/vmware

# If we're already inside the collection tree, use it directly; otherwise point
# at the installed copy that upgrade-collections populates. This is decided here
# (make parse time) because $(eval) inside a recipe cannot be gated by a shell if.
ifeq ($(patsubst %/ansible_collections/vmware/vmware,MATCH,$(realpath $(CURDIR))),MATCH)
COLLECTION_ROOT ?= .
IN_COLLECTION_TREE := 1
else
COLLECTION_ROOT ?= $(INSTALLED_COLLECTION_ROOT)
IN_COLLECTION_TREE :=
endif

# Emit --exclude flags for build_ignore directories that exist (ansible-test errors on missing paths).
# $(1) = path to galaxy.yml; run from COLLECTION_ROOT so -d checks the install tree.
define sanity_build_ignore_excludes
sed -n '/^build_ignore:/,$$p' "$(1)" | sed '1d' | sed -n 's/^[[:space:]]*-[[:space:]]*//p' | while IFS= read -r path; do \
	if [ -d "$$path" ]; then printf ' --exclude %s' "$$path"; fi; \
done
endef

# setup commands
.PHONY: upgrade-collections
upgrade-collections:
ifndef IN_COLLECTION_TREE
	ansible-galaxy collection install --upgrade -p ~/.ansible/collections .
endif

.PHONY: install-collection-python-reqs
install-collection-python-reqs:
	pip install -r requirements.txt

.PHONY: install-linters-python-reqs
install-linters-python-reqs:
	pip install -r linters.requirements.txt

.PHONY: install-integration-reqs
install-integration-reqs: install-collection-python-reqs
	pip install -r tests/integration/requirements.txt; \
	ansible-galaxy collection install --upgrade -p ~/.ansible/collections -r tests/integration/requirements.yml

tests/integration/integration_config.yml:
	chmod +x ./tests/integration/generate_integration_config.sh; \
	./tests/integration/generate_integration_config.sh

# test commands
.PHONY: linters
linters: install-linters-python-reqs
	ansible-lint;

.PHONY: sanity
sanity: upgrade-collections
	cd $(COLLECTION_ROOT); \
	SANITY_EXCLUDES=$(if $(IN_COLLECTION_TREE),,$$($(call sanity_build_ignore_excludes,$(GALAXY_YML)))); \
	ansible-test sanity -v --color --coverage --junit \
		--docker default $$SANITY_EXCLUDES $(SANITY_TARGETS)

.PHONY: units
units: upgrade-collections
	cd $(COLLECTION_ROOT); \
	ansible-test units --docker --python $(UNIT_PYTHON_VERSION) --coverage $(UNIT_TARGETS); \
	ansible-test coverage combine --requirements --export tests/output/coverage/; \
	ansible-test coverage report --requirements --docker --omit 'tests/*' --show-missing;

.PHONY: units-coverage
units-coverage: units
	cd $(COLLECTION_ROOT); \
	ansible-test coverage xml --requirements; \
	cp tests/output/reports/coverage.xml $(CURDIR)/coverage-units.xml;

.PHONY: integration
integration: tests/integration/integration_config.yml upgrade-collections
	cd $(COLLECTION_ROOT); \
	ansible --version; \
	ansible-test --version; \
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. ansible-galaxy collection list; \
	ANSIBLE_ROLES_PATH=$(COLLECTION_ROOT)/tests/integration/targets \
		ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. \
		ansible-test integration $(INTEGRATION_TARGETS) $(CLI_ARGS)
