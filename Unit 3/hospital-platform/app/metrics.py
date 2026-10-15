import time
from flask import request, g, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUESTS = Counter("http_requests_total", "Total HTTP requests",
                   ["method", "endpoint", "status"])
LATENCY = Histogram("http_request_seconds", "Request latency in seconds", ["endpoint"])


def register_metrics(app):
    @app.before_request
    def _start_timer():
        g.start = time.time()

    @app.after_request
    def _record(resp):
        endpoint = request.endpoint or "unknown"
        REQUESTS.labels(request.method, endpoint, resp.status_code).inc()
        LATENCY.labels(endpoint).observe(time.time() - g.get("start", time.time()))
        return resp

    @app.route("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
