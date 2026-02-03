#!/usr/bin/env node

/**
 * Test CLI - Status Command
 * 
 * Provides test run statistics and timing information
 * 
 * Usage:
 *   node tests/cli/test-status.js
 *   npm run test:status
 */

const fs = require('fs');
const path = require('path');

const TEST_TIMING_FILE = path.join(__dirname, '..', '..', '.test-timings.json');

function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

function loadTestTimings() {
  try {
    if (fs.existsSync(TEST_TIMING_FILE)) {
      const data = fs.readFileSync(TEST_TIMING_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.error('Error loading test timings:', error.message);
  }
  return null;
}

function saveTestTimings(timings) {
  try {
    fs.writeFileSync(TEST_TIMING_FILE, JSON.stringify(timings, null, 2));
  } catch (error) {
    console.error('Error saving test timings:', error.message);
  }
}

function showStatus() {
  const timings = loadTestTimings();
  
  console.log('\n📊 Test Status\n');
  
  if (!timings) {
    console.log('No previous test run data found.');
    console.log('Run `npm test` to collect timing information.\n');
    return;
  }
  
  const { lastRun, lastSuccessfulRun } = timings;
  
  if (lastRun) {
    console.log('Last Run:');
    console.log(`  Date: ${new Date(lastRun.timestamp).toLocaleString()}`);
    console.log(`  Duration: ${formatDuration(lastRun.duration)}`);
    console.log(`  Status: ${lastRun.success ? '✅ Passed' : '❌ Failed'}`);
    console.log(`  Tests: ${lastRun.numPassedTests}/${lastRun.numTotalTests} passed`);
    if (lastRun.numFailedTests > 0) {
      console.log(`  Failed: ${lastRun.numFailedTests}`);
    }
    if (lastRun.numSkippedTests > 0) {
      console.log(`  Skipped: ${lastRun.numSkippedTests}`);
    }
    console.log();
  }
  
  if (lastSuccessfulRun && (!lastRun || !lastRun.success)) {
    console.log('Last Successful Run:');
    console.log(`  Date: ${new Date(lastSuccessfulRun.timestamp).toLocaleString()}`);
    console.log(`  Duration: ${formatDuration(lastSuccessfulRun.duration)}`);
    console.log(`  Tests: ${lastSuccessfulRun.numPassedTests} passed`);
    console.log();
    
    console.log(`⏱️  Estimated time for next successful run: ${formatDuration(lastSuccessfulRun.duration)}`);
  } else if (lastRun && lastRun.success) {
    console.log(`⏱️  Estimated time for next run: ${formatDuration(lastRun.duration)}`);
  }
  
  console.log();
}

// Handle as CLI command
if (require.main === module) {
  const command = process.argv[2];
  
  if (command === 'save') {
    // Called by test runner to save timings
    const timingData = JSON.parse(process.argv[3] || '{}');
    saveTestTimings(timingData);
  } else {
    // Default: show status
    showStatus();
  }
}

module.exports = {
  loadTestTimings,
  saveTestTimings,
  showStatus
};
