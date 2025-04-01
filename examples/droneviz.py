# visualizer.py
"""
Pygame visualization for the drone simulator client with enhanced telemetry box.
"""
import pygame
import asyncio
from vizclient import SimpleDroneClient

class DroneVisualizer:
    """Visualizes drone client state using Pygame."""
    
    def __init__(self, client: SimpleDroneClient):
        """Initialize visualizer with drone client."""
        self.client = client
        pygame.init()
        self.screen_width = 800
        self.screen_height = 400
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(f"Drone Simulator - Client {client.connection_id or 'Not Connected'}")
        self.clock = pygame.time.Clock()
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)
        self.DARK_GRAY = (50, 50, 50)
        self.LIGHT_GRAY = (200, 200, 200)
        self.BLUE = (0, 150, 255)
        
        # Map parameters
        self.map_scale = 5  # Pixels per unit
        self.telemetry_box_x = 10  # Top left of screen
        self.telemetry_box_y = 10
        self.telemetry_box_width = 260
        self.telemetry_box_height = 380
        
    def draw(self):
        """Draw the drone position and enhanced telemetry."""
        # Handle Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.client.running = False
                pygame.quit()
                return
                
        # Clear screen
        self.screen.fill(self.BLACK)
        
        if not self.client.telemetry:
            font = pygame.font.Font(None, 36)
            text = font.render("Waiting for telemetry...", True, self.WHITE)
            self.screen.blit(text, (self.screen_width // 2 - text.get_width() // 2, 
                                  self.screen_height // 2 - text.get_height() // 2))
        else:
            # Draw origin line (ground) with a gradient effect
            pygame.draw.line(self.screen, self.LIGHT_GRAY, 
                           (0, self.screen_height - 50),
                           (self.screen_width, self.screen_height - 50), 3)
            
            # Draw center line (x=0) with dashed effect
            for y in range(0, self.screen_height, 10):
                pygame.draw.line(self.screen, self.LIGHT_GRAY,
                               (self.screen_width // 2, y),
                               (self.screen_width // 2, y + 5), 1)
            
            # Calculate drone screen position
            x_pos = self.client.telemetry['x_position'] * self.map_scale + self.screen_width // 2
            y_pos = self.screen_height - 50 - (self.client.telemetry['y_position'] * self.map_scale)
            
            # Draw drone with a glow effect
            pygame.draw.circle(self.screen, self.WHITE,
                             (int(x_pos), int(y_pos)), 12, 2)  # Outer glow
            pygame.draw.circle(self.screen, self.RED,
                             (int(x_pos), int(y_pos)), 8)  # Inner circle
            
            # Draw telemetry box with background
            pygame.draw.rect(self.screen, self.DARK_GRAY,
                           (self.telemetry_box_x, self.telemetry_box_y,
                            self.telemetry_box_width, self.telemetry_box_height))
            pygame.draw.rect(self.screen, self.BLUE,
                           (self.telemetry_box_x, self.telemetry_box_y,
                            self.telemetry_box_width, self.telemetry_box_height), 2)
            
            # Render telemetry data
            font = pygame.font.Font(None, 22)
            small_font = pygame.font.Font(None, 18)
            y_offset = self.telemetry_box_y + 15
            line_height = 25
            
            # Title
            title = font.render("Telemetry Data", True, self.BLUE)
            self.screen.blit(title, (self.telemetry_box_x + 15, y_offset))
            y_offset += line_height * 1.5
            
            # Connection ID
            id_text = small_font.render(f"Client ID: {self.client.connection_id}", True, self.LIGHT_GRAY)
            self.screen.blit(id_text, (self.telemetry_box_x + 15, y_offset))
            y_offset += line_height
            
            # Telemetry
            telemetry = self.client.telemetry
            # Battery with bar
            battery_text = small_font.render(f"Battery: {telemetry['battery']:.1f}%", True, self.LIGHT_GRAY)
            self.screen.blit(battery_text, (self.telemetry_box_x + 15, y_offset))
            battery_width = int(telemetry['battery'] * 2)  # Scale to 200 pixels max
            battery_color = self.GREEN if telemetry['battery'] > 30 else self.YELLOW if telemetry['battery'] > 15 else self.RED
            pygame.draw.rect(self.screen, battery_color,
                           (self.telemetry_box_x + 15, y_offset + 20, battery_width, 10))
            pygame.draw.rect(self.screen, self.LIGHT_GRAY,
                           (self.telemetry_box_x + 15, y_offset + 20, 200, 10), 1)
            y_offset += line_height * 2
            
            # Rest of telemetry
            telem_items = [
                f"X Position: {telemetry['x_position']}",
                f"Y Position: {telemetry['y_position']}",
                f"Gyroscope: [{telemetry['gyroscope'][0]:.1f}, {telemetry['gyroscope'][1]:.1f}, {telemetry['gyroscope'][2]:.1f}]",
                f"Wind Speed: {telemetry['wind_speed']}",
                f"Dust Level: {telemetry['dust_level']}",
            ]
            
            for item in telem_items:
                text = small_font.render(item, True, self.LIGHT_GRAY)
                self.screen.blit(text, (self.telemetry_box_x + 15, y_offset))
                y_offset += line_height
            
            # Sensor Status with color
            sensor_status = telemetry['sensor_status']
            status_color = self.GREEN if sensor_status == "GREEN" else self.YELLOW if sensor_status == "YELLOW" else self.RED
            status_text = small_font.render(f"Sensor Status: {sensor_status}", True, status_color)
            self.screen.blit(status_text, (self.telemetry_box_x + 15, y_offset))
            y_offset += line_height * 1.5
            
            # Metrics (if available)
            if self.client.metrics:
                metrics = self.client.metrics
                metric_items = [
                    "Metrics:",
                    f"Iterations: {metrics['iterations']}",
                    f"Total Distance: {metrics['total_distance']:.1f}"
                ]
                for item in metric_items:
                    text = small_font.render(item, True, self.LIGHT_GRAY)
                    self.screen.blit(text, (self.telemetry_box_x + 15, y_offset))
                    y_offset += line_height
        
        # Update display
        pygame.display.flip()
        self.clock.tick(60)
        
    async def run(self):
        """Run visualization for the connected client."""
        websocket = await self.client.connect()
        if not websocket:
            print("Failed to connect, visualization will close")
            pygame.quit()
            return
            
        # Update window title with connection ID
        pygame.display.set_caption(f"Drone Simulator - Client {self.client.connection_id}")
        
        # Start client flight in async task
        client_task = asyncio.create_task(self.client.fly(websocket))
        
        # Run visualization loop
        while self.client.running:
            self.draw()
            await asyncio.sleep(0.01)  # Small delay to prevent overwhelming
            
        # Wait for client to finish
        await client_task
        pygame.quit()

async def main():
    """Run the visualizer with a client instance."""
    client = SimpleDroneClient()
    visualizer = DroneVisualizer(client)
    try:
        await visualizer.run()
    except KeyboardInterrupt:
        print("\nExample stopped by user")
    finally:
        pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())