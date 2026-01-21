import time
import json
import math
import paho.mqtt.client as mqtt
import threading

# Configuration
BROKER = "broker.emqx.io"
PORT = 1883 # Standard MQTT port (Python client doesn't need WSS usually, can use TCP)
ROBOT_ID = "reachy_1"
TOPIC_CMD = f"reachy/{ROBOT_ID}/cmd"
TOPIC_STATE = f"reachy/{ROBOT_ID}/state"

# Global state
latest_state = None

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC_STATE)

def on_message(client, userdata, msg):
    global latest_state
    try:
        latest_state = json.loads(msg.payload.decode())
        # print(f"Received state at t={latest_state['time']:.2f}")
    except Exception as e:
        print(f"Error parsing message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to {BROKER}...")
client.connect(BROKER, PORT, 60)

# Start background thread for network loop
t = threading.Thread(target=client.loop_forever)
t.daemon = True
t.start()

print("Starting control loop...")
print("Press Ctrl+C to stop.")

start_time = time.time()

try:
    while True:
        elapsed = time.time() - start_time
        
        # Example Control: Sine wave on first few actuators
        # Adjust these indices based on real Reachy Mini joints
        # 0-2 usually head joints? 
        
        # Simple head nodding/shaking
        val1 = 0.5 * math.sin(elapsed * 2.0) # Head Pan?
        val2 = 0.3 * math.cos(elapsed * 2.0) # Head Tilt?
        
        # Construct control array
        # This needs to be long enough for the robot
        # We can send a partial array or full array.
        # Let's send a generous array of zeros with our values inserted
        ctrl = [0.0] * 20 
        ctrl[0] = val1
        ctrl[1] = val2
        
        payload = {
            "ctrl": ctrl
        }
        
        client.publish(TOPIC_CMD, json.dumps(payload))
        
        time.sleep(0.033) # ~30Hz

except KeyboardInterrupt:
    print("Stopping...")
    client.disconnect()
