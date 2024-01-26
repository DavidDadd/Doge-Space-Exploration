import socket
import json
import pygame
import math
import tkinter as tk
from tkinter import messagebox, Label
import qrcode
from PIL import Image, ImageTk
import sys
import threading
import os

WIDTH, HEIGHT = 800, 600
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (180, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
GREEN = (0, 150, 0)
DOGE_COLOR = (255, 215, 0)

class LoginWindow:
    def __init__(self, submit_callback):
        self.submit_callback = submit_callback
        self.root = tk.Tk()
        self.root.title("Login/Signup")

        # Centering the window
        window_width = 400
        window_height = 250
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width / 2 - window_width / 2)
        center_y = int(screen_height / 2 - window_height / 2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        tk.Label(self.root, text="Username:").pack()
        self.username_entry = tk.Entry(self.root, width=50)
        self.username_entry.pack()

        tk.Label(self.root, text="Password:").pack()
        self.password_entry = tk.Entry(self.root, show="*", width=50)
        self.password_entry.pack()

        tk.Label(self.root, text="Confirm Password:").pack()
        self.confirm_password_entry = tk.Entry(self.root, show="*", width=50)
        self.confirm_password_entry.pack()

        tk.Label(self.root, text="Dogecoin Withdraw Address:").pack()
        self.withdraw_address_entry = tk.Entry(self.root, width=50)
        self.withdraw_address_entry.pack()

        tk.Button(self.root, text="Submit", command=self.on_submit).pack()

    def on_submit(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        withdraw_address = self.withdraw_address_entry.get()

        # Client-side validation
        if not (4 < len(username) <= 15 and username.replace("_", "").isalnum()):
            messagebox.showerror("Error", "Invalid username. Username must be 5-15 characters long and can contain letters, numbers, and underscores.")
            return

        if len(password) > 20 or len(password) < 10 or not all(ord(c) < 128 for c in password):
            messagebox.showerror("Error", "Invalid password. Password must be at least 10-20 characters long and only contain ASCII characters.")
            return

        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.")
            return

        if not (withdraw_address.startswith('D') and len(withdraw_address) == 34):
            messagebox.showerror("Error", "Invalid Dogecoin withdraw address. It must start with 'D' and be 34 characters long.")
            return

        self.submit_callback(username, password, withdraw_address)
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.root.destroy()
        sys.exit() 
        
class Button:
    def __init__(self, x, y, width, height, text='', color=(0, 255, 0), hover_color=(50, 200, 50), font_size=30, disabled=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font_size = font_size
        self.disabled = disabled 

    def draw(self, win, outline=None):
        if outline:
            pygame.draw.rect(win, outline, (self.x-2, self.y-2, self.width+4, self.height+4), 0)
        
        pygame.draw.rect(win, self.color, (self.x, self.y, self.width, self.height), 0)
        
        if self.text != '':
            font = pygame.font.SysFont('comicsans', self.font_size)
            text = font.render(self.text, 1, (0,0,0))
            win.blit(text, (self.x + (self.width/2 - text.get_width()/2), self.y + (self.height/2 - text.get_height()/2)))

    def is_over(self, pos):
        if self.disabled:  # Check if the button is disabled
            return False
        return self.x < pos[0] < self.x + self.width and self.y < pos[1] < self.y + self.height

    def disable(self):
        self.disabled = True

    def enable(self):
        self.disabled = False
    
class Client:
    def __init__(self, host='47.74.6.224', port=12345):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(0)
        
        self.username = None
        self.password = None
        self.withdraw_address = None
        
        self.running = True
        self.login_successful = False

        self.planet_image = pygame.image.load('dogecoin.png')
        self.ship_image = pygame.image.load('ship.png')
        self.clock = pygame.time.Clock()
        self.ships = {}  
        self.planets = {}

        self.zoom = 0.033
        self.pan_offset = [WIDTH//2, HEIGHT//2] 
        self.is_dragging = False
        self.last_mouse_pos = (0, 0)

        self.explosion_counter = 0

        pygame.font.init()
        self.font = pygame.font.Font("CJK.ttc", 20)
        self.font_size = 30

        self.key_states = {
            "left": False,
            "right": False,
            "up": False,
            "down": False
        }
        self.space_key_pressed = False
        self.r_key_pressed = False
        self.d_key_pressed = False

        self.last_update_time = pygame.time.get_ticks()

        self.previous_positions = {}
        self.previous_planet_positions = {}
        self.interpolation_rate = 0.001

        self.show_replenish_button = False
        self.show_loot_button = False
        self.replenish_button = pygame.Rect(250, 50, 120, 50)
        self.loot_button = pygame.Rect(100, 50, 120, 50)

        self.doge_button = Button(50, 50, 100, 40, 'Doge')
        self.ship_button = Button(50, 50, 100, 40, 'Ship')
        self.planet_button = Button(50, 100, 100, 40, 'Planet')

        self.doge_sub_buttons = []
        self.ship_sub_buttons = []
        self.planet_sub_buttons = []

        self.show_doge_buttons = False
        self.show_ship_buttons = False
        self.show_planet_buttons = False

        self.show_doge_sub_buttons = False
        self.show_ship_sub_buttons = False
        self.show_planet_sub_buttons = False

        self.death_wave_active_previous = {}
        self.ship_death_wave_last_state = {}

    def initialize_game(self):
        pygame.init()
        pygame.mixer.init()
        icon = pygame.image.load('DSE_APP.ico')
        pygame.display.set_icon(icon)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('Space Exploration - Client')

        pygame.mixer.music.load('music.mp3') 
        pygame.mixer.music.play(-1)

    def load_user_info(self):
        if os.path.exists('user_info.json'):
            with open('user_info.json', 'r') as file:
                user_info = json.load(file)
                self.set_login_details(user_info['username'], user_info['password'], user_info['withdraw_address'])

    def save_user_info(self):
        user_info = {
            'username': self.username,
            'password': self.password,
            'withdraw_address': self.withdraw_address
        }
        with open('user_info.json', 'w') as file:
            json.dump(user_info, file)
        
    def draw_buttons(self,planet_data):
        
        if self.show_replenish_button:
            pygame.draw.rect(self.screen, [0, 255, 0], self.replenish_button)
            self.screen.blit(self.font.render("Replenish", True, BLACK), (self.replenish_button.x+15, self.replenish_button.y+10))

        if self.show_loot_button:
            pygame.draw.rect(self.screen, [255, 0, 0], self.loot_button)
            self.screen.blit(self.font.render("Loot", True, [0, 0, 0]), (self.loot_button.x+15, self.loot_button.y+10))

        if self.show_ship_buttons and self.show_planet_buttons:
            if 'pp' in planet_data and planet_data['pn'] == self.username:
                p = (int(planet_data['pp'][0] * self.zoom + self.pan_offset[0]), 
                            int(planet_data['pp'][1] * self.zoom + self.pan_offset[1]))
                
                self.planet_button = Button(p[0], p[1]-50, 100, 40, 'Planet',color = GREEN)
                self.doge_button = Button(p[0], p[1]-100, 100, 40, 'Doge',color = DOGE_COLOR)
                
                dk =round((planet_data['dk']-0.495) * 1000**((planet_data['dk']-0.495)*10+1),1)
                dr =round((planet_data['dr']-1900)/100 * 10,1)
                ds =round((planet_data['ds']-80)/100 * 50,1)
                self.planet_sub_buttons = [
                    Button(p[0]+100, p[1]-50, 550, 41, f'Upgrade DW kill rate +0.5% -{dk} D',color = GREEN),
                    Button(p[0]+100, p[1]-10, 550, 41, f'Upgrade DW max radius +100 -{dr} D',color = GREEN),
                    Button(p[0]+100, p[1]+30, 550, 41, f'Upgrade DW speed +20 -{ds} D',color = GREEN),
                    Button(p[0]+100, p[1]+70, 550, 41, 'Purchase fuel (300,000 per dogecoin)',color = GREEN),
                    Button(p[0]+100, p[1]+110, 550, 41, 'Increase Fuel Price By 10,000',color = GREEN),
                    Button(p[0]+100, p[1]+150, 550, 41, 'Decrease Fuel Price By 10,000',color = GREEN),
                ]

                top_up_disabled = False
                if self.doge_sub_buttons and len(self.doge_sub_buttons) > 0:
                    top_up_disabled = self.doge_sub_buttons[0].disabled
                
                self.doge_sub_buttons = [
                    Button(p[0]+100, p[1]-100, 550, 41, 'Top Up',color = DOGE_COLOR, disabled=top_up_disabled),
                    Button(p[0]+100, p[1]-60, 550, 41, 'Withdraw(1 Dogecoin Minimum,0.1 Fee)',color = DOGE_COLOR),

                ]
            mouse_pos = pygame.mouse.get_pos()
            

            self.planet_button.draw(self.screen)
            self.doge_button.draw(self.screen)


            if self.planet_button.is_over(mouse_pos):
                self.show_planet_sub_buttons = True
            elif not any(btn.is_over(mouse_pos) for btn in self.planet_sub_buttons):
                self.show_planet_sub_buttons = False

            if self.doge_button.is_over(mouse_pos):
                self.show_doge_sub_buttons = True
            elif not any(btn.is_over(mouse_pos) for btn in self.doge_sub_buttons):
                self.show_doge_sub_buttons = False

            if self.show_planet_sub_buttons:
                for btn in self.planet_sub_buttons:
                    btn.draw(self.screen)

            if self.show_doge_sub_buttons:
                for btn in self.doge_sub_buttons:
                    btn.draw(self.screen)

    def draw_ship_buttons(self,ship_data):

        if self.show_ship_buttons and self.show_planet_buttons:
            if 'pvl' in ship_data and ship_data['sn'] == self.username:
                p = (int(ship_data['sp'][0] * self.zoom + self.pan_offset[0]), 
                            int(ship_data['sp'][1] * self.zoom + self.pan_offset[1]))
                
                self.ship_button = Button(p[0], p[1], 100, 40,'Ship',color = RED)

                pc = round(ship_data['pc'] * 100**(ship_data['pc']*10),1)
                dk = round((ship_data['dk']-0.295) * 1000**((ship_data['dk']-0.295)*10+1),1)
                dr = round((ship_data['dr']-900)/100 * 10,1)
                ds = round((ship_data['ds']-700)/100 * 10,1)
                ss = round(ship_data['ss'] * 1000**(ship_data['ss']*100),1)
                self.ship_sub_buttons = [
                    Button(p[0]+100, p[1], 550, 41, f'Upgrade payload capacity +0.01 -{pc} D',color = RED), 
                    Button(p[0]+100, p[1]+40, 550, 41, f'Upgrade DW kill rate +0.5% -{dk} D',color = RED),
                    Button(p[0]+100, p[1]+80, 550, 41, f'Upgrade DW max radius +100 -{dr} D',color = RED),
                    Button(p[0]+100, p[1]+120, 550, 41, f'Upgrade DW speed +100 -{ds} D',color = RED),
                    Button(p[0]+100, p[1]+160, 550, 41, f'Upgrade speed +0.001 -{ss} D',color = RED),
                ]


            mouse_pos = pygame.mouse.get_pos()
            
            self.ship_button.draw(self.screen)

            if self.ship_button.is_over(mouse_pos):
                self.show_ship_sub_buttons = True
            elif not any(btn.is_over(mouse_pos) for btn in self.ship_sub_buttons):
                self.show_ship_sub_buttons = False

            if self.show_ship_sub_buttons:
                for btn in self.ship_sub_buttons:
                    btn.draw(self.screen)

    def update_button_visibility(self, ship_data):
        successful_landing = ship_data.get('l')
        current_planet_name = ship_data.get('cpn')
        home_planet = ship_data.get('hp')
        if current_planet_name and successful_landing:
            if current_planet_name == home_planet:
                self.show_replenish_button = True
                self.show_loot_button = False
                self.show_ship_buttons = True
                self.show_planet_buttons = True
                self.show_doge_buttons = True
            else:
                self.show_replenish_button = True
                self.show_loot_button = True
                self.show_ship_buttons = False
                self.show_planet_buttons = False
                self.show_doge_buttons = False
        else:
            self.show_replenish_button = False
            self.show_loot_button = False
            self.show_ship_buttons = False
            self.show_planet_buttons = False
            self.show_doge_buttons = False

    def handle_mouse_click(self, event):
        if event.button == 1:
            if self.show_replenish_button and self.replenish_button.collidepoint(event.pos):
                self.send_command("replenish")
                pygame.mixer.Sound('replenish.wav').play()
                self.show_replenish_button = False
                self.show_loot_button = False
            elif self.show_loot_button and self.loot_button.collidepoint(event.pos):
                self.send_command("loot")
                pygame.mixer.Sound('loot.wav').play()
                self.show_replenish_button = False
                self.show_loot_button = False
            elif self.show_ship_sub_buttons and self.ship_sub_buttons[0].is_over(event.pos):
                self.send_command("upspc")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_ship_sub_buttons and self.ship_sub_buttons[1].is_over(event.pos):  
                self.send_command("upsdkr")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_ship_sub_buttons and self.ship_sub_buttons[2].is_over(event.pos):  
                self.send_command("upsdmr")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_ship_sub_buttons and self.ship_sub_buttons[3].is_over(event.pos):  
                self.send_command("upsds")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_ship_sub_buttons and self.ship_sub_buttons[4].is_over(event.pos):  
                self.send_command("upss")
                pygame.mixer.Sound('clicked.wav').play()
                
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[0].is_over(event.pos):  
                self.send_command("uppdkr")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[1].is_over(event.pos):  
                self.send_command("uppdmr")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[2].is_over(event.pos):  
                self.send_command("uppds")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[3].is_over(event.pos):  
                self.send_command("buyf")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[4].is_over(event.pos):  
                self.send_command("ipfp")
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_planet_sub_buttons and self.planet_sub_buttons[5].is_over(event.pos):  
                self.send_command("dpfp")
                pygame.mixer.Sound('clicked.wav').play()

            elif self.show_doge_sub_buttons and self.doge_sub_buttons[0].is_over(event.pos):
                self.send_command("topup")
                self.doge_sub_buttons[0].disable()
                pygame.mixer.Sound('clicked.wav').play()
            elif self.show_doge_sub_buttons and self.doge_sub_buttons[1].is_over(event.pos):
                self.send_command("withdraw")
                pygame.mixer.Sound('clicked.wav').play()
            

    def load_images(self):
        self.planet_image = pygame.transform.scale(self.planet_image, (100, 100))
        self.ship_image = pygame.transform.scale(self.ship_image, (40, 80))

    def send_login_details(self):
        login_details = {
            "c": "login",
            "username": self.username,
            "password": self.password,
            "withdraw_address": self.withdraw_address,
        }
        data = json.dumps(login_details)
        self.socket.sendto(data.encode('utf-8'), (self.host, self.port))

    def set_login_details(self, username, password, withdraw_address):
        self.username = username
        self.password = password
        self.withdraw_address = withdraw_address
        self.login_successful = True
        
    def send_logout_details(self):
        if self.username:
            logout_details = {
                "c": "logout",
                "username": self.username
            }
            data = json.dumps(logout_details)
            self.socket.sendto(data.encode('utf-8'), (self.host, self.port))
            self.running = False

    def request_ship_data(self):
        message = {"c": "request_ship_data"}
        data = json.dumps(message)
        self.socket.sendto(data.encode('utf-8'), (self.host, self.port))

    def receive_ship_data(self):
        try:
            data, _ = self.socket.recvfrom(4096)
            if data:
                received_data = json.loads(data.decode('utf-8'))

                if isinstance(received_data, list):
                    
                    for item in received_data:
                        self.process_data(item)
                            
                elif isinstance(received_data, dict):
                    #print(received_data)
                    self.process_data(received_data)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"Error receiving data: {e}")

    def process_data(self, data):
        #print(data)
        if 'u' in data:
            if data['u'] == 'usd':
                ship_name = data['sn']
                if ship_name in self.ships:
                    current_position = self.ships[ship_name]['sp']
                    current_angle = self.ships[ship_name]['a']
                    current_death_wave_radius = self.ships[ship_name].get('d', 0)  # Get death wave radius
                    current_time = pygame.time.get_ticks() / 1000.0

                    prev_data = self.previous_positions.get(ship_name, (None, None, 0, 0))
                    prev_position, prev_angle, prev_death_wave_radius, prev_time = prev_data[:4]

                    if ship_name not in self.previous_positions or \
                       prev_position != current_position or \
                       prev_angle != current_angle or \
                       prev_death_wave_radius != current_death_wave_radius:
                        self.previous_positions[ship_name] = (current_position, current_angle, current_death_wave_radius, current_time, 0)
                    self.ships[ship_name].update(data)
                else:
                    self.ships[ship_name] = data
                    self.previous_positions[ship_name] = (data['sp'], data['a'], data.get('d', 0), pygame.time.get_ticks() / 1000.0, 0)

            elif data['u'] in ['upfd', 'uplfd']:
                planet_name = data['pn']
                current_death_wave_radius = data.get('d', 0)
                current_time = pygame.time.get_ticks() / 1000.0

                if planet_name in self.planets:
                    prev_data = self.previous_planet_positions.get(planet_name, (0, 0))
                    prev_death_wave_radius, prev_time = prev_data

                    if planet_name not in self.previous_planet_positions or \
                       prev_death_wave_radius != current_death_wave_radius:
                        self.previous_planet_positions[planet_name] = (current_death_wave_radius, current_time)
                    self.planets[planet_name].update(data)
                else:
                    self.planets[planet_name] = data
                    self.previous_planet_positions[planet_name] = (current_death_wave_radius, current_time)
        elif 'pv' in data:
            if data['pv'] == 'pf':
                ship_name = data['sn']
                if ship_name in self.ships:
                    self.ships[ship_name].update(data)
        elif 'pvl' in data:
            #print(data)
            if data['pvl'] == 'plf':
                ship_name = data['sn']
                if ship_name in self.ships:
                    self.ships[ship_name].update(data)

        
        if 'type' in data:
            print(data['type']) 
            if data['type'] == 'topup':
                self.display_donation_address(data['address'])
            elif data['type'] == 'topup_success':
                # Display the top-up success message
                tk.messagebox.showinfo("Success", "Top Up Successful")

    def display_donation_address(self, address):
        def run_tkinter_window():
            def generate_qr_code(data, file_name='qr_code.png'):
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(data)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                img.save(file_name)
                return file_name

            def copy_to_clipboard():
                root.clipboard_clear()
                root.clipboard_append(address)
                messagebox.showinfo("Copied", "Address copied to clipboard")

            def on_close():
                self.notify_topup_window_closed()
                self.doge_sub_buttons[0].enable()
                root.destroy()

            qr_file = generate_qr_code(address)
            
            root = tk.Tk()
            root.title("Dogecoin Top Up")

            window_width = 300
            window_height = 500

            # Get screen width and height
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()

            # Calculate position x, y
            x = int((screen_width / 2) - (window_width / 2))
            y = int((screen_height / 2) - (window_height / 2))

            root.geometry(f'{window_width}x{window_height}+{x}+{y}')
            
            qr_image = Image.open(qr_file)
            qr_photo = ImageTk.PhotoImage(qr_image)
            qr_label = tk.Label(root, image=qr_photo)
            qr_label.image = qr_photo  # keep a reference
            qr_label.pack()

            address_label = tk.Label(root, text=f"Top Up Address:\n{address}\n\nPlease Do Not Close This Window,\nUntil Top Up Success.")
            address_label.pack()

            copy_button = tk.Button(root, text="Copy Address to Clipboard", command=copy_to_clipboard)
            copy_button.pack()

            root.protocol("WM_DELETE_WINDOW", on_close)
            root.mainloop()

        tkinter_thread = threading.Thread(target=run_tkinter_window)
        tkinter_thread.start()
        
    def notify_topup_window_closed(self):
        if self.username:
            close_topup_command = {
                "c": "close_topup",
                "username": self.username
            }
            data = json.dumps(close_topup_command)
            self.socket.sendto(data.encode('utf-8'), (self.host, self.port))

    def send_command(self, action):
        command = {"c": action}
        data = json.dumps(command)
        #print(data)
        self.socket.sendto(data.encode('utf-8'), (self.host, self.port))

    def update_key_state(self, event, state):
        if event.key == pygame.K_LEFT:
            self.key_states["left"] = state
        elif event.key == pygame.K_RIGHT:
            self.key_states["right"] = state
        elif event.key == pygame.K_UP:
            self.key_states["up"] = state
        elif event.key == pygame.K_DOWN:
            self.key_states["down"] = state
        elif event.key == pygame.K_SPACE:
            if state and not self.space_key_pressed:
                self.toggle_ignition()
                self.space_key_pressed = True
            elif not state:
                self.space_key_pressed = False
        elif event.key == pygame.K_r:
            if state and not self.r_key_pressed:
                self.respawn()
                self.r_key_pressed = True
            elif not state:
                self.r_key_pressed = False
        elif event.key == pygame.K_d:
            if state and not self.d_key_pressed:
                self.death_wave()
                self.d_key_pressed = True
            elif not state:
                self.d_key_pressed = False

    def handle_continuous_commands(self):
        if self.key_states["left"]:
            self.rotate_left()
        if self.key_states["right"]:
            self.rotate_right()
        if self.key_states["up"]:
            self.fuel_increase()
        if self.key_states["down"]:
            self.fuel_decrease()

    def rotate_left(self):
        self.send_command("l")

    def rotate_right(self):
        self.send_command("r")

    def fuel_increase(self):
        self.send_command("u")

    def fuel_decrease(self):
        self.send_command("d")

    def toggle_ignition(self):
        self.send_command("e")

    def respawn(self):
        self.send_command("re")

    def death_wave(self):
        self.send_command("dw")
        

    def draw_objects(self):
        self.screen.fill((255, 255, 255))
        for planet_data in self.planets.values():
            self.draw_planet(planet_data)
            self.draw_buttons(planet_data)
        for ship_data in self.ships.values():
            self.draw_ship(ship_data)
            self.draw_ship_buttons(ship_data)
        
        
        pygame.display.flip()  


    def draw_planet(self, planet_data):
        if 'pp' in planet_data:
            position = (int(planet_data['pp'][0] * self.zoom + self.pan_offset[0]), 
                        int(planet_data['pp'][1] * self.zoom + self.pan_offset[1]))
            
            size = int(500 * self.zoom)
            if self.planet_image:
                scaled_image = pygame.transform.scale(self.planet_image, (size * 2, size * 2))
                image_rect = scaled_image.get_rect(center=position)
                self.screen.blit(scaled_image, image_rect.topleft)
            else:
                color = planet_data.get('color', WHITE) 
                pygame.draw.circle(self.screen, color, position, size)

            if 'pn' in planet_data:
                self.draw_planet_label(planet_data, position)

            planet_name = planet_data['pn']
            death_wave_active = planet_data.get('da', False)############
            if planet_name not in self.death_wave_active_previous:
                self.death_wave_active_previous[planet_name] = False

            if death_wave_active and not self.death_wave_active_previous[planet_name]:
                pygame.mixer.Sound('death_wave.wav').play()
            
            self.death_wave_active_previous[planet_name] = death_wave_active##########
            #print(planet_data)
            if planet_name in self.previous_planet_positions:
                prev_death_wave_radius, prev_time = self.previous_planet_positions[planet_name]
                
                current_death_wave_radius = planet_data.get('d', 0)
                #print(f"current_death_wave_radius:{current_death_wave_radius}")
                current_time = pygame.time.get_ticks() / 1000.0
                
                num_interpolation_steps = 10
                step = min(num_interpolation_steps, int((current_time - prev_time) * 1000))
                if step < num_interpolation_steps:
                    interp_factor = step / num_interpolation_steps
                    interpolated_radius = prev_death_wave_radius + (current_death_wave_radius - prev_death_wave_radius) * interp_factor
                else:
                    interpolated_radius = current_death_wave_radius

                if interpolated_radius > 0:
                    #pygame.mixer.Sound('death_wave.wav').play()
                    self.draw_death_wave(position, interpolated_radius)
                #print(f"interpolated_radius:{interpolated_radius}")
                #print(f"self.planet_death_wave_counter:{self.planet_death_wave_counter}")
                    

    def draw_planet_label(self, planet_data, position):
        font_size = int(50*self.zoom)

        label_color = GREEN if planet_data['pn'] == self.username else BLACK
        label_name = self.font.render("Planet: "+planet_data['pn'], True, label_color)
        label_pos = (position[0] + 20, position[1] + 50) 
        if planet_data['dr'] and font_size> 13:
            label_dr = self.font.render("Planet DW Max Radius: "+str(planet_data['dr']), True, label_color)
            self.screen.blit(label_dr, (label_pos[0],label_pos[1]+40))
        if planet_data['ds'] and font_size> 13:
            label_ds = self.font.render("Planet DW Speed: "+str(planet_data['ds']), True, label_color)
            self.screen.blit(label_ds, (label_pos[0],label_pos[1]+60))
        if planet_data['dk'] and font_size> 13:
            label_dk = self.font.render("Planet DW Kill Rate: "+str(round(planet_data['dk']*100,1))+"%", True, label_color)
            self.screen.blit(label_dk, (label_pos[0],label_pos[1]+80))
        if 'pfp' in planet_data and font_size> 13:
            label_pfp = self.font.render("Planet Fuel Price: "+str(planet_data['pfp']), True, label_color)
            self.screen.blit(label_pfp, (label_pos[0],label_pos[1]+100))
        if 'pf' in planet_data and font_size> 13:
            label_pf = self.font.render("Planet Fuel Left: "+str(planet_data['pf']), True, label_color)
            self.screen.blit(label_pf, (label_pos[0],label_pos[1]+120))
        if 'pd' in planet_data:
            label_pd = self.font.render("Dogecoin: "+str(planet_data['pd']), True, label_color)
            self.screen.blit(label_pd, (label_pos[0], label_pos[1] + 20))

        self.screen.blit(label_name, label_pos)

    def draw_ship_label(self, ship_data, position):
        if ship_data['sn']:
            label_color = RED if ship_data['sn'] == self.username else BLACK
            label_sn = self.font.render("Ship: "+ship_data['sn'], True, label_color)
            self.screen.blit(label_sn, (position[0],position[1]+10))
        if ship_data['scp']:
            label_color = RED if ship_data['sn'] == self.username else BLACK
            label_scp = self.font.render("Payload: "+str(ship_data['scp']), True, label_color)
            self.screen.blit(label_scp, (position[0],position[1]+30))
        

    def draw_death_wave(self, center, radius):
        adjusted_radius = int(radius * self.zoom)
        pygame.draw.circle(self.screen, RED, center, adjusted_radius, 1)
            
    def draw_ship(self, ship_data):
        ship_name = ship_data['sn']
        current_position = ship_data['sp']
        current_angle = ship_data['a']
        current_death_wave_radius = ship_data.get('d', 0)
        current_time = pygame.time.get_ticks() / 1000.0

        num_interpolation_steps = 10
        #print(ship_data.get('da', False))
        death_wave_active = ship_data.get('da', False)############
        if ship_name not in self.ship_death_wave_last_state:
            self.ship_death_wave_last_state[ship_name] = False

        if death_wave_active and not self.ship_death_wave_last_state[ship_name]:
            pygame.mixer.Sound('death_wave.wav').play()
        
        self.ship_death_wave_last_state[ship_name] = death_wave_active######

        if ship_name in self.previous_positions:
            prev_position, prev_angle, prev_death_wave_radius,prev_time, step = self.previous_positions.get(ship_name, (None, None, None, 0))
            time_diff = current_time - prev_time

            if step < num_interpolation_steps:
                interp_factor = step / num_interpolation_steps
                interpolated_x = prev_position[0] + (current_position[0] - prev_position[0]) * interp_factor
                interpolated_y = prev_position[1] + (current_position[1] - prev_position[1]) * interp_factor
                angle_diff = (current_angle - prev_angle) % (2 * math.pi)
                if angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                if abs(angle_diff) < 0.1:
                    interpolated_angle = current_angle
                else:
                    interpolated_angle = prev_angle + angle_diff * interp_factor
                interpolated_radius = prev_death_wave_radius + (current_death_wave_radius - prev_death_wave_radius) * interp_factor

                self.previous_positions[ship_name] = (prev_position, prev_angle,prev_death_wave_radius, prev_time, step + 1)
            else:
                interpolated_x = current_position[0]
                interpolated_y = current_position[1]
                interpolated_angle = current_angle
                interpolated_radius = current_death_wave_radius
                self.previous_positions[ship_name] = (current_position, current_angle,current_death_wave_radius, current_time, 0)

            position = (int(interpolated_x * self.zoom + self.pan_offset[0]),
                        int(interpolated_y * self.zoom + self.pan_offset[1]))
            angle = interpolated_angle
        else:
            position = (int(current_position[0] * self.zoom + self.pan_offset[0]),
                        int(current_position[1] * self.zoom + self.pan_offset[1]))
            angle = current_angle
            interpolated_radius = current_death_wave_radius
            self.previous_positions[ship_name] = (current_position, current_angle, current_death_wave_radius,current_time, 0)

        rotated_ship = pygame.transform.rotate(self.ship_image, math.degrees(angle) + 90)
        scaled_width, scaled_height = rotated_ship.get_size()
        scaled_image = pygame.transform.scale(rotated_ship, (int(scaled_width * self.zoom / 3), int(scaled_height * self.zoom / 3)))
        adjusted_position = (position[0], position[1])
        rotated_image_rect = scaled_image.get_rect(center=adjusted_position)
        if interpolated_radius > 0:
            #pygame.mixer.Sound('death_wave.wav').play()
            self.draw_death_wave(adjusted_position, interpolated_radius)

        self.screen.blit(scaled_image, rotated_image_rect.topleft)

        self.draw_ship_label(ship_data,position)

        if 'pv' in ship_data:
            ship_name = ship_data['sn']
            self.update_button_visibility(ship_data)
            #angle = ship_data['a']
            real_position = (ship_data['sp'][0],ship_data['sp'][1])
            velocity = (ship_data['v'][0],ship_data['v'][1])
            absolute_velocity = math.sqrt(velocity[0]**2 + velocity[1]**2)
            current_payload = ship_data['scp']
            fuel = ship_data['f']
            fuel_consumption_speed = ship_data['fs']
            successful_landing = ship_data['l']
            death_wave_active = ship_data['da']
            death_wave_uses = ship_data['du']

            ship_name_text = self.font.render(f"Ship Name: {ship_name}", True, BLACK)
            position_text = self.font.render(f"Ship Position: X={real_position[0]:.2f}, Y={real_position[1]:.2f}", True, BLACK)
            absolute_velocity_text = self.font.render(f"Ship Velocity: {absolute_velocity:.1f}", True, BLACK)
            fuel_remaining_text = self.font.render(f"Fuel Remaining: {fuel:.0f}", True, BLACK)
            fuel_consumption_text = self.font.render(f"Fuel Consumption Speed: {fuel_consumption_speed:.0f}%", True, BLACK)
            current_payload_text = self.font.render(f"Current Payload: {current_payload:.8f} Dogecoin", True, BLACK)
            
            ship_name_text.set_alpha(128)
            position_text.set_alpha(128)
            absolute_velocity_text.set_alpha(128)
            fuel_remaining_text.set_alpha(128)
            fuel_consumption_text.set_alpha(128)
            current_payload_text.set_alpha(128)

            self.screen.blit(ship_name_text, (WIDTH - 420, HEIGHT - 230))
            self.screen.blit(position_text, (WIDTH - 420, HEIGHT - 210))
            self.screen.blit(absolute_velocity_text, (WIDTH - 420, HEIGHT - 190))
            self.screen.blit(fuel_remaining_text, (WIDTH - 420, HEIGHT - 170))
            self.screen.blit(fuel_consumption_text, (WIDTH - 420, HEIGHT - 150))
            self.screen.blit(current_payload_text, (WIDTH - 420, HEIGHT - 130))

            arrow_length = 20 
            direction_x = math.cos(angle)
            direction_y = math.sin(angle)
            start_x = adjusted_position[0]
            start_y = adjusted_position[1]
            end_x = start_x - direction_x * arrow_length
            end_y = start_y + direction_y * arrow_length
            arrow_color = (0, 255, 0) 
            pygame.draw.line(self.screen, arrow_color, (start_x, start_y), (end_x, end_y), 2)


            velocity_vector_x = velocity[0]*arrow_length
            velocity_vector_y = velocity[1]*arrow_length
            start_pos = (adjusted_position[0], adjusted_position[1])
            end_pos = (int(start_pos[0] + velocity_vector_x), int(start_pos[1] + velocity_vector_y))
            pygame.draw.line(self.screen, (0, 0, 255), start_pos, end_pos, 2)

            """label = self.font.render(ship_name, True, GREEN)
            label_pos = (adjusted_position[0] + 20, adjusted_position[1] + 20)
            self.screen.blit(label, label_pos)"""
            
            
        if 'pvl' in ship_data:
            payload_capacity =  ship_data['pc']
            reborn_position = ship_data['rbp']
            current_planet_name = ship_data['cpn']
            home_planet = ship_data['hp']
            speed = ship_data['ss']
            death_wave_max_radius =  ship_data['dr']
            death_wave_growth_rate = ship_data['ds']
            death_wave_killing_rate = ship_data['dk']

            payload_capacity_text = self.font.render(f"Payload Capacity: {payload_capacity:.8f} Dogecoin", True, BLACK)
            death_wave_max_radius_text = self.font.render(f"Ship Death Wave Max Radius: {death_wave_max_radius:.0f}", True, BLACK)
            death_wave_growth_rate_text = self.font.render(f"Ship Death Wave Speed: {death_wave_growth_rate:.0f}", True, BLACK)
            death_wave_killing_rate_text = self.font.render(f"Ship Death Wave Kill Rate: {death_wave_killing_rate*100:.1f}%", True, BLACK)
            speed_text = self.font.render(f"Ship Speed: {speed}", True, BLACK)

            payload_capacity_text.set_alpha(128)
            death_wave_max_radius_text.set_alpha(128)
            death_wave_growth_rate_text.set_alpha(128)
            death_wave_killing_rate_text.set_alpha(128)
            speed_text.set_alpha(128)

            self.screen.blit(payload_capacity_text, (WIDTH - 420, HEIGHT - 110))
            self.screen.blit(death_wave_max_radius_text, (WIDTH - 420, HEIGHT - 90))
            self.screen.blit(death_wave_growth_rate_text, (WIDTH - 420, HEIGHT - 70))
            self.screen.blit(death_wave_killing_rate_text, (WIDTH - 420, HEIGHT - 50))
            self.screen.blit(speed_text, (WIDTH - 420, HEIGHT - 30))

            #print(f"current_position[0]:{current_position[0]}")
            #print(f"reborn_position[0]:{reborn_position[0]}")
            
            if round(current_position[0], 0) == round(reborn_position[0], 0) and \
                   round(current_position[1], 0) == round(reborn_position[1], 0) and \
                   self.explosion_counter == 0:
                pygame.mixer.Sound('explosion.wav').play()
                self.explosion_counter+=1
            if round(current_position[0], 0) != round(reborn_position[0], 0) and \
                   round(current_position[1], 0) != round(reborn_position[1], 0):
                self.explosion_counter = 0
                
           
    def adjust_zoom(self, event):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_x = (mouse_x - self.pan_offset[0]) / self.zoom
        world_y = (mouse_y - self.pan_offset[1]) / self.zoom

        zoom_factor = 1.1
        smoothing_factor = 0.4
        if event.y > 0:
            target_zoom = self.zoom * zoom_factor
        else:
            target_zoom = self.zoom / zoom_factor

        self.zoom += (target_zoom - self.zoom) * smoothing_factor
        self.zoom = max(0.0001, min(self.zoom, 100))

        self.pan_offset[0] = mouse_x - world_x * self.zoom
        self.pan_offset[1] = mouse_y - world_y * self.zoom
    
    def run(self):
        # Start with the login process
        if not os.path.exists('user_info.json'):
            login_window = LoginWindow(self.set_login_details)
            login_window.run()
        else:
            self.load_user_info()
            self.login_successful = True
        tk.messagebox.showinfo("Play Guide", "Press R to reborn. Press D to initiate ship's death wave. Press Space Bar to toggle engine. Press Up or Down to adjust fuel speed. Press Left or Right to adjust ship's angle. Spin the Mouse Wheel to zoom in or out")

        # Check if login was successful
        if self.login_successful:
            self.initialize_game()
            self.send_login_details()
            self.save_user_info()
            self.request_ship_data()

            # Main game loop starts here
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                        self.send_logout_details()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            self.is_dragging = True
                            self.last_mouse_pos = event.pos
                            self.handle_mouse_click(event)
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if event.button == 1:
                            self.is_dragging = False
                    elif event.type == pygame.MOUSEMOTION:
                        if self.is_dragging:
                            dx, dy = event.pos[0] - self.last_mouse_pos[0], event.pos[1] - self.last_mouse_pos[1]
                            self.last_mouse_pos = event.pos
                            self.pan_offset[0] += dx
                            self.pan_offset[1] += dy
                    elif event.type == pygame.MOUSEWHEEL:
                        self.adjust_zoom(event)
                    elif event.type in [pygame.KEYDOWN, pygame.KEYUP]:
                        self.update_key_state(event, event.type == pygame.KEYDOWN)

                self.handle_continuous_commands()
                self.receive_ship_data()
                self.draw_objects()
                self.clock.tick(100)

            pygame.quit()
        else:
            print("Login not successful. Exiting game.")


if __name__ == "__main__":
    client = Client()
    client.run()

