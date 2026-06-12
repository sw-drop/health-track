from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from influxdb_client import InfluxDBClient
import os

app = Flask(__name__)
CORS(app)

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "health")
PIN_CODE = os.getenv("DASHBOARD_PIN", "2364")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)

@app.before_request
def check_pin():
    if request.path.startswith('/api/'):
        if request.method == 'OPTIONS':
            return '', 200
        client_pin = request.headers.get('X-PIN')
        if client_pin != PIN_CODE:
            return jsonify({"error": "Unauthorized"}), 401

@app.route('/')
def index():
    return send_from_directory('/html', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('/html', path)

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    query = f'''
        import "influxdata/influxdb/schema"
        schema.measurementTagValues(bucket: "{INFLUX_BUCKET}", measurement: "health_record", tag: "type")
    '''
    try:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        metrics = []
        for table in tables:
            for record in table.records:
                metrics.append(record.get_value())
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data/<metric_type>', methods=['GET'])
def get_data(metric_type):
    time_range = request.args.get('range', '1M')
    range_map = {
        '1W': '-7d',
        '1M': '-30d',
        '6M': '-180d',
        '1Y': '-1y',
        'ALL': '-10y'
    }
    flux_start = range_map.get(time_range, '-30d')

    agg_fn = "mean"
    sum_metrics = [
        "StepCount", "ActiveEnergyBurned", "BasalEnergyBurned", "FlightsClimbed", 
        "DistanceWalkingRunning", "AppleStandTime", "AppleExerciseTime", "TimeInDaylight"
    ]
    if any(m in metric_type for m in sum_metrics) or "SleepAnalysis" in metric_type:
        agg_fn = "sum"

    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {flux_start})
          |> filter(fn: (r) => r["_measurement"] == "health_record")
          |> filter(fn: (r) => r["type"] == "{metric_type}")
          |> filter(fn: (r) => r["_field"] == "value")
          |> aggregateWindow(every: 1d, fn: {agg_fn}, createEmpty: false)
          |> yield(name: "{agg_fn}")
    '''
    try:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        data_points = []
        unit = ""
        for table in tables:
            for record in table.records:
                if not unit and "unit" in record.values:
                    unit = record.values["unit"]
                data_points.append({
                    "time": record.get_time().isoformat(),
                    "value": record.get_value()
                })
        return jsonify({"unit": unit, "data": data_points})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
