.PHONY: build
build: clean setup
	python ./build.py
	npm install
	python ./scripts/vendor.py
	npx --yes @vscode/vsce@3 package

.PHONY: package
package:
	npm install
	python ./scripts/vendor.py
	npx --yes @vscode/vsce@3 package

.PHONY: install
install: build
	-find . -name '*.vsix' | xargs code --install-extension

.PHONY: setup
setup:
	npm install -g @vscode/vsce ovsx semver
	-git clone https://github.com/evhub/tmtools.git
	pip install -e ./tmtools
	pip install -r ./server/requirements.txt pytest

.PHONY: test
test:
	cd server && python -m pytest tests

.PHONY: test-vscode
test-vscode:
	npm install
	python ./scripts/vendor.py
	xvfb-run -a npm run test:vscode

.PHONY: docs-data
docs-data:
	python ./scripts/generate_docs.py

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
