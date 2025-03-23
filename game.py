# game.py
import pygame
import asyncio
import websockets
import json
import threading
import sys
import os

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
WIDTH, HEIGHT = 800, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (0, 100, 255)
GREEN = (0, 200, 0)
RED = (255, 0, 0)

# Server settings - update this with your Render URL
SERVER_URL = "https://virus-kuw5.onrender.com"  # Replace with your actual Render URL

# Fonts
TITLE_FONT = pygame.font.SysFont('arial', 50)
BUTTON_FONT = pygame.font.SysFont('arial', 30)
TEXT_FONT = pygame.font.SysFont('arial', 24)

# Game states
NAME_INPUT = 0
MAIN_MENU = 1
CREATE_LOBBY = 2
JOIN_LOBBY = 3
LOBBY = 4
CONNECTING = 5
ERROR = 6

class Button:
    def __init__(self, x, y, width, height, text, color=BLUE, hover_color=GREEN):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        
    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=5)
        
        text_surface = BUTTON_FONT.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
        
    def check_hover(self, pos):
        self.is_hovered = self.rect.collidepoint(pos)
        
    def is_clicked(self, pos, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(pos)
        return False

class InputBox:
    def __init__(self, x, y, w, h, text='', placeholder=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BLACK
        self.text = text
        self.placeholder = placeholder
        self.txt_surface = TEXT_FONT.render(text, True, BLACK)
        self.active = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = BLUE if self.active else BLACK
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = TEXT_FONT.render(self.text, True, BLACK)
        return False
        
    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, self.color, self.rect, 2)
        
        if self.text:
            screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        else:
            placeholder_surface = TEXT_FONT.render(self.placeholder, True, DARK_GRAY)
            screen.blit(placeholder_surface, (self.rect.x + 5, self.rect.y + 5))

class GameClient:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Multiplayer Lobby Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = NAME_INPUT
        self.error_message = ""
        
        # Player info
        self.player_name = ""
        self.lobby_code = ""
        self.players_in_lobby = []
        self.is_host = False
        
        # UI elements
        self.name_input = InputBox(WIDTH//2 - 150, HEIGHT//2, 300, 40, placeholder="Enter your name")
        self.code_input = InputBox(WIDTH//2 - 150, HEIGHT//2, 300, 40, placeholder="Enter lobby code")
        
        self.create_lobby_btn = Button(WIDTH//2 - 150, HEIGHT//2 - 60, 300, 50, "Create Lobby")
        self.join_lobby_btn = Button(WIDTH//2 - 150, HEIGHT//2 + 20, 300, 50, "Join Lobby")
        self.back_btn = Button(20, HEIGHT - 70, 100, 50, "Back")
        self.submit_btn = Button(WIDTH//2 - 50, HEIGHT//2 + 70, 100, 50, "Submit")
        self.retry_btn = Button(WIDTH//2 - 100, HEIGHT//2 + 50, 200, 50, "Retry Connection")
        
        # Network
        self.websocket = None
        self.connected = False
        self.connection_error = False
        
        # WebSocket communication thread
        self.ws_thread = None
    
    async def connect_to_server(self):
        self.state = CONNECTING
        try:
            self.websocket = await websockets.connect(SERVER_URL)
            self.connected = True
            self.connection_error = False
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            self.connected = False
            self.connection_error = True
            self.error_message = f"Failed to connect: {str(e)}"
            self.state = ERROR
            return False
    
    async def listen_to_server(self):
        while self.connected:
            try:
                data = await self.websocket.recv()
                msg = json.loads(data)
                
                if msg["type"] == "lobby_created":
                    self.lobby_code = msg["code"]
                    self.state = LOBBY
                    self.is_host = True
                elif msg["type"] == "lobby_joined":
                    self.state = LOBBY
                elif msg["type"] == "player_list":
                    self.players_in_lobby = msg["players"]
                elif msg["type"] == "join_failed":
                    print("Failed to join lobby: Invalid code")
                    self.state = MAIN_MENU
                    self.error_message = "Failed to join: Invalid lobby code"
                    self.state = ERROR
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                self.connected = False
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                self.connected = False
                self.error_message = f"Connection error: {str(e)}"
                self.state = ERROR
                break
    
    async def send_to_server(self, msg_dict):
        if self.connected:
            message = json.dumps(msg_dict)
            await self.websocket.send(message)
    
    async def create_lobby_async(self):
        if not self.connected:
            if not await self.connect_to_server():
                return
            
        await self.send_to_server({
            "type": "create_lobby",
            "name": self.player_name
        })
    
    async def join_lobby_async(self, code):
        if not self.connected:
            if not await self.connect_to_server():
                return
            
        self.lobby_code = code
        await self.send_to_server({
            "type": "join_lobby",
            "name": self.player_name,
            "code": code
        })
    
    def create_lobby(self):
        asyncio.run_coroutine_threadsafe(self.create_lobby_async(), self.loop)
    
    def join_lobby(self, code):
        asyncio.run_coroutine_threadsafe(self.join_lobby_async(code), self.loop)
    
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            # Handle button hovering
            if self.state == MAIN_MENU:
                self.create_lobby_btn.check_hover(mouse_pos)
                self.join_lobby_btn.check_hover(mouse_pos)
            elif self.state in [CREATE_LOBBY, JOIN_LOBBY]:
                self.back_btn.check_hover(mouse_pos)
                self.submit_btn.check_hover(mouse_pos)
            elif self.state == ERROR:
                self.retry_btn.check_hover(mouse_pos)
                self.back_btn.check_hover(mouse_pos)
            elif self.state == LOBBY:
                self.back_btn.check_hover(mouse_pos)
            
            # Handle button clicks
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == MAIN_MENU:
                    if self.create_lobby_btn.is_clicked(mouse_pos, event):
                        self.create_lobby()
                    elif self.join_lobby_btn.is_clicked(mouse_pos, event):
                        self.state = JOIN_LOBBY
                elif self.state == JOIN_LOBBY:
                    if self.back_btn.is_clicked(mouse_pos, event):
                        self.state = MAIN_MENU
                    elif self.submit_btn.is_clicked(mouse_pos, event):
                        self.join_lobby(self.code_input.text)
                elif self.state == ERROR:
                    if self.retry_btn.is_clicked(mouse_pos, event):
                        if self.lobby_code:
                            self.join_lobby(self.lobby_code)
                        else:
                            self.create_lobby()
                    elif self.back_btn.is_clicked(mouse_pos, event):
                        self.state = MAIN_MENU
                elif self.state == LOBBY:
                    if self.back_btn.is_clicked(mouse_pos, event):
                        self.state = MAIN_MENU
                        asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)
                
            # Handle input boxes
            if self.state == NAME_INPUT:
                if self.name_input.handle_event(event):
                    if self.name_input.text:
                        self.player_name = self.name_input.text
                        self.state = MAIN_MENU
            elif self.state == JOIN_LOBBY:
                self.code_input.handle_event(event)
    
    async def disconnect(self):
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
    
    def draw(self):
        self.screen.fill(WHITE)
        
        if self.state == NAME_INPUT:
            title = TITLE_FONT.render("Enter Your Name", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
            self.name_input.draw(self.screen)
            
        elif self.state == MAIN_MENU:
            title = TITLE_FONT.render(f"Welcome, {self.player_name}!", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
            
            self.create_lobby_btn.draw(self.screen)
            self.join_lobby_btn.draw(self.screen)
            
        elif self.state == JOIN_LOBBY:
            title = TITLE_FONT.render("Join a Lobby", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
            
            self.code_input.draw(self.screen)
            self.back_btn.draw(self.screen)
            self.submit_btn.draw(self.screen)
            
        elif self.state == CONNECTING:
            connecting_text = TITLE_FONT.render("Connecting...", True, BLACK)
            self.screen.blit(connecting_text, (WIDTH//2 - connecting_text.get_width()//2, HEIGHT//2))
            
        elif self.state == ERROR:
            error_title = TITLE_FONT.render("Connection Error", True, RED)
            self.screen.blit(error_title, (WIDTH//2 - error_title.get_width()//2, HEIGHT//4))
            
            error_text = TEXT_FONT.render(self.error_message, True, BLACK)
            self.screen.blit(error_text, (WIDTH//2 - error_text.get_width()//2, HEIGHT//3))
            
            self.retry_btn.draw(self.screen)
            self.back_btn.draw(self.screen)
            
        elif self.state == LOBBY:
            if self.is_host:
                title = TITLE_FONT.render(f"Lobby: {self.lobby_code}", True, BLACK)
            else:
                title = TITLE_FONT.render(f"Joined Lobby: {self.lobby_code}", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//4))
            
            # Display all players
            y_offset = HEIGHT//3
            players_title = BUTTON_FONT.render("Players in Lobby:", True, BLACK)
            self.screen.blit(players_title, (WIDTH//2 - players_title.get_width()//2, y_offset))
            y_offset += 40
            
            for player in self.players_in_lobby:
                player_text = TEXT_FONT.render(player, True, BLACK)
                self.screen.blit(player_text, (WIDTH//2 - player_text.get_width()//2, y_offset))
                y_offset += 30
                
            self.back_btn.draw(self.screen)
        
        pygame.display.flip()
    
    async def websocket_loop(self):
        while self.running:
            if self.connected:
                await self.listen_to_server()
            await asyncio.sleep(0.1)
    
    def pygame_loop(self):
        while self.running:
            self.clock.tick(60)
            self.handle_events()
            self.draw()
            
        # Clean up
        asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)
        pygame.quit()
    
    def start(self):
        # Create an event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Start the WebSocket thread
        self.ws_thread = threading.Thread(target=self.run_websocket_loop, daemon=True)
        self.ws_thread.start()
        
        # Start the Pygame loop (in the main thread)
        self.pygame_loop()
        
    def run_websocket_loop(self):
        # Run the WebSocket loop in the background thread
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.websocket_loop())
        self.loop.close()

def main():
    client = GameClient()
    client.start()

if __name__ == "__main__":
    main()