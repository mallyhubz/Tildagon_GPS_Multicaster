import app
import settings
import socket
import network
import time

from events.input import Buttons, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
from system.eventbus import eventbus
from system.hexpansion.util import get_app_by_vid_pid

MCAST_GRP = '239.71.80.83'  
MCAST_PORT = 6969

class GPSMcast(app.App):

    def __init__(self):

        self.username = settings.get("name") or "Unknown"
        print("Badge user:", self.username)

        wlan = network.WLAN(network.STA_IF)

        while not wlan.isconnected():
            print("Connecting to network...")
            time.sleep(1)

        print("Connected! IP:", wlan.ifconfig()[0])
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)        
        
        try:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        except AttributeError:
            pass  # Skip if the constant isn't exposed by board firmware
        
        self.gps = get_app_by_vid_pid(0x7CAB, 0xBEAC)

        self.last_position = None
        self.last_speed = 0
        self.last_bearing = 0

        if self.gps:
            eventbus.on(
                self.gps.GPSEvent,
                self.handle_gps_event,
                self
            )
            print("GPS Hexpansion found")
        else:
            print("GPS Hexpansion NOT found")

        self.button_states = Buttons(self)
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
        eventbus.on(ButtonUpEvent, self._handle_buttonup, self)

    def on_resume(self):
        print("resumed")
    
    def on_pause(self):
        print("paused")

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["LEFT"] in event.button:
            print("Left Button Down")            
            self.send_location(self.last_position, self.last_speed, 1)
            time.sleep(1)
            self.button_states.clear()

        if BUTTON_TYPES["RIGHT"] in event.button:
            print("Right Button Down")
            self.button_states.clear()

        if BUTTON_TYPES["DOWN"] in event.button:
            self.close_app()
            self.button_states.clear()

        if BUTTON_TYPES["CANCEL"] in event.button:
            self.button_states.clear()
            self.minimise()
    
    def _handle_buttonup(self, event: ButtonUpEvent):
        if BUTTON_TYPES["LEFT"] in event.button:
            print("Left Button Up")
            self.button_states.clear()

        if BUTTON_TYPES["RIGHT"] in event.button:
            print("Right Button Up")
            self.button_states.clear()

    def send_multicast(self, message: str):
                
        try:        
                print(f"Sending multicast to {MCAST_GRP}:{MCAST_PORT}")
                self.sock.sendto(message, (MCAST_GRP, MCAST_PORT))
                time.sleep(1)
        finally:
                print("Sent Multicast")

    def on_destroy(self):
        print("I'm outta here!")
        self.sock.close()

    def send_location(self, pos, speed, forced):
        
        # get badge username
        user = self.username
        
        # Check if GPS is Fixed
        if (
            isinstance(pos, (tuple, list)) and
            len(pos) == 2
        ):
            lat, lon = pos            
            message = f"{user},{lat},{lon}"
            
            # only send if I am moving            
            if isinstance(speed, (int, float)) and (speed > 0 or forced == 1):
                print(message)
                self.send_multicast(message)
            else:
                print("Speed zero or invalid, not sending")

        # GPS is NOT Fixed
        else:
            
            # Check if Username is set
            if (user != "Unknown"):
                message = f"{user},?,?"
                print(message)
                self.send_multicast(message)                                
            else:
                print("No username, no location, why bother sending anything?")

    def handle_gps_event(self, event):

        self.last_position = event.position
        self.last_speed = event.speed
        self.last_bearing = event.bearing

        print("GPS Event")
        print("Position:", event.position)
        print("Speed:", event.speed)
        print("Bearing:", event.bearing)
        
        #lat, lon = event.position
        self.send_location(event.position, event.speed, 0)
        

    def update(self, delta):
        pass

    def draw(self, ctx):

        ctx.rgb(0, 0.2, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(0, 1, 0)

        if not self.gps:
            ctx.move_to(-100, 0).text("GPS Not Found")
            return

        if not self.last_position:
            ctx.move_to(-100, 0).text("Waiting For Fix")
            return

        lat, lon = self.last_position

        ctx.move_to(-110, -40).text(
            "Lat: %.5f" % lat
        )

        ctx.move_to(-110, -10).text(
            "Lon: %.5f" % lon
        )

        ctx.move_to(-110, 20).text(
            "Spd: %.1f kt" % self.last_speed
        )

        ctx.move_to(-110, 50).text(
            "Brg: %.0f" % self.last_bearing
        )


__app_export__ = GPSMcast