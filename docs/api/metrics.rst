Metrics and Monitoring
======================

The metrics module provides comprehensive monitoring, analysis, and reporting capabilities for CloudflareBypass operations.

.. currentmodule:: cloudflare_research.metrics

Core Metrics
------------

.. autoclass:: MetricsCollector
   :members:
   :undoc-members:
   :show-inheritance:

   Central metrics collection and analysis system.

.. automethod:: MetricsCollector.record_request
.. automethod:: MetricsCollector.record_challenge
.. automethod:: MetricsCollector.record_performance
.. automethod:: MetricsCollector.get_statistics

Request Metrics
---------------

.. autoclass:: RequestMetrics
   :members:
   :undoc-members:
   :show-inheritance:

   Detailed metrics for individual HTTP requests.

.. automethod:: RequestMetrics.start_timer
.. automethod:: RequestMetrics.end_timer
.. automethod:: RequestMetrics.record_error
.. automethod:: RequestMetrics.get_duration

Challenge Metrics
-----------------

.. autoclass:: ChallengeMetrics
   :members:
   :undoc-members:
   :show-inheritance:

   Metrics specific to challenge detection and solving.

.. automethod:: ChallengeMetrics.record_detection
.. automethod:: ChallengeMetrics.record_solution
.. automethod:: ChallengeMetrics.get_solve_rate
.. automethod:: ChallengeMetrics.get_avg_solve_time

Performance Monitoring
----------------------

.. autoclass:: PerformanceMonitor
   :members:
   :undoc-members:
   :show-inheritance:

   Real-time performance monitoring and alerting.

.. automethod:: PerformanceMonitor.start_monitoring
.. automethod:: PerformanceMonitor.stop_monitoring
.. automethod:: PerformanceMonitor.get_live_metrics
.. automethod:: PerformanceMonitor.set_alert_thresholds

Statistics Aggregation
----------------------

.. autoclass:: StatisticsAggregator
   :members:
   :undoc-members:
   :show-inheritance:

   Aggregates and analyzes collected metrics data.

.. automethod:: StatisticsAggregator.calculate_percentiles
.. automethod:: StatisticsAggregator.generate_summary
.. automethod:: StatisticsAggregator.detect_anomalies
.. automethod:: StatisticsAggregator.get_trends

Export and Reporting
--------------------

.. autoclass:: MetricsExporter
   :members:
   :undoc-members:
   :show-inheritance:

   Exports metrics data to various formats and systems.

.. automethod:: MetricsExporter.export_json
.. automethod:: MetricsExporter.export_csv
.. automethod:: MetricsExporter.export_prometheus
.. automethod:: MetricsExporter.export_influxdb

Report Generation
-----------------

.. autoclass:: ReportGenerator
   :members:
   :undoc-members:
   :show-inheritance:

   Generates comprehensive analysis reports.

.. automethod:: ReportGenerator.generate_performance_report
.. automethod:: ReportGenerator.generate_challenge_report
.. automethod:: ReportGenerator.generate_executive_summary
.. automethod:: ReportGenerator.generate_detailed_analysis

Visualization
-------------

.. autoclass:: MetricsVisualizer
   :members:
   :undoc-members:
   :show-inheritance:

   Creates visualizations for metrics data.

.. automethod:: MetricsVisualizer.create_timeline_chart
.. automethod:: MetricsVisualizer.create_success_rate_chart
.. automethod:: MetricsVisualizer.create_response_time_histogram
.. automethod:: MetricsVisualizer.create_heatmap

Alert System
------------

.. autoclass:: AlertManager
   :members:
   :undoc-members:
   :show-inheritance:

   Manages alerts and notifications for metric thresholds.

.. automethod:: AlertManager.set_threshold
.. automethod:: AlertManager.check_thresholds
.. automethod:: AlertManager.send_alert
.. automethod:: AlertManager.get_active_alerts

Configuration
-------------

.. autoclass:: MetricsConfig
   :members:
   :undoc-members:
   :show-inheritance:

   Configuration for metrics collection and monitoring.

Example Usage
-------------

