"""Drive the Sphero out along a straight line and back to where it started.
I

    TASKS:
    1. add a diagonal direction
    2. change the speed
    3. change the pause time
"""

import math
import time
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions

# =====================================================================
# SETTINGS - change these to change how the robot moves
# =====================================================================

# The directions you can pick. Each line is:
#     "key": angle in degrees,
# 0 is forward, 90 is left, -90 is right and 180 is back.


DIRECTIONS = {
    "f": 0,       # forward
    "b": 180,     # back
    "l": 90,      # left
    "r": -90,     # right
   
}
# How fast to drive, in feet per second. The driver's top speed is about 1.6.
SPEED = 0.6

# The longest line you're allowed to type, in feet (to keep it on the table!).
MAX_LENGTH = 6.0

SLOW_DOWN_DISTANCE = 1.5
MIN_SPEED = 0.15
# Pause between changing directions
PAUSE = 1.0
TURN_TIME = 1.0
FORWARD_OFFSET = 45




# =====================================================================
# You don't need to change anything below this line to use the node.
# =====================================================================

CMD_VEL_TOPIC = "/cmd_vel"
ODOM_TOPIC = "/sphero/odom"

METERS_PER_FOOT = 0.3048


# How many times per second to check progress and send the speed command.
CONTROL_RATE = 20.0
TIMEOUT_FACTOR = 3.0
TURN_ONLY_SPEED = 0.0001


