# Test Reports Guide

This document explains how to generate, view, and share test reports from the test suite.

## Report Formats

The test suite generates reports in multiple formats:

1. **HTML Report** - Human-readable web page with full test details
2. **JUnit XML** - Machine-readable format for CI/CD integration
3. **Console Output** - Real-time output during test execution

## Generating Reports Locally

Reports are automatically generated when you run tests:

```bash
# Run tests (reports auto-generated)
npm run test:e2e:pages

# Reports are saved to test-reports/ directory
ls test-reports/
# index.html    - HTML report (open in browser)
# junit.xml     - JUnit XML report
```

### Viewing HTML Reports Locally

After running tests, open the HTML report in your browser:

```bash
# macOS
open test-reports/index.html

# Linux
xdg-open test-reports/index.html

# Windows
start test-reports/index.html

# Or use a simple HTTP server
npx http-server test-reports -o
```

The HTML report includes:
- ✅ Pass/fail status for each test
- ⏱️ Execution times
- 📋 Console logs
- ❌ Error messages and stack traces
- 📊 Summary statistics

## GitHub Actions Integration

### Automatic Report Generation

When you push code to GitHub, the E2E Tests workflow automatically:

1. Runs all tests
2. Generates HTML and XML reports
3. Uploads reports as artifacts
4. (Optional) Deploys reports to GitHub Pages

### Viewing Reports in GitHub

**Method 1: Download Artifacts**

1. Go to your repository on GitHub
2. Click "Actions" tab
3. Click on a workflow run
4. Scroll to "Artifacts" section
5. Download "test-reports.zip"
6. Extract and open `index.html`

**Method 2: GitHub Pages (if enabled)**

If you enable the GitHub Pages deployment in the workflow:

1. Reports are automatically published to your GitHub Pages site
2. URL: `https://[username].github.io/stock-market-words/`
3. Updated on every push to `main` branch

### Setting Up GitHub Pages for Reports

To enable automatic report publishing:

1. Go to repository Settings → Pages
2. Set Source to "GitHub Actions"
3. The workflow will automatically deploy reports
4. Reports will be available at your GitHub Pages URL

## Report Structure

### HTML Report (index.html)

```
Test Report
├── Summary
│   ├── Total Tests
│   ├── Passed
│   ├── Failed
│   └── Duration
├── Test Suites
│   └── For each test file:
│       ├── Suite name
│       ├── Test list
│       ├── Pass/fail status
│       ├── Duration
│       └── Error details (if failed)
└── Console Logs
    └── All console output
```

### JUnit XML (junit.xml)

Standard JUnit format for CI/CD integration:
- Compatible with Jenkins, GitLab CI, CircleCI, etc.
- Can be parsed by most CI/CD platforms
- Useful for trend analysis over time

## Advanced Usage

### Custom Report Configuration

Edit `package.json` to customize reports:

```json
{
  "jest": {
    "reporters": [
      "default",
      ["jest-html-reporter", {
        "pageTitle": "My Custom Title",
        "outputPath": "custom-path/report.html",
        "theme": "lightTheme"  // or "darkTheme"
      }]
    ]
  }
}
```

### Multiple Report Formats

Generate additional formats:

```bash
# Install additional reporters
npm install --save-dev jest-json-reporter

# Add to package.json jest.reporters array
```

### Generating PDF Reports

Convert HTML reports to PDF:

```bash
# Using Chrome/Chromium headless
google-chrome --headless --print-to-pdf=test-report.pdf test-reports/index.html

# Or use a Node.js tool
npm install -g html-pdf-node
html-to-pdf test-reports/index.html test-reports/report.pdf
```

## CI/CD Integration Examples

### Jenkins

```groovy
stage('Test') {
  steps {
    sh 'npm run test:e2e:pages'
  }
  post {
    always {
      junit 'test-reports/junit.xml'
      publishHTML([
        reportDir: 'test-reports',
        reportFiles: 'index.html',
        reportName: 'Test Report'
      ])
    }
  }
}
```

