VENV=$(shell echo "$${VDIR:-'.env'}")

all: $(VENV)

# =============
#  Development
# =============

$(VENV): requirements.txt
	@[ -d $(VENV) ]	|| virtualenv --no-site-packages $(VENV)
	@$(VENV)/bin/pip install -r requirements.txt

run: $(VENV)
	@$(VENV)/bin/pip install -r requirements-test.txt
	$(VENV)/bin/python -m graphite_beacon.app --config=example-config.json --pidfile=pid --graphite_url=http://zoo.local:8000

t: $(VENV)
	@$(VENV)/bin/pip install -r requirements-test.txt
	py.test -xs tests.py
