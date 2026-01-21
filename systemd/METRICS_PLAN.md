# Metrics Implementation Plan for Stock Market Words Pipeline

## Executive Summary

This document outlines a comprehensive plan for adding Prometheus-compatible metrics to the Stock Market Words data pipeline. The pipeline is a long-running process (30+ minutes) that fetches stock data from multiple external APIs, making observability crucial for operations.

## Goals

1. **Track pipeline performance**: Timing, throughput, and completion rates
2. **Monitor external dependencies**: FTP and Yahoo Finance API health
3. **Detect anomalies**: Unusual run times, API rate limits, data quality issues
4. **Enable visualization**: Grafana dashboards for operational insights
5. **Support alerting**: Prometheus AlertManager integration

## Architecture Overview

### Metrics Exposition

**Option 1: Pushgateway (Recommended for Batch Jobs)**
- Pipeline pushes metrics to Prometheus Pushgateway at completion
- Suitable for one-shot batch processes
- Metrics persist after job completion
- Simple integration with existing cron/systemd jobs

**Option 2: Node Exporter Textfile Collector**
- Pipeline writes metrics to `/var/lib/node_exporter/textfile_collector/*.prom`
- Node exporter scrapes these files
- Good for local metrics without additional infrastructure

**Option 3: Custom Exporter (Optional Future Enhancement)**
- Standalone HTTP server exposing `/metrics` endpoint
- Real-time metrics during pipeline execution
- More complex but provides live observability

**Recommended**: Start with Option 1 (Pushgateway) for simplicity and reliability.

## Metric Categories

### 1. Pipeline Execution Metrics

#### Timing Metrics

```python
# Gauge: Last run duration (seconds)
stock_market_words_pipeline_duration_seconds{step="full"} 1847.23

# Histogram: Duration distribution per step
stock_market_words_step_duration_seconds_bucket{step="sync-ftp", le="60"} 45
stock_market_words_step_duration_seconds_bucket{step="extract-prices", le="900"} 847
stock_market_words_step_duration_seconds_bucket{step="extract-metadata", le="1800"} 1456

# Gauge: Individual step durations
stock_market_words_step_duration_seconds{step="sync-ftp"} 23.4
stock_market_words_step_duration_seconds{step="extract-prices"} 845.7
stock_market_words_step_duration_seconds{step="extract-metadata"} 987.3
stock_market_words_step_duration_seconds{step="build"} 45.2
stock_market_words_step_duration_seconds{step="generate-hugo"} 12.1
```

#### Success/Failure Metrics

```python
# Counter: Total runs
stock_market_words_pipeline_runs_total{status="success"} 156
stock_market_words_pipeline_runs_total{status="failed"} 3
stock_market_words_pipeline_runs_total{status="partial"} 2

# Gauge: Last run status (1=success, 0=failure)
stock_market_words_pipeline_last_run_status 1

# Gauge: Last successful run timestamp
stock_market_words_pipeline_last_success_timestamp 1705795200

# Counter: Failures by step
stock_market_words_step_failures_total{step="sync-ftp"} 2
stock_market_words_step_failures_total{step="extract-prices"} 1
```

#### Progress Metrics

```python
# Gauge: Items processed per step
stock_market_words_step_items_processed{step="sync-ftp"} 8234
stock_market_words_step_items_processed{step="extract-prices"} 8234
stock_market_words_step_items_processed{step="extract-metadata"} 3421
stock_market_words_step_items_processed{step="build"} 3421

# Gauge: Processing rate (items/second)
stock_market_words_step_processing_rate{step="extract-prices"} 9.74
stock_market_words_step_processing_rate{step="extract-metadata"} 3.47
```

### 2. External Dependency Metrics

#### API Health

```python
# Gauge: Reachability check (1=up, 0=down)
stock_market_words_dependency_up{service="nasdaq_ftp"} 1
stock_market_words_dependency_up{service="yahoo_finance"} 1
stock_market_words_dependency_up{service="database"} 1

# Counter: API request counts
stock_market_words_api_requests_total{service="yahoo_finance", status="success"} 8234
stock_market_words_api_requests_total{service="yahoo_finance", status="rate_limit"} 12
stock_market_words_api_requests_total{service="yahoo_finance", status="error"} 8

# Histogram: API response times
stock_market_words_api_response_seconds_bucket{service="yahoo_finance", le="1.0"} 7890
stock_market_words_api_response_seconds_bucket{service="yahoo_finance", le="5.0"} 8200
```

#### FTP Metrics

```python
# Gauge: Downloaded file sizes (bytes)
stock_market_words_ftp_file_size_bytes{file="nasdaqlisted.txt"} 487234
stock_market_words_ftp_file_size_bytes{file="otherlisted.txt"} 234567

# Counter: FTP download success/failure
stock_market_words_ftp_downloads_total{file="nasdaqlisted.txt", status="success"} 156
stock_market_words_ftp_downloads_total{file="otherlisted.txt", status="success"} 156

# Gauge: FTP connection time (seconds)
stock_market_words_ftp_connection_seconds 2.34
```

