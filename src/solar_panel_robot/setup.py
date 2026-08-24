from setuptools import find_packages, setup
from glob import glob
import os

package_name = "solar_panel_robot"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            os.path.join("share", package_name, "config"),
            glob("config/*.yaml"),
        ),
        (
            os.path.join("share", package_name, "launch"),
            glob("launch/*.launch.py"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="jb9874123",
    maintainer_email="jb9874123@todo.todo",
    description="Solar panel assembly robot controller",
    license="Apache-2.0",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
<<<<<<< HEAD
        'console_scripts': [
            "main = solar_panel_robot.main:main",
            "action_server=solar_panel_robot.action_server:main",
=======
        "console_scripts": [
>>>>>>> origin/feature
            "controller = solar_panel_robot.controller_node:main",
        ],
    },
)