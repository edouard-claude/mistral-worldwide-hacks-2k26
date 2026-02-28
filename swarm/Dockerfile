# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY *.go ./

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /fakenews-arena .

# Run stage
FROM alpine:3.19

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy binary from builder
COPY --from=builder /fakenews-arena .

# Create sessions directory
RUN mkdir -p /app/sessions

# Expose nothing (NATS client, not server)

# Default command - override with docker run args
ENTRYPOINT ["./fakenews-arena"]
CMD ["--dir", "/app"]
