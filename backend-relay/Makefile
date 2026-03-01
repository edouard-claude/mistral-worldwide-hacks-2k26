APP_NAME ?= wh26-backend
CAPROVER_MACHINE ?= captain-wh26
TAR_FILE := /tmp/$(APP_NAME)-deploy.tar

.PHONY: dist deploy

dist:
	tar -cf $(TAR_FILE) \
		--exclude='.venv' \
		--exclude='__pycache__' \
		--exclude='sessions' \
		--exclude='.claude' \
		--exclude='_bmad' \
		--exclude='_bmad-output' \
		--exclude='docs' \
		--exclude='.git' \
		--exclude='node_modules' \
		--exclude='*.local.md' \
		--exclude='.DS_Store' \
		--exclude='Makefile' \
		.
	@echo "Created $(TAR_FILE)"

deploy: dist
	caprover deploy --caproverName $(CAPROVER_MACHINE) --appName $(APP_NAME) --tarFile $(TAR_FILE)
