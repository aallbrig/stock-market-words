# English Dictionary Stock Tickers: A Website
Why? Why not. I remembered reading about how linux has a file with a dictionary in it.

I amuse myself imagining this list providing some sort of trading edge for any type of investor.

## Links

### [QA Environment](https://aallbrig.github.io/english-dictionary-stocks/)
![QR code for QA environment](media/qa-env-qr-code.png)
## Developer Section

### Getting Started
```bash
# Start up a local static HTTP server (requires python3)
./scripts/website-up.sh
./scripts/website-down.sh

# Single liner
./scripts/website-down.sh && ./scripts/website-up.sh
```

### TODO
- [ ] Bash script to pull stock tickers
- [ ] Python script to pull info about stock ticker from Yahoo Finance
- [ ] Website acceptance tests
    - [ ] index.spec.js
        - [x] Website describes itself
        - [x] Website has all exchanges link
        - [ ] Website has NASDAQ exchange link
        - [ ] Website has NYSE exchange link
        - [ ] Website has AMEX exchange link
        - [ ] Website provides telemetry on user activity
    - [ ] exchange-data-pages.spec.js
        - [ ] HTML page
            - [ ] display page title
            - [ ] display data
            - [ ] link to JSON format
            - [ ] (stretch) link to TXT format
            - [ ] (stretch) link to CSV format
            - [ ] (stretch) link to XML format
        - [ ] One HTML data display page for all exchanges
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

### Stretch
- [ ] Public API to extract raw data
    - [ ] Website contains API documentation
        - [ ] Website contains link to API documentation
    - [ ] /api/stocks
    - [ ] /api/stocks?filter=NASDAQ
    - [ ] /api/stocks?filter=NYSE
    - [ ] /api/stocks?filter=AMEX
    - [ ] /api/stocks?filter[]=NASDAQ&filter[]=NYSE&filter[]=AMEX
    - [ ] /api/stocks.json
    - [ ] /api/stocks.csv
    - [ ] /api/stocks.xml
    - [ ] /api/stocks.txt
    - [ ] /api/stocks.html
- [ ] Terraform (at least a bash script) exists to generate AWS resources
    - [ ] S3 bucket (for public website assets
    - [ ] Route 53 DNS configuration (link domain to S3 bucket)
- [ ] Website is deployed to AWS S3 using Github Actions
- [ ] Amazon associates product links? (Maybe book links? Investor books? Linux books? An investor related toy?)

### Resources
- https://github.com/rreichel3/US-Stock-Symbols
- /usr/share/dict/words (location of dictionary file on my mac)
