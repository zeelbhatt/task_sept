from neuronav.sensors import GetDepthai
from neuronav import NeuronavClient

sensor = GetDepthai("oak-d-pro", mock_source="synthetic")
client = NeuronavClient(api_key="test")
client.record(sensor, duration_seconds=5)

