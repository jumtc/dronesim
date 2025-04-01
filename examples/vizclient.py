# drone_client.py
"""
Simple example client for the drone simulator.
Handles connection and control logic.
"""
import asyncio
import json
import websockets
import time
import random
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class SimpleDroneClient:
    """A simple drone client example."""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """Initialize the client with server URI."""
        self.uri = uri
        self.connection_id = None
        self.telemetry = None
        self.metrics = None
        self.running = True
        self.websocket = None
        
    async def connect(self):
        """Connect to the server and return the websocket."""
        print(f"Connecting to {self.uri}...")
        
        try:
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            response = await self.websocket.recv()
            data = json.loads(response)
            self.connection_id = data.get("connection_id")
            print(f"Connected! ID: {self.connection_id}")
            print(f"Server says: {data.get('message')}")
            return self.websocket
            
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed abnormally: {e}")
            print("\nThe connection was closed unexpectedly.")
            return None
            
        except ConnectionRefusedError:
            logger.error(f"Connection refused. Is the server running at {self.uri}?")
            print("\nCannot connect to the server.")
            return None
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return None
    
    async def fly(self, websocket):
        """Demonstrate flight patterns using the provided websocket."""
        if not websocket:
            return
            
        try:
            await self.run_simple_demo(websocket)
            await self.battery_aware_flight(websocket)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info("Connection closed normally by the server")
        finally:
            await websocket.close()
    
    async def send_command(self, websocket, speed, altitude, movement):
        """Send a command and receive telemetry updates."""
        command = {
            "speed": speed,
            "altitude": altitude,
            "movement": movement
        }
        
        logger.info(f"Sending command: {command}")
        
        try:
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("status") == "crashed":
                print(f"\n*** DRONE CRASHED: {data.get('message')} ***")
                if "metrics" in data:
                    self.metrics = data["metrics"]
                if "final_telemetry" in data:
                    self.telemetry = data["final_telemetry"]
                print("\nFinal Flight Statistics:")
                print(f"Total distance traveled: {self.metrics.get('total_distance', 0)}")
                print(f"Successful flight iterations: {self.metrics.get('iterations', 0)}")
                return False
            
            if data["status"] == "success":
                self.telemetry = data["telemetry"]
                self.metrics = data["metrics"]
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
        print("Watch the Pygame window for drone movement")
        
        print("\n1. Taking off...")
        if not await self.send_command(websocket, 0, 5, "fwd"):
            return
        await asyncio.sleep(1)
        
        print("\n2. Flying forward...")
        for speed in range(1, 6):
            if not await self.send_command(websocket, speed, 0, "fwd"):
                return
            await asyncio.sleep(0.5)
        
        print("\n3. Hovering...")
        if not await self.send_command(websocket, 0, 0, "fwd"):
            return
        await asyncio.sleep(1)
        
        print("\n4. Returning...")
        for _ in range(3):
            if not await self.send_command(websocket, 3, 0, "rev"):
                return
            await asyncio.sleep(0.5)
        
        print("\n5. Landing...")
        if not await self.send_command(websocket, 0, -5, "fwd"):
            return
        
        print("\nDemo completed!")
        print(f"Flight metrics: {self.metrics}")
        
    async def battery_aware_flight(self, websocket):
        """Demonstrate a battery-aware flight pattern."""
        print("\n=== Battery-Aware Flight Demo ===")
        print("Watch the green bar for battery level")
        
        if self.telemetry and self.telemetry["y_position"] > 0:
            await self.send_command(websocket, 0, -self.telemetry["y_position"], "fwd")
        
        print("\n1. Taking off with moderate altitude...")
        if not await self.send_command(websocket, 0, 3, "fwd"):
            return
            
        print("\n2. Exploring the area...")
        while self.running and self.telemetry and self.telemetry["battery"] > 30:
            max_speed = max(1, min(5, int(self.telemetry["battery"] / 20)))
            speed = random.randint(1, max_speed)
            movement = "rev" if self.telemetry["x_position"] > 50 else "fwd" if self.telemetry["x_position"] < -50 else random.choice(["fwd", "rev"])
            altitude_change = random.randint(-1, 1)
            
            if not await self.send_command(websocket, speed, altitude_change, movement):
                return
            await asyncio.sleep(0.5)
        
        print("\n3. Battery low, returning home...")
        while self.running and self.telemetry and abs(self.telemetry["x_position"]) > 5:
            movement = "rev" if self.telemetry["x_position"] > 0 else "fwd"
            speed = min(2, max(1, int(self.telemetry["battery"] / 25)))
            
            if not await self.send_command(websocket, speed, 0, movement):
                return
            await asyncio.sleep(0.5)
        
        print("\n4. Landing safely...")
        while self.running and self.telemetry and self.telemetry["y_position"] > 0:
            descent_rate = min(2, self.telemetry["y_position"])
            if not await self.send_command(websocket, 0, -descent_rate, "fwd"):
                return
            await asyncio.sleep(0.5)
        
        print("\nBattery-aware mission completed!")
        if self.telemetry:
            print(f"Final battery: {self.telemetry['battery']:.1f}%")
        print(f"Flight metrics: {self.metrics}")

async def main():
    """Run the example client."""
    import sys
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"
    client = SimpleDroneClient(uri)
    websocket = await client.connect()
    if websocket:
        await client.fly(websocket)

if __name__ == "__main__":
    asyncio.run(main())