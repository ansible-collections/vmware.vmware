# Define ANSI escape codes for colors
GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m  # No Color

.PHONY: units
units:
	ansible-test units --docker --python 3.12

.PHONY: prepare_symlinks
prepare_symlinks:
	ansible-playbook tools/prepare_symlinks.yml

.PHONY: integration
integration: prepare_symlinks
	ansible-test integration --no-temp-workdir

.PHONY: eco-vcenter-ci
eco-vcenter-ci: prepare_symlinks
	@[ -f /tmp/failed-tests.txt ] && rm /tmp/failed-tests.txt || true; \
	@failed=0; \
	total=0; \
	echo "===============" >> /tmp/failed-tests.txt; \
	echo "Tests Summary" >> /tmp/failed-tests.txt; \
	echo "===============" >> /tmp/failed-tests.txt; \
	for dir in $(shell ansible-test integration --list-target --no-temp-workdir | grep 'vmware_'); do \
	  echo "Running integration test for $$dir"; \
	  total=$$((total + 1)); \
	  if ansible-test integration --no-temp-workdir $$dir; then \
	    echo -e "Test: $$dir ${GREEN}Passed${NC}" | tee -a /tmp/failed-tests.txt; \
	  else \
	    echo -e "Test: $$dir ${RED}Failed${NC}" | tee -a /tmp/failed-tests.txt; \
	    failed=$$((failed + 1)); \
	  fi; \
	done; \
	if [ $$failed -gt 0 ]; then \
	  echo "$$failed test(s) failed out of $$total." >> /tmp/failed-tests.txt; \
	  cat /tmp/failed-tests.txt; \
	  exit 1; \
	fi
