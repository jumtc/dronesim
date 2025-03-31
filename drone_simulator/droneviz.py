import asyncio
import json
import math
import websockets
import pygame
import sys
from typing import Dict, Any, Tuple

class DroneVisualization:
    """Visualization client for the drone simulator."""
    
    # Colors
    BACKGROUND = (50, 20, 20)  # Dark reddish-brown for Mars surface
    GRID_COLOR = (100, 50, 50)
    TEXT_COLOR = (255, 255, 255)
    DRONE_COLOR = (0, 200, 255)
    STATUS_COLORS = {
        "GREEN": (0, 255, 0),
        "YELLOW": (255, 255, 0),
        "RED": (255, 0, 0)
    }
    
    def __init__(self, uri: str = "ws://localhost:8765"):
        """Initialize the visualization client."""
        self.uri = uri
        self.connection_id = None
        self.telemetry = {
            "x_position": 0,
            "y_position": 0,
            "battery": 100.0,
            "gyroscope": [0.0, 0.0, 0.0],
            "wind_speed": 0,
            "dust_level": 0,
            "sensor_status": "GREEN"
        }  # Initialize with default values
        self.metrics = {
            "iterations": 0,
            "total_distance": 0.0
        }  # Initialize with default values
        self.running = True
        self.connected = False
        self.connection_error = None
        self.raw_messages = []  # Store raw messages for debugging
        
        # Initialize pygame
        pygame.init()
        self.width, self.height = 800, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Mars Drone Telemetry")
        self.font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 24, bold=True)
        self.clock = pygame.time.Clock()
        
        # Visualization parameters
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        self.scale = 5  # Pixels per unit
        self.max_trail_length = 50
        self.position_history = []
        
        print("Visualization initialized. Window should be visible now.")
        
    async def connect_and_visualize(self):
        """Connect to the server and visualize drone telemetry."""
        print(f"Connecting to drone server at {self.uri}...")
        
        # Start the event handling task
        event_task = asyncio.create_task(self.handle_events())
        
        # Start a task to keep drawing even before connection is established
        draw_task = asyncio.create_task(self.continuous_draw())
        
        try:
            print("Attempting websocket connection...")
            async with websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            ) as websocket:
                # Handle welcome message
                response = await websocket.recv()
                print(f"Raw welcome message: {response}")
                self.raw_messages.append(response)
                
                try:
                    data = json.loads(response)
                    self.connection_id = data.get("connection_id")
                    self.connected = True
                    print(f"Connected! ID: {self.connection_id}")
                except json.JSONDecodeError:
                    print(f"Error decoding welcome message: {response}")
                
                # Main visualization loop
                while self.running:
                    # Receive updates from the server
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        print(f"Raw message received: {response}")
                        self.raw_messages.append(response)
                        
                        try:
                            data = json.loads(response)
                            print(f"Parsed data status: {data.get('status', 'unknown')}")
                            
                            # Update local state
                            if data.get("status") == "success":
                                if "telemetry" in data:
                                    self.telemetry = data["telemetry"]
                                if "metrics" in data:
                                    self.metrics = data["metrics"]
                                
                                # Add current position to history
                                pos = (self.telemetry["x_position"], self.telemetry["y_position"])
                                self.position_history.append(pos)
                                # Keep history at a fixed length
                                if len(self.position_history) > self.max_trail_length:
                                    self.position_history.pop(0)
                            
                            elif data.get("status") == "crashed":
                                print(f"\n*** DRONE CRASHED: {data.get('message')} ***")
                                # Update our local state one last time
                                if "metrics" in data:
                                    self.metrics = data["metrics"]
                                if "final_telemetry" in data:
                                    self.telemetry = data["final_telemetry"]
                        except json.JSONDecodeError:
                            print(f"Error decoding message: {response}")
                    
                    except asyncio.TimeoutError:
                        # This just means no new data in the timeout period
                        pass
                    
                    except Exception as e:
                        print(f"Error processing websocket data: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Cancel the tasks when done
                event_task.cancel()
                draw_task.cancel()
                
        except websockets.exceptions.ConnectionClosedError as e:
            self.connection_error = f"Connection closed abnormally: {e}"
            print(self.connection_error)
        except websockets.exceptions.ConnectionClosedOK:
            self.connection_error = "Connection closed normally by the server"
            print(self.connection_error)
        except ConnectionRefusedError:
            self.connection_error = f"Connection refused. Is the server running at {self.uri}?"
            print(self.connection_error)
        except Exception as e:
            self.connection_error = f"Error: {e}"
            print(self.connection_error)
            import traceback
            traceback.print_exc()
        finally:
            # Let the visualization run a bit longer to display any error messages
            if self.connection_error:
                await asyncio.sleep(5)
            
            # Make sure tasks are cancelled
            event_task.cancel()
            draw_task.cancel()
            
            try:
                await event_task
                await draw_task
            except asyncio.CancelledError:
                pass
                
            # Print collected raw messages for debugging
            print("\n==== RAW SERVER MESSAGES ====")
            for i, msg in enumerate(self.raw_messages):
                print(f"Message {i+1}: {msg}")
            print("============================\n")
            
            pygame.quit()
            
    async def handle_events(self):
        """Handle pygame events in an async manner."""
        try:
            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        print("Quit event detected")
                        self.running = False
                        return
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            print("Escape key pressed")
                            self.running = False
                            return
                
                await asyncio.sleep(0.1)  # Check events 10 times per second
        except asyncio.CancelledError:
            print("Event handling task cancelled")
            return
            
    async def continuous_draw(self):
        """Continuously update the visualization regardless of websocket updates."""
        try:
            print("Starting continuous draw task")
            while self.running:
                self.draw_visualization()
                pygame.display.flip()
                await asyncio.sleep(0.03)  # ~30 FPS
                
                # Use tick after display update
                self.clock.tick(30)  # Limit to 30 FPS
        except asyncio.CancelledError:
            print("Draw task cancelled")
            return
        except Exception as e:
            print(f"Error in draw task: {e}")
            import traceback
            traceback.print_exc()
            
    def draw_visualization(self):
        """Draw the current state of the drone and telemetry."""
        # Fill background
        self.screen.fill(self.BACKGROUND)
        
        # Draw grid
        self.draw_grid()
        
        # Draw connection status
        self.draw_connection_status()
        
        # Draw position trail
        self.draw_position_trail()
        
        # Draw drone
        self.draw_drone()
        
        # Draw telemetry data
        self.draw_telemetry_panel()
        
        # Draw metrics
        self.draw_metrics_panel()
        
        # Draw message count for debugging
        msg_count = self.font.render(f"Messages received: {len(self.raw_messages)}", True, (255, 255, 255))
        self.screen.blit(msg_count, (10, self.height - 30))
        
    def draw_connection_status(self):
        """Draw connection status information."""
        status_rect = pygame.Rect(self.width - 260, self.height - 40, 250, 30)
        pygame.draw.rect(self.screen, (30, 30, 30), status_rect)
        
        if self.connected:
            status_text = f"Connected: ID {self.connection_id}"
            color = (0, 255, 0)  # Green
        else:
            if self.connection_error:
                status_text = "Connection Error"
                color = (255, 0, 0)  # Red
            else:
                status_text = "Connecting..."
                color = (255, 255, 0)  # Yellow
        
        status = self.font.render(status_text, True, color)
        self.screen.blit(status, (self.width - 250, self.height - 35))
        
    def draw_grid(self):
        """Draw coordinate grid."""
        # Draw horizontal line
        pygame.draw.line(
            self.screen, 
            self.GRID_COLOR, 
            (0, self.center_y), 
            (self.width, self.center_y), 
            1
        )
        
        # Draw vertical line
        pygame.draw.line(
            self.screen, 
            self.GRID_COLOR, 
            (self.center_x, 0), 
            (self.center_x, self.height), 
            1
        )
        
        # Draw grid lines and labels
        for x in range(-100, 101, 20):
            screen_x = self.center_x + x * self.scale
            if 0 <= screen_x <= self.width:
                pygame.draw.line(
                    self.screen, 
                    self.GRID_COLOR, 
                    (screen_x, 0), 
                    (screen_x, self.height), 
                    1
                )
                if x != 0:  # Don't draw 0 at origin, it's redundant
                    label = self.font.render(str(x), True, self.GRID_COLOR)
                    self.screen.blit(label, (screen_x + 5, self.center_y + 5))
        
        for y in range(-100, 101, 20):
            screen_y = self.center_y - y * self.scale  # y increases upward
            if 0 <= screen_y <= self.height:
                pygame.draw.line(
                    self.screen, 
                    self.GRID_COLOR, 
                    (0, screen_y), 
                    (self.width, screen_y), 
                    1
                )
                if y != 0:  # Don't draw 0 at origin, it's redundant
                    label = self.font.render(str(y), True, self.GRID_COLOR)
                    self.screen.blit(label, (self.center_x + 5, screen_y - 20))
        
        # Draw origin label
        origin = self.font.render("0", True, self.GRID_COLOR)
        self.screen.blit(origin, (self.center_x + 5, self.center_y + 5))
        
    def draw_position_trail(self):
        """Draw the drone's position history as a trail."""
        if len(self.position_history) < 2:
            return
            
        # Draw lines connecting previous positions
        for i in range(1, len(self.position_history)):
            prev_x, prev_y = self.position_history[i-1]
            curr_x, curr_y = self.position_history[i]
            
            # Convert to screen coordinates
            prev_screen_x = self.center_x + prev_x * self.scale
            prev_screen_y = self.center_y - prev_y * self.scale
            curr_screen_x = self.center_x + curr_x * self.scale
            curr_screen_y = self.center_y - curr_y * self.scale
            
            # Calculate alpha but ensure it's a valid RGB tuple (no alpha)
            alpha_factor = i / len(self.position_history)
            trail_color = (0, int(100 * alpha_factor), int(200 * alpha_factor))
            
            # Draw line segment
            pygame.draw.line(
                self.screen,
                trail_color,
                (prev_screen_x, prev_screen_y),
                (curr_screen_x, curr_screen_y),
                2
            )
            
    def draw_drone(self):
        """Draw the drone at its current position with orientation."""
        x = self.telemetry["x_position"]
        y = self.telemetry["y_position"]
        
        # Convert to screen coordinates
        screen_x = self.center_x + x * self.scale
        screen_y = self.center_y - y * self.scale  # y increases upward
        
        # Draw drone body (a circle with directional indicator)
        radius = 10
        pygame.draw.circle(self.screen, self.DRONE_COLOR, (int(screen_x), int(screen_y)), radius)
        
        # Draw altitude indicator (vertical line)
        if y > 0:
            pygame.draw.line(
                self.screen,
                self.DRONE_COLOR,
                (int(screen_x), int(screen_y)),
                (int(screen_x), int(self.center_y)),
                1
            )
            
        # Draw shadow on the ground
        ground_y = self.center_y  # Ground level
        shadow_radius = max(3, radius - y * 0.5)  # Shadow gets smaller with height
        pygame.draw.circle(
            self.screen, 
            (0, 0, 0),  # Black since alpha might not work
            (int(screen_x), int(ground_y)), 
            int(shadow_radius)
        )
        
        # Indicate sensor status with a colored ring
        if "sensor_status" in self.telemetry:
            status_color = self.STATUS_COLORS.get(self.telemetry["sensor_status"], self.DRONE_COLOR)
            pygame.draw.circle(self.screen, status_color, (int(screen_x), int(screen_y)), radius + 2, 2)
            
    def draw_telemetry_panel(self):
        """Draw a panel with current telemetry data."""
        # Create panel background
        panel_rect = pygame.Rect(10, 10, 250, 180)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 1)
        
        # Draw title
        title = self.title_font.render("DRONE TELEMETRY", True, self.TEXT_COLOR)
        self.screen.blit(title, (20, 15))
        
        # Draw telemetry data
        y_pos = 50
        line_height = 20
        
        telem_items = [
            f"Position: ({self.telemetry['x_position']:.1f}, {self.telemetry['y_position']:.1f})",
            f"Battery: {self.telemetry['battery']:.1f}%",
            f"Gyroscope: [{', '.join([f'{g:.2f}' for g in self.telemetry['gyroscope']])}]",
            f"Wind Speed: {self.telemetry['wind_speed']} km/h",
            f"Dust Level: {self.telemetry['dust_level']}%",
            f"Sensor Status: {self.telemetry['sensor_status']}"
        ]
        
        for item in telem_items:
            text = self.font.render(item, True, self.TEXT_COLOR)
            self.screen.blit(text, (20, y_pos))
            y_pos += line_height
            
        # Draw battery indicator
        self.draw_battery_indicator(20, 170, 210, 20)
        
    def draw_metrics_panel(self):
        """Draw a panel with flight metrics."""
        # Create panel background
        panel_rect = pygame.Rect(self.width - 260, 10, 250, 100)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 1)
        
        # Draw title
        title = self.title_font.render("FLIGHT METRICS", True, self.TEXT_COLOR)
        self.screen.blit(title, (self.width - 250, 15))
        
        # Draw metrics data
        y_pos = 50
        line_height = 20
        
        metric_items = [
            f"Iterations: {self.metrics['iterations']}",
            f"Total Distance: {self.metrics['total_distance']:.2f} m"
        ]
        
        for item in metric_items:
            text = self.font.render(item, True, self.TEXT_COLOR)
            self.screen.blit(text, (self.width - 250, y_pos))
            y_pos += line_height
            
    def draw_battery_indicator(self, x, y, width, height):
        """Draw a visual battery indicator."""
        # Draw battery outline
        bat_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, self.TEXT_COLOR, bat_rect, 1)
        
        # Draw battery terminal
        term_rect = pygame.Rect(x + width, y + height//4, 5, height//2)
        pygame.draw.rect(self.screen, self.TEXT_COLOR, term_rect)
        
        # Draw battery level
        level_width = int((width - 4) * (self.telemetry["battery"] / 100))
        level_rect = pygame.Rect(x + 2, y + 2, level_width, height - 4)
        
        # Color based on battery level
        if self.telemetry["battery"] > 50:
            level_color = (0, 255, 0)  # Green
        elif self.telemetry["battery"] > 20:
            level_color = (255, 255, 0)  # Yellow
        else:
            level_color = (255, 0, 0)  # Red
            
        pygame.draw.rect(self.screen, level_color, level_rect)

def main():
    """Run the visualization client."""
    import sys
    
    # Allow custom server URI from command line
    uri = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8765"
    
    print(f"Starting Mars Drone Visualization for {uri}")
    print(f"Python version: {sys.version}")
    print(f"Pygame version: {pygame.version.ver}")
    
    # Create and run visualization
    viz = DroneVisualization(uri)
    try:
        asyncio.run(viz.connect_and_visualize())
    except KeyboardInterrupt:
        print("\nVisualization stopped by user")
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        print("Visualization ended")

if __name__ == "__main__":
    main()