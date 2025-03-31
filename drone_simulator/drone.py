"""Drone simulator main class."""
from typing import Dict, Union, Any
from validators import validate_drone_input
from telemetry import TelemetryManager
from environment import EnvironmentSimulator

class DroneSimulator:
    """Simulates drone flight and telemetry."""
    
    def __init__(self, telemetry_file: str = 'telemetry.json'):
        """Initialize drone simulator."""
        self.telemetry_manager = TelemetryManager(telemetry_file)
        self.telemetry = self.telemetry_manager.get_telemetry()
        self.movement_speed = 5
        self.max_x_position = 100000
        self.user_input = None
        self.iteration_count = 0
        self.total_distance = 0
        self.crashed = False
        self.crash_reason = None

    def validate_input(self) -> Union[bool, str]:
        """Validate user input."""
        return validate_drone_input(self.user_input)

    def update_telemetry(self, user_input: Dict[str, Union[int, str]]) -> Dict:
        """Update drone telemetry based on user input."""
        # If drone is already crashed, don't process new commands
        if self.crashed:
            raise ValueError(f"Drone has crashed: {self.crash_reason}. Cannot accept new commands.")
            
        self.user_input = user_input
        validation_result = self.validate_input()
        if validation_result is not True:
            raise ValueError(f"Invalid input data: {validation_result}")
        
        # Store previous position for distance calculation
        prev_x_position = self.telemetry["x_position"]
        
        try:
            self._update_position()
            self._update_battery()
            self._update_environmental_conditions()
            self._check_drone_crash()
            
            # Calculate distance traveled
            distance = abs(self.telemetry["x_position"] - prev_x_position)
            self.total_distance += distance
            
            # Count iterations when speed is not zero
            if user_input.get("speed", 0) != 0:
                self.iteration_count += 1
            
            # Save updated telemetry
            self.telemetry_manager.update_telemetry(self.telemetry)
            
            return self.telemetry
            
        except ValueError as e:
            # Mark the drone as crashed and save the crash reason
            self.crashed = True
            self.crash_reason = str(e)
            
            # Save the final state
            self.telemetry_manager.update_telemetry(self.telemetry)
            
            # Re-raise the exception
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get drone performance metrics."""
        metrics = {
            "iterations": self.iteration_count,
            "total_distance": self.total_distance
        }
        
        if self.crashed:
            metrics["crashed"] = True
            metrics["crash_reason"] = self.crash_reason
            
        return metrics
    
    def reset(self) -> None:
        """Reset the drone to its initial state."""
        self.telemetry = {
            "x_position": 0,
            "y_position": 0, 
            "battery": 100,
            "gyroscope": [0.0, 0.0, 0.0],
            "wind_speed": 0,
            "dust_level": 0,
            "sensor_status": "GREEN"
        }
        self.telemetry_manager.update_telemetry(self.telemetry)
        self.iteration_count = 0
        self.total_distance = 0
        self.crashed = False
        self.crash_reason = None
    
    def _update_position(self) -> None:
        """Update drone position based on user input."""
        speed = self.user_input.get("speed", 0)
        altitude_change = self.user_input.get("altitude", 0)
        movement = self.user_input.get("movement", None)
        
        # Update position based on movement
        if movement == "fwd":
            self.telemetry["x_position"] = self.telemetry["x_position"] + speed
        elif movement == "rev":
            self.telemetry["x_position"] = self.telemetry["x_position"] - speed

        # Update altitude
        if abs(altitude_change) > 0:
            self.telemetry["y_position"] = self.telemetry["y_position"] + altitude_change
    
    def _update_battery(self) -> None:
        """Update battery level based on drone operations."""
        speed = self.user_input.get("speed", 0)
        altitude_change = self.user_input.get("altitude", 0)
        
        # Simulate battery drain
        self.telemetry["battery"] = self.telemetry["battery"] - (.5 * speed + abs(altitude_change) * 0.005) - 0.5

    def _update_environmental_conditions(self) -> None:
        """Update environmental conditions affecting the drone."""
        self.telemetry = EnvironmentSimulator.simulate_environmental_conditions(self.telemetry)

    def _check_drone_crash(self) -> None:
        """Check if drone has crashed based on current telemetry."""
        if self.telemetry["battery"] <= 0:
            self.telemetry["battery"] = 0
            raise ValueError("Drone has crashed due to battery depletion.")
            
        if self.telemetry["y_position"] < 0:
            self.telemetry["y_position"] = 0  # Reset to ground level
            raise ValueError("Drone has crashed due to negative altitude.")
            
        if abs(self.telemetry["x_position"]) > self.max_x_position:
            raise ValueError("Drone has crashed due to exceeding max x position.")