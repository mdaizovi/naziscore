GCLOUD_HOME = $(shell readlink -f $(shell which gcloud) | sed "s/\(.*\)\/bin\/gcloud/\1/")/platform/google_appengine/google

venv: .venv
	@ln -sf $(GCLOUD_HOME) .venv/lib/python2.7/
	@.venv/bin/pip install --upgrade pip
	@.venv/bin/pip install -r requirements.txt
	@.venv/bin/python -c 'from google.appengine import *'

.venv:
	@virtualenv .venv
	.venv/bin/pip install -r requirements.txt

clean_venv:
	@$(RM) -rf .venv

clean:
	@find $(CURDIR) -name '*.pyc' -exec $(RM) {} \;
