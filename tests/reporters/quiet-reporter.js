/**
 * Custom Jest Reporter - Quiet Reporter
 * 
 * Suppresses console.log output for passing tests
 * Shows full output (including console.log) only for failing tests
 */

class QuietReporter {
  constructor(globalConfig, options) {
    this._globalConfig = globalConfig;
    this._options = options;
  }

  onRunStart() {
    // Silence
  }

  onTestStart() {
    // Silence
  }

  onTestResult(test, testResult, aggregatedResult) {
    // Only show console output for failed tests
    if (testResult.numFailingTests > 0) {
      testResult.testResults.forEach((result) => {
        if (result.status === 'failed') {
          console.log(`\n❌ ${result.ancestorTitles.join(' › ')} › ${result.title}`);
          
          if (result.failureMessages && result.failureMessages.length > 0) {
            result.failureMessages.forEach(msg => console.log(msg));
          }
        }
      });
    }
  }

  onRunComplete() {
    // Default reporter will handle final summary
  }

  getLastError() {
    return this._shouldFail ? new Error('Custom reporter error') : undefined;
  }
}

module.exports = QuietReporter;
