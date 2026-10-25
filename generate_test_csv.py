import csv
import random

random.seed(42)
samples = 3072

with open('test_waveform.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['sample_index', 'E', 'N', 'Z'])
    
    for i in range(samples):
        e = round(random.gauss(0, 0.1), 4)
        n = round(random.gauss(0, 0.1), 4)
        z = round(random.gauss(0, 0.1), 4)
        writer.writerow([i, e, n, z])

print(f"Created test_waveform.csv with {samples} samples")
