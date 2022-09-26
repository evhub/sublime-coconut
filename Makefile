.PHONY: build
build: clean setup
	python ./build.py
	vsce package

.PHONY: install
install: build
	-find . -name '*.vsix' | xargs code --install-extension

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

.PHONY: clean
clean:
	-find . -name "*.pyc" -delete
	-C:/GnuWin32/bin/find.exe . -name "*.pyc" -delete
	-find . -name "__pycache__" -delete
	-C:/GnuWin32/bin/find.exe . -name "__pycache__" -delete
	-find . -name "*.vsix" -delete
	-C:/GnuWin32/bin/find.exe . -name "*.vsix" -delete
