.PHONY: help install serve build clean tags optimize-image fetch-data update-metric update-metric-all backfill-metric

# Default target
help:
	@echo "Available commands:"
	@echo "  make install             - Install dependencies"
	@echo "  make serve               - Start Jekyll development server"
	@echo "  make build               - Build the site"
	@echo "  make tags                - Generate tags data JSON"
	@echo "  make fetch-data          - Fetch latest pulse metrics data"
	@echo "  make update-metric      - Update a manual metric (e.g. make update-metric ID=china_pmi VAL=50.1)"
	@echo "  make update-metric-all  - Interactively update all manual metrics"
	@echo "  make backfill-metric    - Backfill history from CSV (e.g. make backfill-metric ID=china_pmi)"
	@echo "  make optimize-image IMG=<filename> - Optimize image for web"
	@echo "  make clean               - Clean generated files"
	@echo "  make help                - Show this help message"

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

# Optimize image for web
optimize-image:
	@if [ -z "$(IMG)" ]; then \
		echo "Error: Please specify image name with IMG=filename"; \
		echo "Usage: make optimize-image IMG=your-image.jpg"; \
		exit 1; \
	fi
	@if [ ! -f "assets/images/$(IMG)" ]; then \
		echo "Error: assets/images/$(IMG) not found"; \
		exit 1; \
	fi
	@echo "Optimizing $(IMG)..."
	@sips -Z 800 -s format jpeg -s formatOptions 70 "assets/images/$(IMG)" --out "assets/images/$(IMG).tmp" > /dev/null
	@mv "assets/images/$(IMG)" "assets/images/$(IMG).original"
	@mv "assets/images/$(IMG).tmp" "assets/images/$(IMG)"
	@echo "Original saved as: assets/images/$(IMG).original"
	@echo "Optimized: $(IMG)"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	bundle exec jekyll clean
	rm -rf _site .jekyll-cache .sass-cache

# Fetch latest pulse metrics data
fetch-data:
	@echo "Fetching pulse data..."
	@export $$(cat .env | xargs) && uv run scripts/fetch_pulse_data.py

# Update a manual metric
update-metric:
	@if [ -z "$(ID)" ] || [ -z "$(VAL)" ]; then \
		echo "Usage: make update-metric ID=<metric_id> VAL=<value> [DATE=YYYY-MM-DD]"; \
		echo ""; \
		uv run scripts/fetch_pulse_data.py update --list; \
		exit 1; \
	fi
	@if [ -n "$(DATE)" ]; then \
		uv run scripts/fetch_pulse_data.py update $(ID) $(VAL) --date $(DATE); \
	else \
		uv run scripts/fetch_pulse_data.py update $(ID) $(VAL); \
	fi

# Interactively update all manual metrics
update-metric-all:
	@uv run scripts/fetch_pulse_data.py update --all

# Backfill historical data from CSV
backfill-metric:
	@if [ -z "$(ID)" ]; then \
		echo "Usage: make backfill-metric ID=<metric_id> [CSV=path/to/file.csv]"; \
		echo ""; \
		echo "Available CSVs in data/backfill/:"; \
		ls -1 data/backfill/*.csv 2>/dev/null || echo "  (none)"; \
		exit 1; \
	fi
	@uv run scripts/fetch_pulse_data.py backfill $(ID) $${CSV:-data/backfill/$(ID).csv}
