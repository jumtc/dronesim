"""
Simple example client for the drone simulator.
Shows how to connect to the websocket server and control a drone.
"""
import asyncio
import json
import websockets
import time
import random
import logging
from typing import Dict, Any
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def decode_string(s: str) -> dict:

    pattern = (
        r"X-(?P<x>-?\d+)-"            # x position
        r"Y-(?P<y>-?\d+)-"            # y position
        r"BAT-(?P<battery>-?\d+(?:\.\d+)?)-"  # battery (float)
        r"GYR-\[(?P<gyro>[^\]]+)\]-"   # gyroscope values within brackets
        r"WIND-(?P<wind>-?\d+)-"       # wind speed
        r"DUST-(?P<dust>-?\d+)-"       # dust level
        r"SENS-(?P<sensor>[A-Z]+)"     # sensor status (expected GREEN, YELLOW, or RED)
    )
    
    match = re.match(pattern, s)
    if not match:
        raise ValueError("Input string does not match expected format.")
    
    # Process gyroscope values: split by comma and convert to floats.
    gyro_values = [float(val.strip()) for val in match.group("gyro").split(",")]
    
    result = {
        "x_position": int(match.group("x")),
        "y_position": int(match.group("y")),
        "battery": float(match.group("battery")),
        "gyroscope": gyro_values,
        "wind_speed": int(match.group("wind")),
        "dust_level": int(match.group("dust")),
        "sensor_status": match.group("sensor")
    }
    return result

