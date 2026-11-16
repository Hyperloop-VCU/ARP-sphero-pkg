"""Control the Sphero BOLT's LEDs by typing colour keys in the terminal.

Start the driver first (in its own terminal):
    ros2 run sphero-monash-ros-pkg robot_node

Then run this node:
    ros2 run ARP-sphero-pkg sphero_led

While it is running, type a key and press Enter:
    r, g, b, ...   change to that colour (see COLORS below)
    off            turn the lights off
    on             turn the lights back on in the last colour
    cycle          switch between colours automatically
    list           show all the colour keys
    quit           stop the node

    TASKS:
    1. Change the cycle speed, make it cycle faster and slower
    2. Make only the top or bottom or matrix change color
    3. Only cycle between two colors
    4. Make it only cycle on and off(do not use the on keyword)
    5. Add a new color
"""

import threading
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import ColorRGBA

# =====================================================================
# SETTINGS - change these to change how the LEDs behave
# =====================================================================

# The colours you can pick. Each line is:
#     "key": (red, green, blue),
# Type the key in the terminal to show that colour.
# Each number goes from 0 (off) to 255 (full brightness).
# Add your own colours by adding a new line!
COLORS = {
    "r": (255, 0, 0),       # red
    "o": (255, 128, 0),     # orange
    "y": (255, 255, 0),     # yellow
    "g": (0, 255, 0),       # green
    "c": (0, 255, 255),     # cyan
    "b": (0, 0, 255),       # blue
    "p": (128, 0, 255),     # purple
    "pink": (255, 0, 128),  # pink
    "w": (255, 255, 255),   # white
    "off": (0, 0, 0),       # LEDs off
}

# Which lights to control:
#     "all"    - the front LEDs, back LEDs and the 8x8 screen together
#     "leds"   - the front and back LEDs together
#     "front"  - just the front LED
#     "back"   - just the back LED
#     "matrix" - just the 8x8 screen
TARGET = "all"

# The colour key to show when the node starts.
START_COLOR = "r"

# How many seconds to show each colour after you type "cycle".
# Smaller number = faster switching.
CYCLE_SPEED = 1.0

# The colour keys to switch between when cycling, in order.
CYCLE_COLORS = ["r", "o", "y", "g", "b", "p"]

# =====================================================================
# You don't need to change anything below this line to use the node.
# =====================================================================

# Which driver topics each TARGET publishes to.
TARGETS = {
    "all": ["/sphero/led/front", "/sphero/led/back", "/sphero/led/matrix"],
    "leds": ["/sphero/led/front", "/sphero/led/back"],
    "front": ["/sphero/led/front"],
    "back": ["/sphero/led/back"],
    "matrix": ["/sphero/led/matrix"],
}

# How often to resend the current colour (seconds), in case the driver
# was started after this node and missed the first message.
RESEND_PERIOD = 1.0

# The prompt shown when waiting for you to type a key.
PROMPT = "Color: "


class LedControlNode(Node):
    def __init__(self):
        super().__init__("sphero_led")

        # Every setting above can be overridden with --ros-args -p name:=value
        self.declare_parameter("target", TARGET)
        self.declare_parameter("start_color", START_COLOR)
        self.declare_parameter("cycle_speed", CYCLE_SPEED)
        self.declare_parameter("cycle_colors", CYCLE_COLORS)

        target = self.get_parameter("target").value
        start_color = self.get_parameter("start_color").value
        cycle_speed = float(self.get_parameter("cycle_speed").value)
        self.cycle_colors = list(self.get_parameter("cycle_colors").value)

        # Check the settings make sense before starting.
        if target not in TARGETS:
            raise ValueError(f"target must be one of {list(TARGETS)}, not '{target}'")
        if start_color not in COLORS:
            raise ValueError(f"start_color '{start_color}' is not a key in COLORS")
        for key in self.cycle_colors:
            if key not in COLORS:
                raise ValueError(f"cycle_colors has '{key}', which is not a key in COLORS")
        if cycle_speed <= 0:
            raise ValueError("cycle_speed must be more than 0 seconds")

        topics = TARGETS[target]
        self.publishers_list = [
            self.create_publisher(ColorRGBA, topic, 10) for topic in topics
        ]

        self.current_key = start_color
        # The last colour that wasn't "off", used by the "on" command.
        self.last_on_key = start_color
        if COLORS[start_color] == (0, 0, 0):
            # Starting with the lights off: "on" uses the first real colour.
            self.last_on_key = next(k for k, rgb in COLORS.items() if rgb != (0, 0, 0))
        self.cycling = False  # becomes True when you type "cycle"
        self.cycle_index = 0

        self.create_timer(cycle_speed, self.on_cycle_timer)
        self.create_timer(RESEND_PERIOD, self.send_current_color)

        self.get_logger().info(f"Controlling '{target}' on {', '.join(topics)}")

    def driver_connected(self):
        """True once the Sphero driver is running and listening for colours."""
        return all(p.get_subscription_count() > 0 for p in self.publishers_list)

    def send_current_color(self):
        """Publish the current colour. The driver wants each value from 0.0 to 1.0."""
        red, green, blue = COLORS[self.current_key]
        msg = ColorRGBA()
        msg.r = red / 255.0
        msg.g = green / 255.0
        msg.b = blue / 255.0
        msg.a = 1.0
        for publisher in self.publishers_list:
            publisher.publish(msg)

    def change_color(self, key):
        self.current_key = key
        if COLORS[key] != (0, 0, 0):
            self.last_on_key = key
        self.send_current_color()
        print(f"Showing: {key} {COLORS[key]}")

    def next_cycle_color(self):
        key = self.cycle_colors[self.cycle_index]
        self.cycle_index = (self.cycle_index + 1) % len(self.cycle_colors)
        self.change_color(key)

    def on_cycle_timer(self):
        if self.cycling:
            print("\r", end="")  # write over the "Color: " prompt
            self.next_cycle_color()
            print(PROMPT, end="", flush=True)  # then show the prompt again

    def handle_command(self, text):
        """Called every time something is typed in the terminal."""
        if text in COLORS:
            self.cycling = False
            self.change_color(text)
        elif text == "on":
            self.cycling = False
            self.change_color(self.last_on_key)
        elif text == "cycle":
            self.cycling = True
            print("Cycling colors. Type a color key to stop.")
        elif text == "list":
            print_help()
        elif text == "":
            pass
        else:
            print(f"Unknown key '{text}'. Type 'list' to see the keys.")


def print_help():
    print("\nColor keys:")
    for key, rgb in COLORS.items():
        print(f"  {key:<6} {rgb}")
    print("Other commands: on, cycle, list, quit\n")


def read_keyboard(node):
    """Runs in the background, waiting for the user to type commands."""
    while rclpy.ok():
        try:
            text = input(PROMPT).strip()
        except EOFError:
            break
        if text == "quit":
            break
        node.handle_command(text)
    rclpy.try_shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = LedControlNode()

    try:
        # Wait for the driver to connect to the robot before reading any keys,
        # so we don't take the number typed to pick the Sphero.
        if not node.driver_connected():
            print("Waiting for the Sphero driver to connect...")
            while rclpy.ok() and not node.driver_connected():
                rclpy.spin_once(node, timeout_sec=0.2)

        print_help()
        node.change_color(node.current_key)

        keyboard_thread = threading.Thread(target=read_keyboard, args=(node,), daemon=True)
        keyboard_thread.start()

        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
