1. Create a Workspace

Create a new ROS workspace (skip this step if you want to use an existing workspace):

mkdir -p sphero_ws/src

2. Clone the Repository

Navigate into your workspace's src folder and clone the repository:

cd sphero_ws/src
git clone https://github.com/Hyperloop-VCU/sphero-monash-ros-pkg.git

3. Return to the Workspace Root

Move back up to the root directory of your workspace:

cd ..

4. Install ROS Dependencies

Run rosdep to install all required ROS packages:

rosdep install --from-paths src --ignore-src -r -y

    Troubleshooting: If you receive an error prompting you to run sudo rosdep init or rosdep update, follow the instructions printed in the terminal and run the rosdep install command again. When successful, it will output: all rosdeps installed successfully.

5. Navigate to the root of your workspace e.g "sphero_ws" and run "colcon build" to compile changes. Run "source install/setup.bash" for those changes to take effect.
6. Launch the sphero projects by running the following commands
     LED project:  ros2 launch ARP-sphero-pkg sphero_led.launch.py
     Line project: ros2 launch ARP-sphero-pkg sphero_line.launch.py
7. After making any changes to the code, repeat step 5.
