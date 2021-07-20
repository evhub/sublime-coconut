.PHONY: install
install: build
	find . -name '*.vsix' | xargs code --install-extension

.PHONY: build
build: setup
	python ./build.py
	vsce package

.PHONY: setup
setup:
	npm install -g vsce ovsx
	-git clone https://github.com/evhub/tmtools.git
	pip install ./tmtools

.PHONY: publish
publish: build
	vsce publish
	ovsx publish

.PHONY: atom
atom: build
	cp ./langs/* ./Syntaxes
	apm init --package ./language-coconut --convert .
