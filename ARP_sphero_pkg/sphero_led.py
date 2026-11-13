"""Control the Sphero BOLT's LEDs through the driver's LED topics.

Start the driver first:
    ros2 run sphero-monash-ros-pkg robot_node

Then, for example:
    ros2 run ARP-sphero-pkg led_control
    ros2 run ARP-sphero-pkg led_control --ros-args -p target:=front -p color:="[0, 255, 0]"
    ros2 run ARP-sphero-pkg led_control --ros-args -p mode:=cycle -p target:=matrix

Parameters:
    target  which LED to set: main, front, back or matrix (default: main)
    mode    solid (one colour) or cycle (step through a list of colours)
    color   [red, green, blue], each 0-255, used in solid mode
    period  seconds between messages (and between colours in cycle mode)
"""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import ColorRGBA

TARGETS = ("main", "front", "back", "matrix")

# Colours used in cycle mode, as (red, green, blue) from 0 to 255.
CYCLE_COLORS = [
    (255, 0, 0),      # red
    (255, 128, 0),    # orange
    (255, 255, 0),    # yellow
    (0, 255, 0),      # green
    (0, 0, 255),      # blue
    (128, 0, 255),    # purple
]


class LedControlNode(Node):
    def __init__(self):
        super().__init__("led_control")

        self.declare_parameter("target", "main")
        self.declare_parameter("mode", "solid")
        self.declare_parameter("color", [255, 0, 0])
        self.declare_parameter("period", 1.0)

        target = str(self.get_parameter("target").value)
        if target not in TARGETS:
            raise ValueError(f"target must be one of {TARGETS}, got '{target}'")

        self.mode = str(self.get_parameter("mode").value)
        if self.mode not in ("solid", "cycle"):
            raise ValueError(f"mode must be 'solid' or 'cycle', got '{self.mode}'")

        self.color = [int(c) for c in self.get_parameter("color").value]
        if len(self.color) != 3:
            raise ValueError("color must be [red, green, blue]")

        period = float(self.get_parameter("period").value)

        topic = f"/sphero/led/{target}"
        self.publisher = self.create_publisher(ColorRGBA, topic, 10)
        self.cycle_index = 0

        # Publish repeatedly so the colour still arrives if the driver
        # starts after this node does.
        self.timer = self.create_timer(period, self.on_timer)
        self.get_logger().info(f"Publishing {self.mode} colours on {topic}")

    def set_color(self, red: int, green: int, blue: int):
        """Send one colour. The driver expects each channel from 0.0 to 1.0."""
        msg = ColorRGBA()
        msg.r = red / 255.0
        msg.g = green / 255.0
        msg.b = blue / 255.0
        msg.a = 1.0
        self.publisher.publish(msg)

    def on_timer(self):
        if self.mode == "solid":
            self.set_color(*self.color)
        else:
            self.set_color(*CYCLE_COLORS[self.cycle_index])
            self.cycle_index = (self.cycle_index + 1) % len(CYCLE_COLORS)


def main(args=None):
    rclpy.init(args=args)
    node = LedControlNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