class LineDriveNode(Node):
    def __init__(self):
        super().__init__("sphero_line")

        # Every setting above can be overridden with --ros-args -p name:=value
        self.declare_parameter("speed", SPEED)
        self.declare_parameter("max_length", MAX_LENGTH)
        self.declare_parameter("pause", PAUSE)
        self.declare_parameter("forward_offset", FORWARD_OFFSET)
        self.declare_parameter("slow_down_distance", SLOW_DOWN_DISTANCE)
        self.declare_parameter("min_speed", MIN_SPEED)
        self.declare_parameter("turn_time", TURN_TIME)

        self.turn_time = float(self.get_parameter("turn_time").value)
        self.slow_down_distance = float(self.get_parameter("slow_down_distance").value) * METERS_PER_FOOT
        self.min_speed = float(self.get_parameter("min_speed").value) * METERS_PER_FOOT
        self.speed_ft = float(self.get_parameter("speed").value)
        self.max_length = float(self.get_parameter("max_length").value)
        self.pause = float(self.get_parameter("pause").value)
        self.forward_offset = float(self.get_parameter("forward_offset").value)

        # Check the settings make sense before starting.
        max_speed_ft = 0.5 / METERS_PER_FOOT
        if not 0 < self.speed_ft <= max_speed_ft:
            raise ValueError(f"speed must be more than 0 and at most {max_speed_ft:.2f} ft/s")
        if self.max_length <= 0:
            raise ValueError("max_length must be more than 0")
        if self.pause < 0:
            raise ValueError("pause can't be negative")
        if self.turn_time < 0:
            raise ValueError("turn_time can't be negative")
        if self.slow_down_distance < 0:
            raise ValueError("slow_down_distance can't be negative")
        if not 0 < self.min_speed <= self.speed_ft * METERS_PER_FOOT:
            raise ValueError("min_speed must be more than 0 and no more than speed")

        # The driver works in metres.
        self.speed = self.speed_ft * METERS_PER_FOOT

        self.cmd_pub = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)
        self.create_subscription(Odometry, ODOM_TOPIC, self.on_odom, 10)
        self.position = None  # latest (x, y) from the robot, in metres

    # ---- Talking to the driver ----

    def driver_connected(self):
        """True once the Sphero driver is running and listening for commands."""
        return self.cmd_pub.get_subscription_count() > 0

    def on_odom(self, msg):
        self.position = (msg.pose.pose.position.x, msg.pose.pose.position.y)

    def send_velocity(self, angle, speed):
        """Drive at `speed` m/s towards `angle` (radians, 0 = forward)."""
        msg = Twist()
        msg.linear.x = speed * math.cos(angle)
        msg.linear.y = speed * math.sin(angle)
        self.cmd_pub.publish(msg)

    def stop(self):
        """Stop completely (used when the node exits)."""
        self.send_velocity(0.0, 0.0)

    def face_forward(self):
        """Stop rolling, but keep facing "forward" while waiting.

        The driver keeps doing the last command it got, so the robot stays
        pointing forward until the next line.
        """
        self.send_velocity(math.radians(self.forward_offset), TURN_ONLY_SPEED)

    def get_fresh_position(self, timeout=2.0):
        """Wait for a new position from the robot, so we don't use an old one."""
        self.position = None
        end = time.monotonic() + timeout
        while self.position is None and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        return self.position

    # ---- Measuring ----

    def distance_from(self, start):
        """Straight-line distance from `start` to the robot, in metres."""
        return math.hypot(self.position[0] - start[0], self.position[1] - start[1])

    # ---- Driving the line ----

    def speed_for(self, remaining):
        """Full speed when far away, slowing down as the robot gets close."""
        if remaining >= self.slow_down_distance:
            return self.speed
        slowed = self.speed * remaining / self.slow_down_distance
        return max(self.min_speed, slowed)

    def drive_distance(self, angle, start, distance):
        """Drive towards `angle` until the robot is `distance` from `start`.

        Returns False if it took too long.
        """
        timeout = time.monotonic() + self.leg_time_limit
        while self.distance_from(start) < distance:
            if time.monotonic() > timeout:
                self.face_forward()
                return False
            remaining = distance - self.distance_from(start)
            self.send_velocity(angle, self.speed_for(remaining))
            rclpy.spin_once(self, timeout_sec=1.0 / CONTROL_RATE)
        self.face_forward()
        return True

    def turn_to(self, angle):
        """Turn on the spot to face `angle`, and give the robot time to get there."""
        end = time.monotonic() + self.turn_time
        while time.monotonic() < end:
            self.send_velocity(angle, TURN_ONLY_SPEED)
            rclpy.spin_once(self, timeout_sec=1.0 / CONTROL_RATE)

    def wait(self, seconds):
        """Stay stopped for a while (still listening to the robot)."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.face_forward()
            rclpy.spin_once(self, timeout_sec=1.0 / CONTROL_RATE)

    def drive_line(self, length_ft, direction_key):
        length = length_ft * METERS_PER_FOOT
        out_angle = math.radians(self.forward_offset + DIRECTIONS[direction_key])
        back_angle = out_angle + math.pi
        self.leg_time_limit = TIMEOUT_FACTOR * length / self.min_speed + 3.0

        print(f"Driving {length_ft} ft towards '{direction_key}'...")
        self.turn_to(out_angle)
        start = self.get_fresh_position()
        if start is None:
            print("No position from the robot. Is the driver connected?")
            return

        # Out: drive until the robot is `length` away from where it started.
        t0 = time.monotonic()
        if not self.drive_distance(out_angle, start, length):
            print("  Took too long, stopping. Is the robot stuck, or not reporting its position?")
            return
        self.wait(self.pause)
        out_dist = self.distance_from(start)
        if out_dist == 0.0:
            return  # didn't move at all, so there's nothing to drive back
        print(f"  out:  {time.monotonic() - t0 - self.pause:.1f} s, "
              f"went {out_dist / METERS_PER_FOOT:.2f} ft (asked for {length_ft} ft)")

        # Back: turn around on the spot, then drive the distance back to the start.
        print("Driving back...")
        self.turn_to(back_angle)
        turn_point = self.get_fresh_position()
        if turn_point is None:
            print("No position from the robot. Is the driver connected?")
            return
        back_dist = self.distance_from(start)
        t0 = time.monotonic()
        if not self.drive_distance(back_angle, turn_point, back_dist):
            print("  Took too long, stopping. Is the robot stuck, or not reporting its position?")
            return
        self.wait(self.pause)
        print(f"  back: {time.monotonic() - t0 - self.pause:.1f} s, "
              f"ended {self.distance_from(start) / METERS_PER_FOOT:.2f} ft from the start")


def ask_length(node):
    """Ask for a line length in feet. Returns a number, or None to quit."""
    while True:
        text = input("Length (ft): ").strip()
        if text == "quit":
            return None
        try:
            length = float(text)
        except ValueError:
            print("Type a number of feet, e.g. 2")
            continue
        if not 0 < length <= node.max_length:
            print(f"Length must be more than 0 and at most {node.max_length} ft")
            continue
        return length


def ask_direction():
    """Ask for a direction key. Returns the key, or None to quit."""
    keys = ", ".join(DIRECTIONS)
    while True:
        text = input(f"Direction ({keys}): ").strip()
        if text == "quit":
            return None
        if text in DIRECTIONS:
            return text
        print(f"Unknown direction '{text}'. Pick one of: {keys}")


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = LineDriveNode()

    try:
        if not node.driver_connected():
            print("Waiting for the Sphero driver to connect...")
            while not node.driver_connected():
                rclpy.spin_once(node, timeout_sec=0.2)

        node.face_forward()
        print("\nType a length and a direction to drive a line. Type 'quit' to stop.")
        while True:
            length = ask_length(node)
            if length is None:
                break
            direction = ask_direction()
            if direction is None:
                break
            node.drive_line(length, direction)
            print()
    except (KeyboardInterrupt, ExternalShutdownException, EOFError):
        pass
    finally:
        # Always stop the robot before exiting. The driver keeps doing the
        # last command it got, so without this it would keep rolling.
        for _ in range(3):
            node.stop()
            time.sleep(0.05)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
