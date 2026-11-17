## Setup

### 1. Create a workspace

Create a new ROS workspace (skip this step if you want to use an existing workspace):

```bash
mkdir -p sphero_ws/src
```

### 2. Clone the repository

Go into your workspace's `src` folder and clone the repository:

```bash
cd sphero_ws/src
git clone https://github.com/Hyperloop-VCU/sphero-monash-ros-pkg.git
```

### 3. Return to the workspace root

Move back up to the root of your workspace:

```bash
cd ..
```

### 4. Install ROS dependencies

Run `rosdep` to install all required ROS packages:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

> [!TIP]
> If you get an error asking you to run `sudo rosdep init` or `rosdep update`, follow the instructions printed in the terminal, then run the `rosdep install` command again. When it works, it prints `All required rosdeps installed successfully`.

### 5. Build the workspace

From the root of your workspace (e.g. `sphero_ws`), build the code and load it:

```bash
colcon build
source install/setup.bash
```

### 6. Launch a project
*Note: these projects require that you have https://github.com/Hyperloop-VCU/sphero-monash-ros-pkg.git in your src folder.
| Project | Command |
|---------|---------|
| LED  | `ros2 launch ARP-sphero-pkg sphero_led.launch.py` |
| Line | `ros2 launch ARP-sphero-pkg sphero_line.launch.py` |

### 7. After changing the code

Repeat [step 5](#5-build-the-workspace) to rebuild before launching again.
