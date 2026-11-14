"""Start the Sphero driver and the line driver with one command.

    ros2 launch ARP-sphero-pkg sphero_line.launch.py

Everything runs in this one terminal:
    1. The driver scans for Spheros. Type the number of yours and press Enter
       (or just Enter to scan again).
    2. Once it has connected, the line driver asks for a "Length (ft):" and a
       "Direction". Type each one and press Enter.

To stop, press Ctrl+C or type "quit". Both stop the robot and the driver
properly so the robot disconnects.
"""

from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node

# ros2 launch normally gives each node its own input pipe, so typing in the
# terminal never reaches them. This runs each node with its input and output
# connected straight to this terminal (/dev/tty) instead.
IN_THIS_TERMINAL = "bash -c 'exec \"$0\" \"$@\" < /dev/tty > /dev/tty 2>&1'"


def generate_launch_description():
    driver = Node(
        package="sphero-monash-ros-pkg",
        executable="robot_node",
        name="sphero_robot_wrapper",
        prefix=IN_THIS_TERMINAL,
    )

    # sphero_line waits by itself until the driver has connected before it
    # asks anything, so it doesn't take the number typed for the driver.
    sphero_line = Node(
        package="ARP-sphero-pkg",
        executable="sphero_line",
        name="sphero_line",
        prefix=IN_THIS_TERMINAL,
        # To change settings from here instead of in sphero_line.py, add e.g.:
        # parameters=[{"speed": 0.4, "slow_down_distance": 1.0}],
    )

    # If either node stops (e.g. typing "quit"), stop everything.
    stop_all = [
        RegisterEventHandler(
            OnProcessExit(target_action=node, on_exit=[EmitEvent(event=Shutdown())])
        )
        for node in (driver, sphero_line)
    ]

    return LaunchDescription([driver, sphero_line, *stop_all])
