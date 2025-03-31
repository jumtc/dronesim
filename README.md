# Drone Simulator

A WebSocket-based drone simulator that provides real-time telemetry data and simulates environmental conditions affecting drone flight.

## Features

- Real-time drone flight simulation with position tracking
- Battery simulation with realistic drain based on operations
- Environmental condition simulation (wind, dust, sensor status)
- WebSocket server for remote control and monitoring
- Telemetry persistence between sessions
- Admin dashboard for monitoring all drone connections
- Crash detection with detailed reporting

## Project Structure

```
drone_simulator/
├── __init__.py
├── admin_server.py     # Admin monitoring server
├── client.py           # WebSocket client for drone control
├── dashboard.py        # Admin dashboard interface
├── drone.py            # Core drone simulation logic
├── environment.py      # Environmental condition simulator
├── main.py             # Simple example usage
├── run_server.py       # Server startup script
├── server.py           # WebSocket server implementation
├── telemetry.py        # Telemetry data management
└── validators.py       # Input validation utilities
```

## Getting Started

### Prerequisites

- Python 3.7+
- websockets
- pytest (for running tests)

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install websockets pytest
```

### Running the Server

```bash
python drone_simulator/run_server.py
```

The server will start on `ws://localhost:8765` by default.

### Connecting Clients

You can connect to the simulator using:

1. The included client:
```bash
python drone_simulator/client.py
```

2. The example client:
```bash
python examples/simple_client.py
```

3. Your own WebSocket client implementation

## Admin Dashboard

Monitor all drone connections with the admin dashboard:

```bash
python drone_simulator/dashboard.py
```

## API Reference

### Client Commands

Send JSON commands to control the drone:

```json
{
    "speed": 0-5,        // Integer speed (0-5)
    "altitude": integer, // Positive or negative integer for altitude change
    "movement": "fwd"|"rev" // Forward or reverse movement
}
```

### Server Responses

The server responds with telemetry data:

```json
{
    "status": "success"|"crashed",
    "telemetry": {
        "x_position": integer,
        "y_position": integer,
        "battery": float,
        "gyroscope": [float, float, float],
        "wind_speed": integer,
        "dust_level": integer,
        "sensor_status": "GREEN"|"YELLOW"|"RED"
    },
    "metrics": {
        "iterations": integer,
        "total_distance": float
    }
}
```

## Todo

- Gives drone status in binary format. [Asmit]
- Gyroscope calculation, stable at low altitude. [Priyam]
- Windspeed tilt condition. [Priyam]
- Dust storm affects battery drain. [Trishit]
- Low altitude causes more battery drain, high altitude causes less battery drain (thickness of atm). [Trishit]
- Only calculate time/iteration when speed != 0, i.e, flight time. [Samrat]
- Drone condition detoriates at higher altitude. [Samrat]
- Option to repair drone when its condition is critical at the cost of battery. Drone crashes when condition is 0. [Samrat]
- Drone crashes if user doesn't provide instruction for 2-3 iterations. [Shrestha the god killer]
- Update tests accordingly. [AI]

## Crash conditions implemented

- Battery Drains to 0.
- Altitude becomes negative.

## Testing

Run the automated tests with:

```bash
pytest
```

## License

This project is licensed under the MIT License.