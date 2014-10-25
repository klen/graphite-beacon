VENV=$(shell echo "$${VDIR:-'.env'}")

all: $(VENV)

.PHONY: help
# target: help - Display callable targets
help:
	@egrep "^# target:" [Mm]akefile

.PHONY: clean
# target: clean - Clean repo
clean:
	@rm -rf build dist docs/_build *.deb
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

.PHONY: deb
BUILD=$(CURDIR)/build
TARGET=/opt/graphite/beacon
PACKAGE_POSTFIX?=
PACKAGE_VERSION?=$(shell git describe --tags `git rev-list master --tags --max-count=1` | tr -d ' ') 
PACKAGE_NAME="graphite-beacon"
PACKAGE_FULLNAME=$(PACKAGE_NAME)$(PACKAGE_POSTFIX)
PACKAGE_MAINTAINER="Kirill Klenov <horneds@gmail.com>"
PACKAGE_DESCRIPTION="Simple allerting system for Graphite metrics."
PACKAGE_URL=https://github.com/klen/graphite-beacon.git
deb: clean
	@mkdir -p $(BUILD)/etc/init $(BUILD)/$(TARGET)
	@cp -r $(CURDIR)/graphite_beacon $(BUILD)/$(TARGET)/.
	@cp $(CURDIR)/debian/upstart.conf $(BUILD)/etc/init/graphite-beacon.conf
	@fpm -s dir -t deb -a all \
	    -n $(PACKAGE_FULLNAME) \
	    -v $(PACKAGE_VERSION) \
	    -m $(PACKAGE_MAINTAINER) \
	    --directories $(TARGET) \
	    --description $(PACKAGE_DESCRIPTION) \
	    --url $(PACKAGE_URL) \
	    --license "Copyright (C) 2014 horneds@gmail.com." \
	    --deb-user root \
	    --deb-group root \
	    --config-files /etc/init/graphite-beacon.conf \
	    --before-install $(CURDIR)/debian/before_install.sh \
	    --before-remove $(CURDIR)/debian/before_remove.sh \
	    --after-install $(CURDIR)/debian/after_install.sh \
	    -C $(CURDIR)/build \
	    -d "python2.7" \
	    opt etc
	for name in *.deb; do \
	    [ -f bintray ] && curl -T "$$name" -uklen:`cat bintray` https://api.bintray.com/content/klen/deb/graphite-beacon/all/$$name ; \
	done

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
