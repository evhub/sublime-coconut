.PHONY: run
run: build
	python ./build.py

.PHONY: build
build:
	coconut -psf .