### GitLab CI

```yaml
test:
  script:
    - npm run test:e2e:pages
  artifacts:
    when: always
    reports:
      junit: test-reports/junit.xml
    paths:
      - test-reports/
    expire_in: 30 days
```

### CircleCI

```yaml
- run:
    name: Run tests
    command: npm run test:e2e:pages
- store_test_results:
    path: test-reports
- store_artifacts:
    path: test-reports
    destination: test-reports
```

## Sharing Reports

### Email Reports

1. Run tests locally
2. Open `test-reports/index.html` in browser
3. Save as PDF (File → Print → Save as PDF)
4. Email the PDF

### Slack/Teams Integration

Share reports in team channels:

```bash
# Example Slack webhook notification
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test Report Available: https://your-github-pages-url"}' \
  YOUR_SLACK_WEBHOOK_URL
```

### Embedding in Documentation

Add test status badges to README:

```markdown
![Tests](https://github.com/username/repo/actions/workflows/e2e-tests.yml/badge.svg)
```

## Troubleshooting

### Reports Not Generated

**Issue**: No `test-reports/` directory after running tests

**Solution**:
- Ensure jest-html-reporter is installed: `npm install`
- Check package.json has reporters configured
- Verify tests actually ran (not skipped)

### HTML Report Doesn't Open

**Issue**: HTML file opens as plain text

**Solution**:
- Use a proper browser (Chrome, Firefox, Safari)
- Try the HTTP server method: `npx http-server test-reports -o`

### Reports Not Uploading to GitHub

**Issue**: Artifacts not appearing in GitHub Actions

**Solution**:
- Check workflow completed successfully
- Verify test-reports/ directory was created
- Check Actions permissions in repo settings

### GitHub Pages Not Updating

**Issue**: Reports not showing on GitHub Pages

**Solution**:
1. Verify GitHub Pages is enabled in Settings
2. Check workflow has proper permissions
3. Ensure main branch protection allows workflow writes
4. Check the deployment step in Actions logs

## Best Practices

1. **Always Review Reports**: Don't just check pass/fail, review the details
2. **Archive Important Reports**: Download critical reports before they expire
3. **Share Links, Not Files**: Use GitHub Pages or artifacts instead of emailing files
4. **Check Trends**: Compare reports over time to spot degrading performance
5. **Fix Failures Quickly**: Don't let broken tests accumulate

## Report Retention

- **Local reports**: Deleted on next test run (in test-reports/)
- **GitHub artifacts**: 30 days retention (configurable in workflow)
- **GitHub Pages**: Persistent until overwritten by next deployment

## Examples

### Example HTML Report Features

The HTML report shows:

```
✅ Website Page Load Tests
  ✅ Page Loading
    ✅ Home (/) loads successfully (1984 ms)
    ✅ About (/about/) loads successfully (1059 ms)
    ❌ Raw FTP Data (/raw-ftp-data/) has console errors (2066 ms)
    
  Error: expect(received).toHaveLength(expected)
  Expected length: 0
  Received length: 3
  Received array: ["jQuery is not defined", ...]
```

### Example JUnit XML Structure

```xml
<testsuites>
  <testsuite name="Website Page Load Tests" tests="23" failures="2">
    <testcase name="Home (/) loads successfully" time="1.984"/>
    <testcase name="Raw FTP Data has console errors" time="2.066">
      <failure>jQuery is not defined</failure>
    </testcase>
  </testsuite>
</testsuites>
```

## Resources

- [Jest HTML Reporter Documentation](https://github.com/Hargne/jest-html-reporter)
- [Jest JUnit Reporter](https://www.npmjs.com/package/jest-junit)
- [GitHub Actions Artifacts](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts)
- [GitHub Pages Deployment](https://docs.github.com/en/pages/getting-started-with-github-pages)
