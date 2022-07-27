test:
	python3 -m pytest

check:
	pyflakes3 `find . -name '*.py'` mkserver

.PHONY: test check
