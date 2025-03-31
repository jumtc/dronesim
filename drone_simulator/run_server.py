"""
Standalone script to run the drone simulator server.
This makes it easier to start the server without importing modules.
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import DroneSimulatorServer

def main():
    """Run the drone simulator server."""
    print("Starting Drone Simulator Server...")
    print("Press Ctrl+C to stop the server")
    
    # Create and run the server
    server = DroneSimulatorServer(host="0.0.0.0", port=8765)
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\nServer stopped by user")

if __name__ == "__main__":
    main()