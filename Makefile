test:
	python3 -m pytest

check:
	pyflakes3 `find . -name '*.py'` mkserver
	shellcheck -e SC2002 data/initrd data/mininit data/update

.PHONY: test check
