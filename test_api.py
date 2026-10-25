import json
import urllib.request

with open('test_waveform.csv', 'r') as f:
    csv_content = f.read()

payload = {
    'csv_content': csv_content,
    'mapping': {
        'e_col': 'E',
        'n_col': 'N',
        'z_col': 'Z',
        'sampling_rate_hz': 100,
        'arrival_coordinate_type': 'sample_index'
    },
    'mode': 'predict',
    'p_threshold': 0.05,
    's_threshold': 0.10
}

req = urllib.request.Request(
    'http://127.0.0.1:8001/api/csv/analyze',
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read())
        print('Analysis successful!')
        print('Mode:', result.get('mode'))
        print('Predictions count:', len(result.get('predictions', [])))
        if result.get('predictions'):
            pred = result['predictions'][0]
            print('First prediction keys:', list(pred.keys()))
except Exception as e:
    print('Error:', str(e))
