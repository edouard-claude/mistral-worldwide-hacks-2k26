.PHONY: build run dist clean docker

# Build the main binary
build:
	go build -o fakenews-arena .

# Build the NATS client
build-nats:
	go build -o nats-client ./cmd/nats

# Run the server
run: build
	./fakenews-arena

# Build Docker image
docker:
	docker build -t fakenews-arena .

# Create source tarball (excludes _bmad*, CLAUDE*, .git, doc, sessions, .claude, .DS_Store)
dist:
	tar --exclude='_bmad*' \
	    --exclude='CLAUDE*' \
	    --exclude='.git' \
	    --exclude='.claude' \
	    --exclude='.DS_Store' \
	    --exclude='doc' \
	    --exclude='docs' \
	    --exclude='sessions' \
	    --exclude='*.tar.gz' \
	    --exclude='fakenews-arena' \
	    --exclude='nats-client' \
	    -czvf gameofclaw-src.tar.gz .

# Clean build artifacts
clean:
	rm -f fakenews-arena nats-client gameofclaw-src.tar.gz
