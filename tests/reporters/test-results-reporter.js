/**
 * Test Results Reporter
 * 
 * Saves test timing information for the status CLI command
 */

const { saveTestTimings } = require('../cli/test-status');

class TestResultsReporter {
  constructor(globalConfig, options) {
    this._globalConfig = globalConfig;
    this._options = options;
    this._startTime = null;
  }

  onRunStart() {
    this._startTime = Date.now();
  }

  onRunComplete(contexts, results) {
    const duration = Math.floor((Date.now() - this._startTime) / 1000);
    const success = results.numFailedTests === 0;
    
    const timingData = {
      lastRun: {
        timestamp: new Date().toISOString(),
        duration,
        success,
        numTotalTests: results.numTotalTests,
        numPassedTests: results.numPassedTests,
        numFailedTests: results.numFailedTests,
        numSkippedTests: results.numPendingTests
      }
    };
    
    // If this run was successful, also save as lastSuccessfulRun
    if (success) {
      timingData.lastSuccessfulRun = { ...timingData.lastRun };
    } else {
      // Preserve previous successful run if exists
      try {
        const { loadTestTimings } = require('../cli/test-status');
        const existing = loadTestTimings();
        if (existing && existing.lastSuccessfulRun) {
          timingData.lastSuccessfulRun = existing.lastSuccessfulRun;
        }
      } catch (error) {
        // Ignore error
      }
    }
    
    saveTestTimings(timingData);
  }
}

module.exports = TestResultsReporter;
