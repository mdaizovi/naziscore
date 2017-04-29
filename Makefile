GCLOUD_HOME = $(shell which gcloud | sed "s/\(.*\)\/bin\/gcloud/\1/")/platform/google_appengine/google

venv: .venv
	@ln -sf $(GCLOUD_HOME) .venv/lib/python2.7/

.venv:
	@virtualenv .venv

clean:
	@$(RM) -rf .venv
