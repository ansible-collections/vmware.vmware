# Optional extra args for ansible-test (leave unset for full suite)
SANITY_TARGETS ?=
INTEGRATION_TARGETS ?=
UNIT_TARGETS ?=

UNIT_PYTHON_VERSION ?= 3.14

# galaxy.yml is not included in the installed collection artifact; read it from the source tree.
GALAXY_YML ?= $(CURDIR)/galaxy.yml
COLLECTION_ROOT ?= $(HOME)/.ansible/collections/ansible_collections/vmware/vmware

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
	ansible-galaxy collection install --upgrade -p ~/.ansible/collections .

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
	SANITY_EXCLUDES=$$($(call sanity_build_ignore_excludes,$(GALAXY_YML))); \
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
integration: install-integration-reqs upgrade-collections
	cd $(COLLECTION_ROOT); \
	ansible --version; \
	ansible-test --version; \
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. ansible-galaxy collection list; \
	ANSIBLE_ROLES_PATH=$(COLLECTION_ROOT)/tests/integration/targets \
		ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. \
		ansible-test integration $(CLI_ARGS);

.PHONY: eco-vcenter-ci
eco-vcenter-ci: tests/integration/integration_config.yml install-integration-reqs upgrade-collections
	cd $(COLLECTION_ROOT); \
	ansible --version; \
	ansible-test --version; \
	ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. ansible-galaxy collection list; \
	chmod +x tests/integration/run_eco_vcenter_ci.sh; \
	ANSIBLE_ROLES_PATH=$(COLLECTION_ROOT)/tests/integration/targets \
		ANSIBLE_COLLECTIONS_PATH=$(COLLECTION_ROOT)/../.. \
		./tests/integration/run_eco_vcenter_ci.sh "$(INTEGRATION_TARGETS)"
