import pytest
import json
import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to sys.path to allow imports from the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from drone_simulator.drone import DroneSimulator
from drone_simulator.telemetry import TelemetryManager
from drone_simulator.environment import EnvironmentSimulator

@pytest.fixture
def temp_telemetry_file():
    """Create a temporary telemetry file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        # Initialize with empty telemetry
        tmp.write(b'{}')
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup after test
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)

@pytest.fixture
def drone(temp_telemetry_file):
    """Initialize drone simulator with a temporary telemetry file."""
    return DroneSimulator(telemetry_file=temp_telemetry_file)

def test_initial_telemetry(drone):
    assert drone.telemetry["x_position"] == 0
    assert drone.telemetry["y_position"] == 0
    assert drone.telemetry["battery"] == 100
    assert drone.telemetry["gyroscope"] == [0.0, 0.0, 0.0]
    assert drone.telemetry["wind_speed"] == 0
    assert drone.telemetry["dust_level"] == 0
    assert drone.telemetry["sensor_status"] == "GREEN"

def test_validate_input(drone):
    # Test valid input
    drone.user_input = {"speed": 5, "altitude": 1, "movement": "fwd"}
    assert drone.validate_input() is True
    
    # Test invalid inputs
    invalid_inputs = [
        (None, "Input must be a dictionary"),
        ({}, "Missing required key: speed"),
        ({"speed": "invalid", "altitude": 1, "movement": "fwd"}, "'speed' must be an integer, got str"),
        ({"speed": 6, "altitude": 1, "movement": "fwd"}, "'speed' must be between 0 and 5, got 6"),
        ({"speed": 5, "altitude": 1.5, "movement": "fwd"}, "'altitude' must be an integer, got float"),
        ({"speed": 5, "altitude": 1, "movement": "up"}, "'movement' must be one of ['fwd', 'rev'], got 'up'")
    ]
    
    for test_input, expected_error in invalid_inputs:
        drone.user_input = test_input
        assert drone.validate_input() == expected_error

def test_movement_updates(drone):
    # Test forward movement
    result = drone.update_telemetry({"speed": 5, "altitude": 0, "movement": "fwd"})
    assert result["x_position"] == 5
    
    # Test reverse movement
    result = drone.update_telemetry({"speed": 3, "altitude": 0, "movement": "rev"})
    assert result["x_position"] == 2  # 5 - 3 = 2

def test_altitude_changes(drone):
    # Test positive altitude change
    result = drone.update_telemetry({"speed": 0, "altitude": 10, "movement": "fwd"})
    assert result["y_position"] == 10
    
    # Test zero altitude change
    result = drone.update_telemetry({"speed": 0, "altitude": 0, "movement": "fwd"})
    assert result["y_position"] == 10  # Should remain at previous altitude

def test_battery_drain(drone):
    # Test battery drain with movement
    result = drone.update_telemetry({"speed": 4, "altitude": 0, "movement": "fwd"})
    assert result["battery"] < 100
    
    # Test battery drain with altitude change
    initial_battery = result["battery"]
    result = drone.update_telemetry({"speed": 0, "altitude": 10, "movement": "fwd"})
    assert result["battery"] < initial_battery

def test_environmental_conditions(drone):
    result = drone.update_telemetry({"speed": 0, "altitude": 0, "movement": "fwd"})
    
    # Test gyroscope bounds
    for value in result["gyroscope"]:
        assert -1.0 <= value <= 1.0
    
    # Test wind_speed and dust_level bounds
    assert 0 <= result["wind_speed"] <= 100
    assert 0 <= result["dust_level"] <= 100
    
    # Test sensor status values
    assert result["sensor_status"] in ["GREEN", "YELLOW", "RED"]

def test_crash_conditions():
    # Test battery depletion crash
    drone = DroneSimulator()
    with pytest.raises(ValueError):
        for _ in range(100):  # Run until battery depletes
            drone.update_telemetry({"speed": 5, "altitude": 1, "movement": "fwd"})
    
    # Test negative altitude crash
    drone = DroneSimulator()  # Reset drone
    with pytest.raises(ValueError):
        drone.update_telemetry({"speed": 0, "altitude": -10, "movement": "fwd"})
    
    # Test max position crash
    drone = DroneSimulator()  # Reset drone
    with pytest.raises(ValueError):
        # Need to set a smaller max_x_position for testing
        drone.max_x_position = 500
        for _ in range(101):  # Move beyond max_x_position (500/5 = 100 steps needed)
            drone.update_telemetry({"speed": 5, "altitude": 0, "movement": "fwd"})

def test_telemetry_file_updates(drone):
    # Test if telemetry file is updated after each update
    result = drone.update_telemetry({"speed": 1, "altitude": 1, "movement": "fwd"})
    
    telemetry_file = drone.telemetry_manager.telemetry_file
    with open(telemetry_file, 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data == result

# Additional tests for the new modular structure

def test_telemetry_manager():
    """Test TelemetryManager functions."""
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Test creating a new telemetry file
        manager = TelemetryManager(tmp_path)
        telemetry = manager.get_telemetry()
        
        # Test default values
        assert telemetry["x_position"] == 0
        assert telemetry["battery"] == 100
        
        # Test updating telemetry
        telemetry["x_position"] = 50
        manager.update_telemetry(telemetry)
        
        # Read directly from file to verify
        with open(tmp_path, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data["x_position"] == 50
        
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def test_environment_simulator():
    """Test EnvironmentSimulator functions."""
    telemetry = {
        "x_position": 10,
        "y_position": 20,
        "battery": 90,
        "gyroscope": [0.0, 0.0, 0.0],
        "wind_speed": 0,
        "dust_level": 0,
        "sensor_status": "GREEN"
    }
    
    # Test environmental simulation
    updated = EnvironmentSimulator.simulate_environmental_conditions(telemetry)
    
    # Original should be unchanged
    assert telemetry["gyroscope"] == [0.0, 0.0, 0.0]
    assert telemetry["wind_speed"] == 0
    
    # Updated should have new values
    assert updated["gyroscope"] != [0.0, 0.0, 0.0]
    assert 0 <= updated["wind_speed"] <= 100
    assert 0 <= updated["dust_level"] <= 100