import json
import random
from typing import Dict, Union
import time

class DroneSimulator:
    def __init__(self):
        initial_telemetry = {
        "x_position": 0,
        "y_position": 0, 
        "battery": 100,
        "gyroscope": [0.0, 0.0, 0.0],
        "wind_speed": 0,
        "dust_level": 0,
        "sensor_status": "GREEN"
        }
        
        try:
            with open('telemetry.json', 'r') as f:
                data = f.read()
                if data:  # Check if file is not empty
                    self.telemetry = json.load(f)
                else:
                    self.telemetry = initial_telemetry
        except (FileNotFoundError, json.JSONDecodeError):
            self.telemetry = initial_telemetry
            with open('telemetry.json', 'w') as f:
                json.dump(initial_telemetry, f)

        self.telemetry = initial_telemetry
        self.movement_speed = 5
        self.max_x_position = 100000

    def validate_input(self) -> Union[bool, str]:
        if not isinstance(self.user_input, dict):
            return "Input must be a dictionary"
        
        required_keys = ["speed", "altitude", "movement"]
        for key in required_keys:
            if key not in self.user_input:
                return f"Missing required key: {key}"
                
            # if not isinstance(self.user_input[key], (int, str)):
            #     return f"'{key}' must be an integer or string"
                
            if key == "speed":
                if not isinstance(self.user_input[key], int):
                    return f"'speed' must be an integer, got {type(self.user_input[key]).__name__}"
                if not (0 <= self.user_input[key] <= 5):
                    return f"'speed' must be between 0 and 5, got {self.user_input[key]}"
                
            if key == "altitude" and not isinstance(self.user_input[key], int):
                return f"'altitude' must be an integer, got {type(self.user_input[key]).__name__}"
                
            if key == "movement":
                if not isinstance(self.user_input[key], str):
                    return f"'movement' must be a string"
                if self.user_input[key] not in ["fwd", "rev"]:
                    return f"'movement' must be one of ['fwd', 'rev'], got '{self.user_input[key]}'"
                
        return True

    def update_telemetry(self, user_input: Dict[str, Union[int, str]]) -> Dict:
        self.user_input = user_input
        validation_result = self.validate_input()
        if validation_result is not True:
            raise ValueError(f"Invalid input data: {validation_result}")
        
        self.speed = user_input.get("speed", 0)
        self.altitude_change = user_input.get("altitude", 0)
        self.movement = user_input.get("movement", None)
        
        # Update position based on movement
        if self.movement == "fwd":
            self.telemetry["x_position"] = self.telemetry["x_position"] + self.speed
        elif self.movement == "rev":
            self.telemetry["x_position"] = self.telemetry["x_position"] - self.speed

        # Update altitude
        if abs(self.altitude_change) > 0:
            self.telemetry["y_position"] = self.telemetry["y_position"] + self.altitude_change

        # Simulate battery drain
        self.telemetry["battery"] = self.telemetry["battery"] - (.5 * self.speed + abs(self.altitude_change) * 0.005) - 0.5
        # Random environmental changes
        self._update_environmental_conditions()
        self._check_drone_crash()
        self._update_data()
        return self.telemetry
    
    def _update_data(self):
        with open('telemetry.json', 'w') as f:
            json.dump(self.telemetry, f)


    def _update_environmental_conditions(self):
        #random changes in gyroscope values
        self.telemetry["gyroscope"] = [
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0)
        ]
        # Random wind changes
        self.telemetry["wind_speed"] = int(random.uniform(0, 100))
        # self.telemetry["wind_speed"] = int(max(0, min(100, self.telemetry["wind_speed"])))

        # Random dust changes
        self.telemetry["dust_level"] = int(random.uniform(0, 100))
        # self.telemetry["dust_level"] = int(max(0, min(100, self.telemetry["dust_level"])))

        # Random events
        if random.random() < 0.4:  # 40% chance of dust storm
            self.telemetry["dust_level"] = min(100, self.telemetry["dust_level"] + 60)
            self.telemetry["wind_speed"] = min(100, self.telemetry["wind_speed"] + 60)

        # Update sensor status based on conditions
        if self.telemetry["dust_level"] > 90 or self.telemetry["wind_speed"] > 90:
            self.telemetry["sensor_status"] = "RED"
        elif self.telemetry["dust_level"] > 60 or self.telemetry["wind_speed"] > 50:
            self.telemetry["sensor_status"] = "YELLOW"
        else:
            self.telemetry["sensor_status"] = "GREEN"

        # fix sensor status for now
        self.telemetry["sensor_status"] = "GREEN"

    def _check_drone_crash(self):
        if self.telemetry["battery"] <= 0:
            self.telemetry["battery"] = 0
            raise ValueError("Drone has crashed due to battery depletion.")
        if self.telemetry["y_position"] < 0:
            raise ValueError("Drone has crashed due to negative altitude.")
        if abs(self.telemetry["x_position"]) > self.max_x_position:
            raise ValueError("Drone has crashed due to exceeding max x position.")

# Example usage
if __name__ == "__main__":
    drone = DroneSimulator()
    
    # Example user input
    user_input = {
        "speed": 0,
        "altitude": 0,
        "movement": "fwd"
    }
    i = 0
    while (True):
        try:
            telemetry = drone.update_telemetry(user_input)
            print(json.dumps(telemetry, indent=3))
        except ValueError as e:
            print(e)
            break
        except KeyboardInterrupt:
            print("Simulation stopped.")
            break
        #add delay of 1sec
        i+=1
        time.sleep(0.1)

