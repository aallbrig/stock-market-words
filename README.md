# English Dictionary Stock Tickers: A Website
Why? Why not. I remembered reading about how linux has a file with a dictionary in it.

I amuse myself imagining this list providing some sort of trading edge for any type of investor.

## Developer Section
### TODO
- [ ] Bash script to pull stock tickers
- [ ] Python script to pull info about stock ticker from Yahoo Finance
- [ ] Website acceptance tests
    - [ ] Website has NASDAQ exchange section
    - [ ] Website has NYSE exchange section
    - [ ] Website has AMEX exchange section
    - [ ] Website provides telemetry on user activitiy
- [ ] Website (First Draft)
    - [ ] Website has NASDAQ exchange section
    - [ ] Website has NYSE exchange section
    - [ ] Website has AMEX exchange section
    - [ ] Website provides telemetry on user activitiy
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
