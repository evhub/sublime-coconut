.PHONY: run
run: build
	python ./build.py

.PHONY: build
build:
	coconut . -sf -j sys

.PHONY: setup
setup:
	pip install coconut-develop
	git clone https://github.com/evhub/tmtools.git
	pip install ./tmtools
	rm -rf tmtools
