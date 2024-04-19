units:
	ansible-test units --docker --python 3.12

integration:
	ansible-test integration --no-temp-workdir
