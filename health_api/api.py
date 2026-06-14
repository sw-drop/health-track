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

@app.route('/api/sleep/segments', methods=['GET'])
def get_sleep_segments():
    time_range = request.args.get('range', '1M')
    range_map = {
        '1W': '-7d',
        '1M': '-30d',
        '6M': '-180d',
        '1Y': '-1y',
        'ALL': '-10y'
    }
    flux_start = range_map.get(time_range, '-30d')

    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {flux_start})
          |> filter(fn: (r) => r["_measurement"] == "SleepAnalysis")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        segments = []
        for table in tables:
            for record in table.records:
                if "start" in record.values and "stop" in record.values:
                    segments.append({
                        "start": record.values["start"],
                        "stop": record.values["stop"],
                        "state": record.values.get("state", "Unspecified")
                    })
        return jsonify({"data": segments})
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

@app.route('/api/sleep/summary', methods=['GET'])
def get_sleep_summary():
    time_range = request.args.get('range', '1M')
    range_map = {
        '1W': '-7d',
        '1M': '-30d',
        '6M': '-180d',
        '1Y': '-1y',
        'ALL': '-10y'
    }
    flux_start = range_map.get(time_range, '-30d')
    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: {flux_start})
          |> filter(fn: (r) => r["_measurement"] == "SleepAnalysis")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    try:
        tables = client.query_api().query(query, org=INFLUX_ORG)
        segments = []
        for table in tables:
            for record in table.records:
                if "start" in record.values and "stop" in record.values:
                    segments.append({
                        "start": record.values["start"],
                        "stop": record.values["stop"],
                        "state": record.values.get("state", "Unspecified")
                    })
        
        if not segments:
            return jsonify({"data": []})

        import datetime
        
        # Group segments into "sleep sessions" (nights)
        nights = {}
        for seg in segments:
            state = seg['state']
            if state in ['Unspecified', 'Asleep', 'InBed']:
                continue
            
            d_start = datetime.datetime.fromtimestamp(seg['start'])
            if d_start.hour < 12:
                session_date = (d_start - datetime.timedelta(days=1)).date()
            else:
                session_date = d_start.date()
                
            date_str = session_date.isoformat()
            if date_str not in nights:
                nights[date_str] = {"segments": [], "bedtime": None}
            nights[date_str]["segments"].append(seg)
            
            if state in ['Core', 'Deep', 'REM']:
                if nights[date_str]["bedtime"] is None or seg['start'] < nights[date_str]["bedtime"]:
                    nights[date_str]["bedtime"] = seg['start']

        if not nights:
            return jsonify({"data": []})
            
        # Calculate overall average bedtime for the range
        bedtimes = []
        for d, data in nights.items():
            if data["bedtime"] is not None:
                dt = datetime.datetime.fromtimestamp(data["bedtime"])
                hour = dt.hour + dt.minute/60.0
                if hour < 12:
                    hour += 24
                bedtimes.append(hour)
                
        avg_bedtime = sum(bedtimes) / len(bedtimes) if bedtimes else None
        
        results = []
        for date_str, data in nights.items():
            core_secs = sum(s['stop'] - s['start'] for s in data['segments'] if s['state'] == 'Core')
            deep_secs = sum(s['stop'] - s['start'] for s in data['segments'] if s['state'] == 'Deep')
            rem_secs = sum(s['stop'] - s['start'] for s in data['segments'] if s['state'] == 'REM')
            awake_secs = sum(s['stop'] - s['start'] for s in data['segments'] if s['state'] == 'Awake')
            
            total_sleep_mins = (core_secs + deep_secs + rem_secs) / 60.0
            duration_score = min(50, (total_sleep_mins / 480.0) * 50)
            
            awake_count = len([s for s in data['segments'] if s['state'] == 'Awake'])
            interruptions_score = max(0, 20 - (awake_count * 2))
            
            consistency_score = 30
            if avg_bedtime is not None and data["bedtime"] is not None:
                dt = datetime.datetime.fromtimestamp(data["bedtime"])
                hour = dt.hour + dt.minute/60.0
                if hour < 12:
                    hour += 24
                variance = abs(hour - avg_bedtime)
                consistency_score = max(0, 30 - (variance * 10))
                
            total_score = round(duration_score + interruptions_score + consistency_score)
            
            results.append({
                "date": date_str,
                "score": total_score,
                "total_sleep_mins": round(total_sleep_mins),
                "core_mins": round(core_secs / 60.0),
                "deep_mins": round(deep_secs / 60.0),
                "rem_mins": round(rem_secs / 60.0),
                "awake_mins": round(awake_secs / 60.0)
            })
            
        results.sort(key=lambda x: x["date"])
        
        return jsonify({"data": results})
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
