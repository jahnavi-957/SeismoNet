from pathlib import Path
import json

# Verify frozen checkpoint
checkpoint_path = Path('runs/experiment_002_p_training/best.pt')
print('Checkpoint status:')
print(f'  Path: {checkpoint_path}')
print(f'  Exists: {checkpoint_path.exists()}')
if checkpoint_path.exists():
    print(f'  Size: {checkpoint_path.stat().st_size / 1024 / 1024:.2f} MB')

# Verify protocol
protocol_path = Path('runs/validation_protocol_candidate_seed42/protocol.json')
print(f'\nProtocol status:')
print(f'  Path: {protocol_path}')
print(f'  Exists: {protocol_path.exists()}')
if protocol_path.exists():
    with open(protocol_path) as f:
        protocol = json.load(f)
    print(f'  Protocol ID: {protocol.get("protocol_id")}')
    print(f'  P threshold: {protocol.get("p_threshold")}')
    print(f'  S threshold: {protocol.get("s_threshold")}')
    print(f'  Tolerance: {protocol.get("tolerance_samples")} samples')

# Verify splits integrity
splits_path = Path('splits/split.json')
print(f'\nSplits status:')
print(f'  Path: {splits_path}')
print(f'  Exists: {splits_path.exists()}')
if splits_path.exists():
    with open(splits_path) as f:
        splits = json.load(f)
    print(f'  Split ID: {splits.get("split_id")}')
    print(f'  Train events: {len(splits.get("train", []))}')
    print(f'  Validation events: {len(splits.get("validation", []))}')
    print(f'  Test events: {len(splits.get("test", []))}')

# Test model loading
print('\nModel loading test:')
try:
    from backend.inference import SeismoInferenceEngine
    engine = SeismoInferenceEngine(Path('.').resolve())
    print(f'  Model loaded: {engine.model is not None}')
    print(f'  Device: {engine.device}')
    print(f'  Protocol ID: {engine.protocol_id}')
except Exception as e:
    print(f'  Error: {e}')
