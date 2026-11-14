from glob import glob

from setuptools import find_packages, setup

package_name = 'ARP-sphero-pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install every launch file so `ros2 launch ARP-sphero-pkg ...` finds it.
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hyperlabsuser',
    maintainer_email='no@no,.conm',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'led_control = ARP_sphero_pkg.sphero_led:main',
        ],
    },
)