### 3. Data Quality Metrics

```python
# Gauge: Ticker counts at each filtering stage
stock_market_words_tickers_count{stage="raw_ftp"} 8234
stock_market_words_tickers_count{stage="after_validation"} 7821
stock_market_words_tickers_count{stage="with_price_data"} 7654
stock_market_words_tickers_count{stage="filtered"} 3421
stock_market_words_tickers_count{stage="with_metadata"} 3398
stock_market_words_tickers_count{stage="scored"} 3398

# Gauge: Percentage of successful fetches
stock_market_words_fetch_success_rate{step="extract-prices"} 0.98
stock_market_words_fetch_success_rate{step="extract-metadata"} 0.99

# Counter: Missing data instances
stock_market_words_missing_data_total{field="market_cap"} 23
stock_market_words_missing_data_total{field="dividend_yield"} 156
stock_market_words_missing_data_total{field="beta"} 45
```

### 4. Resource Utilization Metrics

```python
# Gauge: Peak memory usage (bytes)
stock_market_words_memory_peak_bytes 1073741824

# Gauge: Database size (bytes)
stock_market_words_database_size_bytes 157286400

# Gauge: Output file sizes (bytes)
stock_market_words_output_file_size_bytes{file="trie.json"} 234567
stock_market_words_output_file_size_bytes{file="metadata.json"} 345678
```

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)

1. **Add Prometheus client library**
   ```bash
   pip install prometheus-client==0.19.0
   ```

2. **Create metrics module** (`src/stock_ticker/metrics.py`)
   ```python
   from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, push_to_gateway
   import time
   from contextlib import contextmanager
   
   # Create registry for this pipeline
   registry = CollectorRegistry()
   
   # Define metrics
   pipeline_duration = Histogram(
       'stock_market_words_step_duration_seconds',
       'Duration of pipeline steps',
       ['step'],
       registry=registry
   )
   
   pipeline_runs = Counter(
       'stock_market_words_pipeline_runs_total',
       'Total pipeline runs',
       ['status'],
       registry=registry
   )
   
   # ... more metrics
   
   @contextmanager
   def measure_duration(step_name):
       """Context manager to measure step duration"""
       start = time.time()
       try:
           yield
       finally:
           duration = time.time() - start
           pipeline_duration.labels(step=step_name).observe(duration)
   
   def push_metrics(pushgateway_url="http://localhost:9091", job="stock-market-words"):
       """Push metrics to Prometheus Pushgateway"""
       push_to_gateway(pushgateway_url, job=job, registry=registry)
   ```

3. **Instrument CLI commands**
   - Wrap each step with timing context manager
   - Record success/failure counters
   - Track item counts

### Phase 2: Detailed Metrics (Week 2)

1. **Instrument FTP sync**
   - Connection time
   - Download time per file
   - File sizes
   - Parse success/failure

2. **Instrument extractors**
   - Batch processing rate
   - API response times
   - Rate limit detection
   - Success rates per ticker

3. **Add data quality metrics**
   - Ticker counts at each stage
   - Missing data tracking
   - Validation failure counts

### Phase 3: Pushgateway Integration (Week 2-3)

1. **Set up Pushgateway**
   ```bash
   # Docker compose
   docker run -d -p 9091:9091 prom/pushgateway
   ```

2. **Modify run-all command**
   ```python
   from .metrics import measure_duration, push_metrics
   
   @cli.command('run-all')
   def run_all(ctx):
       with measure_duration('full'):
           # ... existing code ...
           
       # Push metrics at end
       try:
           push_metrics()
       except Exception as e:
           logger.warning(f"Failed to push metrics: {e}")
   ```

3. **Update systemd service**
   ```ini
   [Service]
   Environment="PROMETHEUS_PUSHGATEWAY=http://localhost:9091"
   ```

### Phase 4: Prometheus Configuration (Week 3)

