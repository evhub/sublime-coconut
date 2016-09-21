.PHONY: build run

run: build
	python ./build.py

build:
	coconut -psf .