class SimpleDroneClient:
    """A simple drone client example for hackathon participants."""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """Initialize the client with server URI."""
        self.uri = uri
        self.connection_id = None
        self.telemetry = None
        self.metrics = None
        self.running = True
        
    async def connect_and_fly(self):
        """Connect to the server and demonstrate flight patterns."""
        print(f"Connecting to {self.uri}...")
        
        try:
            # Configure ping_interval and ping_timeout for proper connection health monitoring
            async with websockets.connect(
                self.uri,
                ping_interval=20,   # Send ping every 20 seconds
                ping_timeout=10,    # Wait 10 seconds for pong response
                close_timeout=5     # Wait 5 seconds for close to complete
            ) as websocket:
                # Handle welcome message
                response = await websocket.recv()
                data = json.loads(response)
                self.connection_id = data.get("connection_id")
                print(f"Connected! ID: {self.connection_id}")
                print(f"Server says: {data.get('message')}")
                
                # Start with a simple flight demonstration
                await self.run_simple_demo(websocket)
                
                # Then show how to implement a battery-aware flight
                await self.battery_aware_flight(websocket)
                
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed abnormally: {e}")
            print("\nThe connection was closed unexpectedly. Possible reasons:")
            print("- Server crashed or restarted")
            print("- Network issues causing ping timeout")
            print("- Server closed the connection due to inactivity")
            
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed normally by the server")
            
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Is the server running at {self.uri}?")
            print("\nCannot connect to the server. Make sure:")
            print("1. The server is running (python run_server.py)")
            print("2. The server address and port are correct")
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
    
    async def send_command(self, websocket, speed, altitude, movement):
        """Send a command and receive telemetry updates."""
        command = {
            "speed": speed,
            "altitude": altitude,
            "movement": movement
        }
        
        # Log the command for debugging
        logger.info(f"Sending command: {command}")
        
        try:
            # Send the command
            await websocket.send(json.dumps(command))
            
            # Get the response
            response = await websocket.recv()
            data = json.loads(response)
            
            # Check if the drone has crashed
            if data.get("status") == "crashed":
                print(f"\n*** DRONE CRASHED: {data.get('message')} ***")
                print("Connection will be terminated.")
                
                # Update our local state one last time
                if "metrics" in data:
                    self.metrics = data["metrics"]
                
                # Show final telemetry
                if "final_telemetry" in data:
                    self.telemetry = data["final_telemetry"]
                    self.telemetry = decode_string(self.telemetry)
                
                print("\nFinal Flight Statistics:")
                print(f"Total distance traveled: {self.metrics.get('total_distance', 0)}")
                print(f"Successful flight iterations: {self.metrics.get('iterations', 0)}")
                
                return False
            
            # Update our local state for normal responses
            if data["status"] == "success":
                self.telemetry = data["telemetry"]
                self.metrics = data["metrics"]
                self.telemetry = decode_string(self.telemetry)
                return True
            else:
                print(f"Error: {data.get('message')}")
                return False
                     
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed while sending command: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
            
    async def run_simple_demo(self, websocket):
        """Run a simple flight demonstration."""
        print("\n=== Simple Flight Demo ===")
        print("This demo shows basic flight controls")
        
        # Take off and gain altitude
        print("\n1. Taking off...")
        if not await self.send_command(websocket, 0, 5, "fwd"):
            return
        print(f"   Altitude: {self.telemetry['y_position']}")
        await asyncio.sleep(1)
        
        # Fly forward
        print("\n2. Flying forward...")
        for speed in range(1, 6):
            if not await self.send_command(websocket, speed, 0, "fwd"):
                return
            print(f"   Speed: {speed}, Position: {self.telemetry['x_position']}")
            await asyncio.sleep(0.5)
        
        # Hover
        print("\n3. Hovering...")
        if not await self.send_command(websocket, 0, 0, "fwd"):
            return
        print(f"   Position: {self.telemetry['x_position']}, Battery: {self.telemetry['battery']:.1f}%")
        await asyncio.sleep(1)
        
        # Return back
        print("\n4. Returning...")
        for _ in range(3):
            if not await self.send_command(websocket, 3, 0, "rev"):
                return
            print(f"   Position: {self.telemetry['x_position']}")
            await asyncio.sleep(0.5)
        
        # Land
        print("\n5. Landing...")
        if not await self.send_command(websocket, 0, -5, "fwd"):
            return
        print(f"   Altitude: {self.telemetry['y_position']}")
        
        print("\nDemo completed!")
        print(f"Flight metrics: {self.metrics}")
        
    async def battery_aware_flight(self, websocket):
        """Demonstrate a battery-aware flight pattern."""
        print("\n=== Battery-Aware Flight Demo ===")
        print("This demo shows how to adjust flight based on battery level")
        
        # Reset flight state if needed
        if self.telemetry["y_position"] > 0:
            await self.send_command(websocket, 0, -self.telemetry["y_position"], "fwd")
        
        # Take off with moderate altitude
        print("\n1. Taking off with moderate altitude...")
        if not await self.send_command(websocket, 0, 3, "fwd"):
            return
            
        # Explore until battery gets low
        print("\n2. Exploring the area...")
        while self.telemetry["battery"] > 30:  # Safe battery threshold
            # Vary speed based on battery level
            max_speed = max(1, min(5, int(self.telemetry["battery"] / 20)))
            speed = random.randint(1, max_speed)
            
            # Decide movement direction
            if self.telemetry["x_position"] > 50:
                # Too far, come back
                movement = "rev"
            elif self.telemetry["x_position"] < -50:
                # Too far the other way, go forward
                movement = "fwd"
            else:
                # Within range, random direction
                movement = random.choice(["fwd", "rev"])
            
            # Small random altitude adjustments
            altitude_change = random.randint(-1, 1)
            
            # Send command and display state
            if not await self.send_command(websocket, speed, altitude_change, movement):
                return
                
            print(f"   Battery: {self.telemetry['battery']:.1f}%, " + 
                  f"Position: {self.telemetry['x_position']}, " + 
                  f"Altitude: {self.telemetry['y_position']}")
            
            await asyncio.sleep(0.5)
        
        # Return home when battery is low
        print("\n3. Battery low, returning home...")
        while abs(self.telemetry["x_position"]) > 5:
            # Determine direction to get back to home (0 position)
            movement = "rev" if self.telemetry["x_position"] > 0 else "fwd"
            
            # Use slower speed as battery is low
            speed = min(2, max(1, int(self.telemetry["battery"] / 25)))
            
            if not await self.send_command(websocket, speed, 0, movement):
                return
                
            print(f"   Returning home... Position: {self.telemetry['x_position']}, " + 
                  f"Battery: {self.telemetry['battery']:.1f}%")
            
            await asyncio.sleep(0.5)
        
        # Land safely
        print("\n4. Landing safely...")
        while self.telemetry["y_position"] > 0:
            descent_rate = min(2, self.telemetry["y_position"])
            if not await self.send_command(websocket, 0, -descent_rate, "fwd"):
                return
            print(f"   Altitude: {self.telemetry['y_position']}")
            await asyncio.sleep(0.5)
        
        print("\nBattery-aware mission completed!")
        print(f"Final battery: {self.telemetry['battery']:.1f}%")
        print(f"Flight metrics: {self.metrics}")

def main():
    """Run the example client."""
    import sys
    
    # Allow custom server URI from command line
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"
    
    # Create and run client
    client = SimpleDroneClient(uri)
    try:
        asyncio.run(client.connect_and_fly())
    except KeyboardInterrupt:
        print("\nExample stopped by user")

if __name__ == "__main__":
    main()