"""Test client for drone simulator WebSocket server."""
import asyncio
import json
import logging
import sys
import websockets
import time
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class DroneClient:
    """WebSocket client for testing the drone simulator."""
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """Initialize the client."""
        self.uri = uri
        self.connection_id = None
        self.telemetry = None
        self.metrics = None
    
    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        print(f"Attempting to connect to {self.uri}...")
        print("Make sure the server is running (python run_server.py)")
        
        try:
            # Configure ping_interval and ping_timeout properly
            async with websockets.connect(
                self.uri, 
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,   # Wait 10 seconds for pong response
                close_timeout=5    # Wait 5 seconds for close to complete
            ) as websocket:
                # Receive welcome message
                response = await websocket.recv()
                data = json.loads(response)
                self.connection_id = data.get("connection_id")
                logger.info(f"Connected: {data['message']}")
                logger.info(f"Connection ID: {self.connection_id}")
                
                # Interactive control of the drone
                await self.interactive_control(websocket)
                
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
            print("\nTroubleshooting steps:")
            print("1. Make sure the server is running: python run_server.py")
            print("2. Check if the server is listening on the correct address")
            print("3. Check if there are any firewalls blocking the connection")
            print("4. Try 'ws://127.0.0.1:8765' instead of 'ws://localhost:8765'")
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
    
    async def send_command(self, websocket, speed: int, altitude: int, movement: str) -> Optional[Dict[str, Any]]:
        """Send a command to the drone server and return the response."""
        try:
            data = {
                "speed": speed,
                "altitude": altitude,
                "movement": movement
            }
            logger.info(f"Sending command: {data}")
            await websocket.send(json.dumps(data))
            
            response = await websocket.recv()
            data = json.loads(response)
            
            # Check if the drone has crashed
            if data.get("status") == "crashed":
                print(f"\n*** DRONE CRASHED: {data.get('message')} ***")
                print("Connection will be terminated.")
                
                # Update metrics one last time
                if "metrics" in data:
                    self.metrics = data["metrics"]
                
                # Show final telemetry
                if "final_telemetry" in data:
                    self.telemetry = data["final_telemetry"]
                    self.display_status()
                
                print("\nFinal Flight Statistics:")
                print(f"Total distance traveled: {self.metrics.get('total_distance', 0)}")
                print(f"Successful flight iterations: {self.metrics.get('iterations', 0)}")
                print("\nConnection terminated due to crash")
                
                # Return None to indicate a crash occurred
                return None
                
            return data
            
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"Connection closed while sending command: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    async def interactive_control(self, websocket) -> None:
        """Interactively control the drone through the console."""
        print("\n==== Drone Simulator Interactive Console ====")
        print("Commands: 'exit' to quit, 'help' for instructions, 'auto' for auto pilot")
        print("Input format: speed,altitude,movement (e.g., '2,0,fwd')")
        print("Keep-alive pings are sent automatically every 20 seconds")
        
        help_text = """
Commands:
- speed: integer 0-5
- altitude: positive or negative integer
- movement: 'fwd' or 'rev'

Examples:
- 3,0,fwd   # Move forward at speed 3
- 0,5,fwd   # Gain altitude by 5 units
- 2,-1,rev  # Move backward and descend 1 unit
- auto      # Start auto pilot mode
- exit      # Exit the client
- help      # Show this help message
- status    # Show current telemetry and metrics
- ping      # Send a keep-alive command (0,0,fwd)
        """
        
        try:
            while True:
                command = input("\nEnter command: ")
                
                if command.lower() == 'exit':
                    break
                    
                if command.lower() == 'help':
                    print(help_text)
                    continue
                
                if command.lower() == 'status' and self.telemetry:
                    self.display_status()
                    continue
                
                if command.lower() == 'auto':
                    await self.auto_pilot(websocket)
                    continue
                    
                if command.lower() == 'ping':
                    print("Sending keep-alive ping...")
                    data = await self.send_command(websocket, 0, 0, "fwd")
                    if data:
                        self.update_state(data)
                        print("Keep-alive successful")
                    continue
                
                try:
                    # Parse command
                    parts = command.split(',')
                    if len(parts) != 3:
                        print("Invalid command format. Use: speed,altitude,movement")
                        continue
                        
                    speed = int(parts[0])
                    altitude = int(parts[1])
                    movement = parts[2].strip()
                    
                    # Send command
                    data = await self.send_command(websocket, speed, altitude, movement)
                    if data:
                        self.update_state(data)
                        self.display_status()
                        
                except ValueError as e:
                    print(f"Invalid input format: {e}")
                    print("Use format: speed,altitude,movement (e.g., '2,0,fwd')")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection to server was closed")
    
    async def auto_pilot(self, websocket) -> None:
        """Run an automated test sequence."""
        print("\n==== Auto Pilot Mode ====")
        print("Press Ctrl+C to exit auto pilot")
        
        try:
            # Test sequence
            actions = [
                (2, 0, "fwd"),   # Move forward
                (3, 1, "fwd"),   # Move forward and gain altitude
                (4, 2, "fwd"),   # Move forward faster and gain more altitude
                (5, 0, "fwd"),   # Max speed
                (3, -1, "fwd"),  # Slow down and descend
                (2, 0, "rev"),   # Reverse
                (3, 0, "rev"),   # Reverse faster
                (1, 1, "fwd"),   # Slow forward and gain altitude
                (0, 0, "fwd"),   # Stop
            ]
            
            for speed, altitude, movement in actions:
                print(f"\nSending command: speed={speed}, altitude={altitude}, movement={movement}")
                data = await self.send_command(websocket, speed, altitude, movement)
                if data:
                    self.update_state(data)
                    self.display_status()
                else:
                    print("Failed to send command or receive response")
                    return
                    
                await asyncio.sleep(1)  # Pause between commands
                
            print("\nAuto pilot sequence completed")
            
        except KeyboardInterrupt:
            print("\nAuto pilot stopped")
            
        except websockets.exceptions.ConnectionClosed:
            print("\nConnection to server was closed")
    
    def update_state(self, data: Dict[str, Any]) -> None:
        """Update client state with server response."""
        if data["status"] == "success":
            self.telemetry = data["telemetry"]
            self.metrics = data["metrics"]
        else:
            print(f"\nError: {data['message']}")
            if "metrics" in data:
                self.metrics = data["metrics"]
    
    def display_status(self) -> None:
        """Display current telemetry and metrics."""
        if not self.telemetry:
            print("No telemetry data available yet")
            return
            
        print("\n----- Telemetry -----")
        print(f"Position: ({self.telemetry['x_position']}, {self.telemetry['y_position']})")
        print(f"Battery: {self.telemetry['battery']:.1f}%")
        print(f"Wind Speed: {self.telemetry['wind_speed']}%")
        print(f"Dust Level: {self.telemetry['dust_level']}%")
        print(f"Sensor Status: {self.telemetry['sensor_status']}")
        print(f"Gyroscope: {self.telemetry['gyroscope']}")
        
        print("\n----- Metrics -----")
        print(f"Successful Iterations: {self.metrics['iterations']}")
        print(f"Total Distance: {self.metrics['total_distance']}")

def main() -> None:
    """Start the drone client."""
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"
    client = DroneClient(uri)
    try:
        asyncio.run(client.connect())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")

if __name__ == "__main__":
    main()