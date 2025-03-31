"""WebSocket server for drone simulator."""
import asyncio
import json
import logging
import uuid
import time
from typing import Dict, Set, Any
import websockets
from websockets.server import WebSocketServerProtocol
from drone import DroneSimulator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class DroneSimulatorServer:
    """WebSocket server to manage multiple drone simulator sessions."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize the server."""
        self.host = host
        self.port = port
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.drones: Dict[str, DroneSimulator] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.last_activity: Dict[str, float] = {}  # Track last activity time for each connection

    async def register(self, websocket: WebSocketServerProtocol) -> str:
        """Register a new client connection."""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        self.drones[connection_id] = DroneSimulator(f"telemetry_{connection_id}.json")
        self.metrics[connection_id] = {
            "iterations": 0,
            "total_distance": 0,
            "connection_time": 0,
            "last_position": 0,
        }
        self.last_activity[connection_id] = time.time()
        logger.info(f"New client connected: {connection_id}")
        return connection_id

    async def unregister(self, connection_id: str) -> None:
        """Unregister a client connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.drones:
            del self.drones[connection_id]
        if connection_id in self.metrics:
            del self.metrics[connection_id]
        if connection_id in self.last_activity:
            del self.last_activity[connection_id]
        logger.info(f"Client disconnected: {connection_id}")

    async def handle_drone_command(self, connection_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a drone command and update metrics."""
        drone = self.drones[connection_id]
        metrics = self.metrics[connection_id]
        
        # Update last activity time
        self.last_activity[connection_id] = time.time()
        
        try:
            # Get previous position for distance calculation
            prev_position = drone.telemetry["x_position"]
            
            # Update drone telemetry based on user input
            telemetry = drone.update_telemetry(data)
            
            # Calculate metrics
            if data.get("speed", 0) != 0:
                metrics["iterations"] += 1
                distance_traveled = abs(telemetry["x_position"] - prev_position)
                metrics["total_distance"] += distance_traveled
            
            metrics["last_position"] = telemetry["x_position"]
            
            # Include metrics in the response
            response = {
                "status": "success",
                "telemetry": telemetry,
                "metrics": {
                    "iterations": metrics["iterations"],
                    "total_distance": metrics["total_distance"]
                }
            }
            return response
            
        except ValueError as e:
            crash_message = str(e)
            logger.warning(f"Drone crashed for {connection_id}: {crash_message}")
            
            # Create a detailed crash response
            return {
                "status": "crashed",  # Changed from "error" to "crashed"
                "message": crash_message,
                "metrics": {
                    "iterations": metrics["iterations"],
                    "total_distance": metrics["total_distance"]
                },
                "final_telemetry": drone.telemetry,
                "connection_terminated": True  # Signal to client that connection should end
            }

    async def handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a client connection."""
        connection_id = await self.register(websocket)
        
        try:
            # Send initial connection message
            await websocket.send(json.dumps({
                "status": "connected",
                "connection_id": connection_id,
                "message": "Welcome to the Drone Simulator! Send commands to control your drone."
            }))
            
            # Start heartbeat task for this connection
            heartbeat_task = asyncio.create_task(self.connection_heartbeat(connection_id, websocket))
            
            # Process messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received from {connection_id}: {data}")
                    
                    # Update last activity time
                    self.last_activity[connection_id] = time.time()
                    
                    response = await self.handle_drone_command(connection_id, data)
                    await websocket.send(json.dumps(response))
                    
                    # If the drone has crashed, terminate the connection
                    if response.get("status") == "crashed" and response.get("connection_terminated", False):
                        logger.info(f"Terminating connection for {connection_id} due to drone crash")
                        await websocket.close(code=1000, reason=f"Drone crashed: {response.get('message')}")
                        break
                    
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Invalid JSON format"
                    }))
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed for {connection_id}: {e}")
        except Exception as e:
            logger.error(f"Error handling connection {connection_id}: {e}")
        finally:
            # Cancel heartbeat task
            if 'heartbeat_task' in locals() and not heartbeat_task.done():
                heartbeat_task.cancel()
                
            await self.unregister(connection_id)

    async def connection_heartbeat(self, connection_id: str, websocket: WebSocketServerProtocol) -> None:
        """Send periodic pings to keep the connection alive."""
        try:
            while connection_id in self.connections:
                # Send a ping to check the connection
                pong_waiter = await websocket.ping()
                try:
                    await asyncio.wait_for(pong_waiter, timeout=10)
                    # Ping successful, connection is alive
                except asyncio.TimeoutError:
                    logger.warning(f"Ping timeout for {connection_id}, closing connection")
                    # Close connection with status code 1011 (internal error)
                    await websocket.close(code=1011, reason="Ping timeout")
                    break
                
                # Check for inactivity
                current_time = time.time()
                last_active = self.last_activity.get(connection_id, 0)
                if current_time - last_active > 120:  # 2 minutes inactivity timeout
                    logger.warning(f"Client {connection_id} inactive for too long, closing connection")
                    await websocket.send(json.dumps({
                        "status": "error",
                        "message": "Connection closed due to inactivity",
                    }))
                    await websocket.close(code=1000, reason="Inactivity timeout")
                    break
                
                # Wait before next ping
                await asyncio.sleep(30)  # Send ping every 30 seconds
                
        except asyncio.CancelledError:
            # Task was cancelled, that's okay
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat for {connection_id}: {e}")

    async def start_server(self) -> None:
        """Start the WebSocket server."""
        # Configure server with ping_interval and ping_timeout
        server = await websockets.serve(
            self.handle_connection, 
            self.host, 
            self.port,
            ping_interval=30,  # Send ping every 30 seconds
            ping_timeout=10,    # Wait 10 seconds for pong response
            max_size=10_485_760  # 10MB max message size (default is 1MB)
        )
        
        logger.info(f"Server started on ws://{self.host}:{self.port}")
        
        # Keep server running
        await asyncio.Future()  # Run forever


def main() -> None:
    """Start the drone simulator server."""
    server = DroneSimulatorServer()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()