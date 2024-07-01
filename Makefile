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
	@[ -f /tmp/vmware_vmware_failed_tests.txt ] && rm /tmp/vmware_vmware_failed_tests.txt || true; \
	@failed=0; \
	total=0; \
	echo "===============" >> /tmp/vmware_vmware_failed_tests.txt; \
	echo "Tests Summary" >> /tmp/vmware_vmware_failed_tests.txt; \
	echo "===============" >> /tmp/vmware_vmware_failed_tests.txt; \
	for dir in $(shell ansible-test integration --list-target --no-temp-workdir | grep 'vmware_'); do \
	  echo "Running integration test for $$dir"; \
	  total=$$((total + 1)); \
	  if ansible-test integration --no-temp-workdir $$dir; then \
	    echo -e "Test: $$dir ${GREEN}Passed${NC}" | tee -a /tmp/vmware_vmware_failed_tests.txt; \
	  else \
	    echo -e "Test: $$dir ${RED}Failed${NC}" | tee -a /tmp/vmware_vmware_failed_tests.txt; \
	    failed=$$((failed + 1)); \
	  fi; \
	done; \
	if [ $$failed -gt 0 ]; then \
	  echo "$$failed test(s) failed out of $$total." >> /tmp/vmware_vmware_failed_tests.txt; \
	  cat /tmp/vmware_vmware_failed_tests.txt; \
	  exit 1; \
	fi
