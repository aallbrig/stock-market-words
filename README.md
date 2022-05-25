# English Dictionary Stock Tickers: A Website
Why? Why not. I remembered reading about how linux has a file with a dictionary in it.

I amuse myself imagining this list providing some sort of trading edge for any type of investor.

## Links

### [QA Environment](https://aallbrig.github.io/english-dictionary-stocks/)
![QR code for QA environment](media/qa-env-qr-code.png)
## Developer Section

### Getting Started
Bash scripts
```bash
# Start up a local static HTTP server (requires python3)
./scripts/website-up.sh
./scripts/website-down.sh
# Test local static HTTP server (requires node)
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
