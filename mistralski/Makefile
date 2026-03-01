APP_NAME := gorafi-simulator
VERSION  := $(shell date +%Y%m%d-%H%M%S)
ARCHIVE  := $(APP_NAME)-$(VERSION).tar.gz

.PHONY: tarball clean

tarball:
	tar czf "$(ARCHIVE)" \
		--exclude-from=.gitignore \
		--exclude=.git \
		--exclude=.claude \
		--exclude=.venv \
		--exclude=.pytest_cache \
		--exclude=.ruff_cache \
		--exclude='*.egg-info' \
		--exclude='$(APP_NAME)-*.tar.gz' \
		.
	@echo "$(ARCHIVE) created ($$(du -h "$(ARCHIVE)" | cut -f1))"

clean:
	rm -f $(APP_NAME)-*.tar.gz
