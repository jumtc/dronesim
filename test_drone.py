import pytest
import json
from drone import DroneSimulator

@pytest.fixture
def drone():
    return DroneSimulator()

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

def test_crash_conditions(drone):
    # Test battery depletion crash
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
        for _ in range(201):  # Move beyond max_x_position (1000/5 = 200 steps needed)
            drone.update_telemetry({"speed": 5, "altitude": 0, "movement": "fwd"})

def test_telemetry_file_updates(drone, tmp_path):
    # Test if telemetry file is updated after each update
    result = drone.update_telemetry({"speed": 1, "altitude": 1, "movement": "fwd"})
    
    with open('telemetry.json', 'r') as f:
        saved_data = json.load(f)
    
    assert saved_data == result