Basic Metrics Collection::

    collector = MetricsCollector()

    # Record a request
    collector.record_request(
        url="https://example.com",
        method="GET",
        status_code=200,
        response_time=1.2,
        success=True
    )

    # Record challenge solving
    collector.record_challenge(
        challenge_type="javascript",
        detection_time=0.005,
        solve_time=2.1,
        success=True
    )

    # Get current statistics
    stats = collector.get_statistics()
    print(f"Success rate: {stats.success_rate:.2%}")
    print(f"Average response time: {stats.avg_response_time:.3f}s")

Performance Monitoring::

    monitor = PerformanceMonitor()

    # Set alert thresholds
    monitor.set_alert_thresholds(
        max_response_time=5.0,
        min_success_rate=0.95,
        max_error_rate=0.05
    )

    # Start monitoring
    await monitor.start_monitoring()

    # Make requests (monitoring happens automatically)
    async with CloudflareBypass() as bypass:
        for url in urls:
            response = await bypass.get(url)

    # Get live metrics
    live_metrics = monitor.get_live_metrics()
    print(f"Current RPS: {live_metrics.requests_per_second}")
    print(f"Active connections: {live_metrics.active_connections}")

Report Generation::

    generator = ReportGenerator(collector)

    # Generate performance report
    perf_report = generator.generate_performance_report(
        time_range="1h",
        include_charts=True
    )

    # Save report
    with open("performance_report.html", "w") as f:
        f.write(perf_report)

    # Generate executive summary
    summary = generator.generate_executive_summary()
    print(summary)

Data Export::

    exporter = MetricsExporter(collector)

    # Export to JSON
    json_data = exporter.export_json(time_range="24h")
    with open("metrics.json", "w") as f:
        f.write(json_data)

    # Export to Prometheus format
    prometheus_data = exporter.export_prometheus()

    # Export to InfluxDB
    await exporter.export_influxdb(
        host="localhost",
        port=8086,
        database="cloudflare_bypass"
    )

Advanced Analytics::

    aggregator = StatisticsAggregator(collector)

    # Calculate response time percentiles
    percentiles = aggregator.calculate_percentiles([50, 90, 95, 99])
    print(f"P95 response time: {percentiles[95]:.3f}s")

    # Detect performance anomalies
    anomalies = aggregator.detect_anomalies(
        metric="response_time",
        threshold=2.0  # 2 standard deviations
    )

    for anomaly in anomalies:
        print(f"Anomaly detected at {anomaly.timestamp}: {anomaly.value}")

    # Get performance trends
    trends = aggregator.get_trends(metric="success_rate", period="1h")
    print(f"Success rate trend: {trends.direction} ({trends.percentage:.1f}%)")

Custom Metrics::

    class CustomMetrics(MetricsCollector):
        def record_custom_event(self, event_type: str, value: float):
            self.custom_events.append({
                "timestamp": time.time(),
                "type": event_type,
                "value": value
            })

    collector = CustomMetrics()

    # Record custom business metrics
    collector.record_custom_event("user_conversion", 0.85)
    collector.record_custom_event("revenue_impact", 1250.0)

Alert Configuration::

    alert_manager = AlertManager()

    # Configure alerts
    alert_manager.set_threshold("response_time", "max", 3.0)
    alert_manager.set_threshold("success_rate", "min", 0.95)
    alert_manager.set_threshold("error_rate", "max", 0.10)

    # Check thresholds (called automatically by monitor)
    alerts = alert_manager.check_thresholds(current_metrics)

    for alert in alerts:
        print(f"ALERT: {alert.metric} {alert.condition} {alert.threshold}")

Visualization::

    visualizer = MetricsVisualizer(collector)

    # Create response time chart
    chart = visualizer.create_timeline_chart(
        metric="response_time",
        time_range="6h",
        title="Response Time Over Time"
    )

    # Save chart
    chart.save("response_time_chart.png")

    # Create success rate heatmap
    heatmap = visualizer.create_heatmap(
        x_metric="hour_of_day",
        y_metric="success_rate",
        title="Success Rate by Hour"
    )

.. seealso::
   :doc:`../user_guide/troubleshooting` for metrics-based troubleshooting guides.