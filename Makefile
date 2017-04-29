venv:
	virtualenv .venv
	ln -s $(which gcloud | cut --d / -f 1-6)/platform/google_appengine/google .venv/lib/python2.7/

