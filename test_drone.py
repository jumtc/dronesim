import pytest
from drone import DroneSimulator

@pytest.fixture
def drone():
    return DroneSimulator()

def test_initial_telemetry(drone):
    assert drone.telemetry["battery"] == 100

def test_valid_input(drone):
    valid_input = {
        "speed": 5,
        "altitude": 1,
        "movement": "fwd"
    }
    result = drone.update_telemetry(valid_input)
    assert result["x_position"] == 5
    assert result["y_position"] == 1

@pytest.mark.parametrize("invalid_input,expected_error", [
    ({"speed": 6, "altitude": 1, "movement": "fwd"}, "Invalid input data: 'speed' must be between 0 and 5, got 6"),
    ({"speed": 5, "altitude": 1, "movement": "invalid"}, "Invalid input data: 'movement' must be one of ['fwd', 'rev'], got 'invalid'"),
])
def test_invalid_inputs(drone, invalid_input, expected_error):
    with pytest.raises(ValueError) as exc_info:
        drone.update_telemetry(invalid_input)
    assert str(exc_info.value) == expected_error