1. **Configure Prometheus to scrape Pushgateway**
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'pushgateway'
       honor_labels: true
       static_configs:
         - targets: ['localhost:9091']
   ```

2. **Create recording rules**
   ```yaml
   # rules.yml
   groups:
     - name: stock_market_words
       interval: 1m
       rules:
         - record: job:pipeline_duration_seconds:avg
           expr: avg_over_time(stock_market_words_step_duration_seconds[1d])
         
         - record: job:pipeline_success_rate:24h
           expr: |
             sum(rate(stock_market_words_pipeline_runs_total{status="success"}[24h]))
             /
             sum(rate(stock_market_words_pipeline_runs_total[24h]))
   ```

### Phase 5: Alerting Rules (Week 4)

```yaml
# alerts.yml
groups:
  - name: stock_market_words_alerts
    rules:
      - alert: PipelineNotRunToday
        expr: (time() - stock_market_words_pipeline_last_success_timestamp) > 86400
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Stock Market Words pipeline hasn't run today"
          description: "Last successful run was {{ $value | humanizeDuration }} ago"
      
      - alert: PipelineDurationHigh
        expr: stock_market_words_step_duration_seconds{step="full"} > 3600
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline taking longer than usual"
          description: "Last run took {{ $value }}s (over 1 hour)"
      
      - alert: PipelineFailureRate
        expr: |
          rate(stock_market_words_pipeline_runs_total{status="failed"}[24h]) > 0.1
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "High pipeline failure rate"
          description: "{{ $value | humanizePercentage }} of runs failing"
      
      - alert: ExternalServiceDown
        expr: stock_market_words_dependency_up == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "External dependency unreachable"
          description: "{{ $labels.service }} has been down for 10+ minutes"
      
      - alert: YahooFinanceRateLimited
        expr: |
          rate(stock_market_words_api_requests_total{service="yahoo_finance",status="rate_limit"}[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Yahoo Finance rate limiting detected"
          description: "Pipeline is being rate limited by Yahoo Finance API"
```

## Grafana Dashboard Design

### Dashboard 1: Pipeline Overview

**Panels:**
1. **Status Indicator**: Current pipeline status (success/failed/running)
2. **Last Run**: Time since last successful run
3. **Run Duration**: Graph showing duration over time (7 days)
4. **Success Rate**: Gauge showing 24h success rate
5. **Items Processed**: Bar chart of tickers at each stage
6. **Step Breakdown**: Stacked area chart of step durations

### Dashboard 2: Performance

**Panels:**
1. **Duration Trends**: Line graph of each step's duration over 30 days
2. **Processing Rate**: Items/second for each step
3. **API Response Times**: Histogram of Yahoo Finance response times
4. **Throughput**: Tickers processed per run over time

### Dashboard 3: External Dependencies

**Panels:**
1. **Service Uptime**: Heatmap of FTP/Yahoo Finance availability
2. **API Errors**: Error rate over time by service
3. **Rate Limits**: Counter of rate limit hits
4. **Network Latency**: Graph of connection times

### Dashboard 4: Data Quality

**Panels:**
1. **Ticker Funnel**: Sankey diagram showing filtering stages
2. **Missing Data**: Bar chart of missing fields
3. **Fetch Success Rates**: Gauge per step
4. **Data Freshness**: Time since last data update

## Storage and Retention

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Retention: 90 days
storage:
  tsdb:
    retention.time: 90d
    retention.size: 10GB
```

## Example Queries

```promql
# Average pipeline duration over last 7 days
avg_over_time(stock_market_words_step_duration_seconds{step="full"}[7d])

# Success rate last 24 hours
sum(rate(stock_market_words_pipeline_runs_total{status="success"}[24h]))
/
sum(rate(stock_market_words_pipeline_runs_total[24h]))

# P95 extraction time for prices
histogram_quantile(0.95, 
  rate(stock_market_words_step_duration_seconds_bucket{step="extract-prices"}[1h])
)

# Tickers dropped at filtering stage
stock_market_words_tickers_count{stage="with_price_data"} 
- 
stock_market_words_tickers_count{stage="filtered"}

# API error rate
rate(stock_market_words_api_requests_total{status="error"}[5m])
```

## Testing Strategy

1. **Unit tests**: Mock Pushgateway, verify metric updates
2. **Integration tests**: Run pipeline with test Pushgateway
3. **Load testing**: Verify metrics don't impact performance
4. **Validation**: Compare metric timing vs log timestamps

## Rollout Plan

1. **Development**: Implement metrics in dev environment
2. **Testing**: Run for 1 week, validate accuracy
3. **Staging**: Deploy to staging with Pushgateway
4. **Production**: Gradual rollout with monitoring
5. **Documentation**: Update operator runbooks

## Operational Considerations

### Pushgateway Lifecycle
- Metrics persist until explicitly deleted or overwritten
- Each run should push complete metric set
- Use `grouping_key` to identify different pipeline runs

### Cardinality Management
- Avoid high-cardinality labels (e.g., ticker symbols)
- Use aggregation where possible
- Monitor Prometheus memory usage

### Failure Handling
- Metric push failures should not fail pipeline
- Log warnings if metrics unavailable
- Consider buffering metrics locally

## Cost/Benefit Analysis

**Benefits:**
- Detect performance regressions early
- Identify external API issues quickly
- Data-driven optimization decisions
- Historical trend analysis
- Proactive alerting

**Costs:**
- Development time: ~2-3 weeks
- Infrastructure: Prometheus + Pushgateway (~500MB RAM)
- Maintenance: Minimal ongoing effort
- Storage: ~1-2GB for 90 days retention

## Future Enhancements

1. **Real-time metrics**: Switch to custom exporter for live progress
2. **Distributed tracing**: Add OpenTelemetry for detailed request traces
3. **ML anomaly detection**: Use metrics to detect unusual patterns
4. **Cost tracking**: Add metrics for API rate limit consumption
5. **SLO/SLI tracking**: Define and track service level objectives

## References

- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Pushgateway Documentation](https://prometheus.io/docs/practices/pushing/)
- [Best Practices for Monitoring Batch Jobs](https://prometheus.io/docs/practices/instrumentation/#batch-jobs)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
