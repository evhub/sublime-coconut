.PHONY: build
build:
	python ./build.py
	cp ./langs/* ./syntaxes

.PHONY: setup
setup:
	-git clone https://github.com/evhub/tmtools.git
	pip install ./tmtools

.PHONY: atom
atom: build
	cp ./langs/* ./Syntaxes
	apm init --package ./language-coconut --convert .
	rm -rf ./Syntaxes
