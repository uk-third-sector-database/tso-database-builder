setup-pyenv:
	pyenv install 3.11.0
	
setup-venv:
	python3 -m venv .tso
	source .tso/bin/activate

install-deps:
	pip install -r test-requirements.txt