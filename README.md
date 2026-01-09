# Stock Market Words: A Website
Why? Why not. I remembered reading about how linux has a file with a dictionary in it.

I amuse myself imagining this list providing some sort of trading edge for any type of investor.

## Links

### [QA Environment](https://aallbrig.github.io/stock-market-words/)
![QR code for QA environment](./hugo/site/static/media/qa-env-qr-code.png)

## Developer Section

### Performance Testing & Profiling

The TickerEngine algorithm can be performance tested and profiled. See the [Performance Profiling Guide](./docs/profiling-guide.md) for detailed instructions on:
- Running performance tests with sample texts
- Profiling with Node.js and Chrome DevTools
- Using WebStorm's built-in profiler (recommended for WebStorm users)
- Identifying and fixing bottlenecks

Quick start:
```bash
# Run unit performance tests (fast - tests algorithm directly)
npm run test:perf

# Run E2E performance tests (requires Hugo server running)
# First start the server: ./scripts/website-up.sh
npm run test:e2e:ticker

# Run page load tests (ensures all pages work without errors)
npm run test:e2e:pages

# Profile with Node.js built-in profiler
node --prof node_modules/.bin/jest tests/perf/
node --prof-process isolate-*.log > profile.txt
```

**Test Status:**
- ✅ Unit tests: All passing (~20ms with mock data)
- ❌ E2E ticker tests: MEDIUM/LONG samples timeout after 60s (needs optimization!)
- ✅ E2E page tests: **All 23 tests passing!** (jQuery errors fixed)

**Test Reports:**
- HTML reports generated automatically in `test-reports/index.html`
- Open in browser after running tests to see detailed results
- GitHub Actions uploads reports as artifacts
- See [docs/test-reports-guide.md](./docs/test-reports-guide.md) for details

See [tests/README.md](./tests/README.md) for complete test suite documentation.

### Hugo Site Development

The website is built using [Hugo](https://gohugo.io/), a fast static site generator.

**Running the development server:**

```bash
# Option 1: Change directory and run
cd hugo/site
hugo server

# Option 2: Run from repo root with flags
hugo server --source hugo/site

# Option 3: Run with additional flags (bind to all interfaces, custom port)
cd hugo/site
hugo server --bind 0.0.0.0 --port 1313
```

The site will be available at `http://localhost:1313` with live reload enabled.

**Building for production:**

```bash
# Option 1: From hugo/site directory
cd hugo/site
hugo

# Option 2: From repo root
hugo --source hugo/site

# Built files will be in hugo/site/public/
```

### Hugo Project Structure

```
hugo/site/
├── content/              # Markdown content files
├── layouts/              # HTML templates
│   ├── shortcodes/      # Reusable content widgets
│   ├── partials/        # Shared template components
│   └── _default/        # Default layouts
├── static/              # Static assets (CSS, JS, images, API data)
└── hugo.toml            # Site configuration
```

### Getting Started
Bash scripts
```bash
# Start up Hugo development server (requires Hugo)
./scripts/website-up.sh
./scripts/website-down.sh
# Test website with acceptance tests (requires node)
./scripts/website-test.sh

# Single liner
./scripts/website-down.sh && ./scripts/website-up.sh

# Extract stock exchange(s) data
./scripts/extract-exchanges-txt-data.sh

# Create resources on AWS (idempotent shell script)
./scripts/infrastructure-up.sh
```

Python scripts
```bash
# Virtual environment
python3 -m virtualenv venv
source venv/bin/activate
source venv/bin/deactivate

# Install requirements
pip3 install -r src/requirements.txt

# Test python files
python3 -m unittest -v

# Run python script
python3 -m src.app
```
### Developer quick commands
```bash
# Preferred Development Bash Command
./scripts/infrastructure-down.sh && ./scripts/infrastructure-down.sh && ./scripts/infrastructure-up.sh && ./scripts/infrastructure-up.sh
# Note: the double call is to ensure the script is idempotent in a user friendly way
```

### TODO
- [ ] Bash script to pull stock tickers
- [ ] Python script to pull info about stock ticker from Yahoo Finance
- [ ] Website acceptance tests
    - [ ] index.spec.js
        - [x] Website describes itself
        - [ ] "Data Updated Date"
        - [x] Website has all exchanges link
        - [ ] Website has NASDAQ exchange link
        - [ ] Website has NYSE exchange link
        - [ ] Website has AMEX exchange link
        - [ ] Website provides telemetry on user activity
    - [ ] exchange-data-pages.spec.js
        - [x] HTML page (One HTML data display page for all exchanges)
            - [ ] "Data Updated Date"
            - [ ] display page title
            - [ ] display data
            - [ ] link to JSON format
            - [ ] (stretch) link to TXT format
            - [ ] (stretch) link to CSV format
            - [ ] (stretch) link to XML format
        
        - [ ] (maybe) A-Z links are available. Once clicked, browser will scroll to that section. Makes it easier to navigate the results
- [ ] Website (First Draft)
    - [x] Website describes itself
    - [x] QR code to QA environment
    - [x] Website has all exchanges link
    - [ ] Website has NASDAQ exchange link
    - [ ] Website has NYSE exchange link
    - [ ] Website has AMEX exchange link
    - [ ] Website has all exchanges page
    - [ ] Website has NASDAQ exchange page
    - [ ] Website has NYSE exchange page
    - [ ] Website has AMEX exchange page
    - [ ] Website provides telemetry on user activity
- [ ] Website is available from Github Pages
    - [ ] Website JS loads QR code for Github Pages, when it detects it is running there
- [ ] Website is deployed to Github Pages using Github Actions
- [ ] Website data is updated by CRON Github Actions
- [ ] Bash script exists that captures AWS CLI commands
    - [ ] Buy domain in AWS
    - [ ] AWS DNS configuration
    - [ ] AWS CloudFront
    - [ ] AWS Certificate Manager
    - [x] AWS S3 bucket, for static website assets
          - [x] Configure bucket for serving static web assets
          - [ ] Enable public access for bucket
          - [x] Bucket for website access logs
    - [ ] AWS S3 bucket, for CloudFront logging

### Stretch Goals
- [ ] Public API to allow users to easily extract data
    - [ ] Website contains API documentation
        - [ ] Website contains link to API documentation
    - [ ] meta tag exists with references to (1) Yahoo Finance (2)rreichel3's repo, because credit
    - [ ] /api/stocks
    - [ ] /api/stocks?filter=NASDAQ
    - [ ] /api/stocks?filter=NYSE
    - [ ] /api/stocks?filter=AMEX
    - [ ] /api/stocks?filter[]=NASDAQ&filter[]=NYSE&filter[]=AMEX
    - [ ] /api/stocks.json or /api/stocks?format=json
    - [ ] /api/stocks.csv or /api/stocks?format=csv
    - [ ] /api/stocks.xml or /api/stocks?format=xml
    - [ ] /api/stocks.txt or /api/stocks?format=txt
    - [ ] /api/stocks.html or /api/stocks?format=html
- [ ] Terraform exists to generate AWS resources
    - [ ] S3 bucket (for public website assets
    - [ ] Route 53 DNS configuration (link domain to S3 bucket)
- [ ] Website is deployed to AWS S3 using Github Actions
- [ ] Amazon associates product links? (Maybe book links? Investor books? Linux books? An investor related toy?)

### Resources
- https://github.com/rreichel3/US-Stock-Symbols
- /usr/share/dict/words (location of dictionary file on my mac)
- https://gist.github.com/mgeeky/cebe7a05557569008c892e2130ec1ec9
