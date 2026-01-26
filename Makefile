.PHONY: help install serve build clean tags

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make serve      - Start Jekyll development server"
	@echo "  make build      - Build the site"
	@echo "  make tags       - Generate tags data JSON"
	@echo "  make clean      - Clean generated files"
	@echo "  make help       - Show this help message"

# Install dependencies
install:
	@echo "Installing dependencies..."
	bundle config set --local path 'vendor/bundle'
	bundle install

# Start Jekyll server
serve:
	@echo "Starting Jekyll server at http://localhost:4000"
	bundle exec jekyll serve --livereload

# Build the site
build:
	@echo "Building site..."
	bundle exec jekyll build

# Generate tags data
tags:
	@echo "Generating tags data..."
	bundle exec ruby generate_tags.rb

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	bundle exec jekyll clean
	rm -rf _site .jekyll-cache .sass-cache
