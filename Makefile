VENV=$(shell echo "$${VDIR:-'.env'}")

all: $(VENV)

.PHONY: help
# target: help - Display callable targets
help:
	@egrep "^# target:" [Mm]akefile

.PHONY: clean
# target: clean - Clean repo
clean:
	@rm -rf build dist docs/_build
	find $(CURDIR)/$(MODULE) -name "*.pyc" -delete
	find $(CURDIR)/$(MODULE) -name "*.orig" -delete
	find $(CURDIR)/$(MODULE) -name "__pycache__" -delete

# ==============
#  Bump version
# ==============

.PHONY: release
VERSION?=minor
# target: release - Bump version
release:
	@pip install bumpversion
	@bumpversion $(VERSION)
	@git checkout master
	@git merge develop
	@git checkout develop
	@git push --all
	@git push --tags

.PHONY: minor
minor: release

.PHONY: patch
patch:
	make release VERSION=patch

# ===============
#  Build package
# ===============

.PHONY: register
# target: register - Register module on PyPi
register:
	@python setup.py register

.PHONY: upload
# target: upload - Upload module on PyPi
upload: clean
	@pip install twine wheel
	@python setup.py sdist bdist_wheel
	@twine upload dist/*

# =============
#  Development
# =============

$(VENV): requirements.txt
	@[ -d $(VENV) ]	|| virtualenv --no-site-packages $(VENV)
	@$(VENV)/bin/pip install -r requirements.txt

.PHONY: run
# target: run - Run graphite-beacon
run: $(VENV)
	@$(VENV)/bin/pip install -r requirements-test.txt
	$(VENV)/bin/python -m graphite_beacon.app --config=example-config.json --pidfile=pid --graphite_url=http://zoo.local:8000

.PHONY: t
# target: t - Runs tests
t: $(VENV)
	@$(VENV)/bin/pip install -r requirements-test.txt
	py.test -xs tests.py
