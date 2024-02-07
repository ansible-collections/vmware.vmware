RELEASE?=0.0.2

lint:
	ansible-lint

clean:
	rm -rf *tar.gz
# build:
# 	ansible-galaxy collection build
#
# publish:
# 	ansible-galaxy collection publish machacekondra-openshift_install-$(RELEASE).tar.gz --token=$(GALAXY_TOKEN)

integration:
	ansible-test sanity -v --color --coverage --junit --docker

