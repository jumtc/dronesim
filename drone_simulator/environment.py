"""Environmental simulation for drone simulator."""
import random
from typing import Dict, Any, List

class EnvironmentSimulator:
    """Simulates environmental conditions affecting the drone."""
    
    @staticmethod
    def generate_gyroscope_values() -> List[float]:
        """Generate random gyroscope values."""
        return [
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0),
            random.uniform(-1.0, 1.0)
        ]
    
    @staticmethod
    def simulate_environmental_conditions(telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Update telemetry with simulated environmental conditions."""
        # Copy telemetry to avoid modifying the original
        updated_telemetry = telemetry.copy()
        
        # Update gyroscope values
        updated_telemetry["gyroscope"] = EnvironmentSimulator.generate_gyroscope_values()
        
        # Random wind changes
        updated_telemetry["wind_speed"] = int(random.uniform(0, 100))
        
        # Random dust changes
        updated_telemetry["dust_level"] = int(random.uniform(0, 100))
        
        # Random events
        if random.random() < 0.4:  # 40% chance of dust storm
            updated_telemetry["dust_level"] = min(100, updated_telemetry["dust_level"] + 60)
            updated_telemetry["wind_speed"] = min(100, updated_telemetry["wind_speed"] + 60)
        
        # Update sensor status based on conditions
        if updated_telemetry["dust_level"] > 90 or updated_telemetry["wind_speed"] > 90:
            updated_telemetry["sensor_status"] = "RED"
        elif updated_telemetry["dust_level"] > 60 or updated_telemetry["wind_speed"] > 50:
            updated_telemetry["sensor_status"] = "YELLOW"
        else:
            updated_telemetry["sensor_status"] = "GREEN"
        
        # Fixed sensor status for now
        updated_telemetry["sensor_status"] = "GREEN"
        
        return updated_telemetry