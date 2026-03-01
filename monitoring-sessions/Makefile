APP_NAME ?= wh26-monitoring
CAPROVER_MACHINE ?= captain-wh26
TAR_FILE := /tmp/$(APP_NAME)-deploy.tar

.PHONY: dist deploy

dist:
	tar -cf $(TAR_FILE) \
		--exclude='.venv' \
		--exclude='__pycache__' \
		--exclude='.claude' \
		--exclude='.git' \
		--exclude='node_modules' \
		--exclude='examples' \
		--exclude='.DS_Store' \
		--exclude='Makefile' \
		.
	@echo "Created $(TAR_FILE)"

deploy: dist
	caprover deploy --caproverName $(CAPROVER_MACHINE) --appName $(APP_NAME) --tarFile $(TAR_FILE)
