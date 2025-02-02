#!/usr/bin/python3
"""
    Hosts the `ObstacleMap` class object for maintaining the CBF enabled
    obstacle list for use in the CBF solver classes. Also provides basic
    visualization in Matplotlib. The object is specifically meant for use
    with the `CARLA simulator`.
    
    CHANGELOG:
    -> Added the ObstacleMapROS object for usage with `CARLA-ROS Bridge`.
    
    Creators' Metadata:
    Authors: 1. Shyamsundar PI | 2. Neelaksh Singh (ROS)
"""

import glob
import os
import sys
import time
import random

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import cv2
import numpy as np

# ROS Imports
# import rospy

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

from matplotlib.transforms import Affine2D
from euclid import *

sys.path.append(os.path.dirname(os.path.abspath('')) +
                "../../")
try:
    from cbf.geometry import Rotation as Rot
    from cbf.obstacles import BoundingBox as Bbox
except:
    raise

# ROS Imports
# from nav_msgs.msg import Odometry

class ObstacleMap:

    def __init__(self, ego, world, trajectory, lanes, display=True, range=30, collision_cone=True):
        """
        Initializing the ObstacleMap class with current ego vehicle, and world parameters
        :param ego: Vehicle object corresponding to the ego vehicle
        :param world: World object corresponding to the world initiated in the Carla server
        :param display: Flag to display the obstacle map
        :param range: Max range of the obstacles to be concerned in metres.
        """

        self.obstacles_list = None
        self.lanes = lanes
        self.ego = None
        self.ego_width = None
        self.ego_height = None
        self.ego_y = None
        self.ego_x = None
        self.ego_yaw = None
        self.ego_v = None
        self.trajectory = np.array(trajectory)[:,:2]

        self.walkers = None
        self.vehicles = None

        self.display = display
        self.collision_cone = collision_cone
        self.cbf_active = False
        self.range = range

        if display:
            self.fig, self.ax = plt.subplots()
            self.fig.tight_layout(pad=0)

        self.refresh(ego, world)

    def init_plot(self):
        plt.cla()
        self.ax.set_xlim(-self.range, self.range)
        self.ax.set_ylim(-self.range, self.range)
        self.ax.spines['left'].set_position('center')
        self.ax.spines['bottom'].set_position('center')
        self.ax.spines['right'].set_color('none')
        self.ax.spines['top'].set_color('none')
        # self.ax.invert_yaxis()
        self.ax.invert_xaxis()
        self.ax.set_xlabel("← West -- East → (metres)", fontsize=10)
        self.ax.set_ylabel("← South -- North → (metres)", fontsize=10)
        self.ax.xaxis.set_label_coords(0.2, 0)
        self.ax.yaxis.set_label_coords(0, 0.2)

    def plot_actors(self, *actors_list, buffer=1):
        """buffer: Buffer (in metres) given to the bounding boxes to form viable ellipses for the CBF"""
        self.obstacles_list = {}
        names = list(mcolors.BASE_COLORS)
        i=0
        for actors in actors_list:
            for actor in actors:
                if actor.id == self.ego.id and self.cbf_active and self.display:
                    self.ax.add_patch(patches.Rectangle(xy=(- self.ego_width / 2, - self.ego_height / 2),
                                                width=self.ego_width,
                                                height=self.ego_height,
                                                edgecolor='red',
                                                linewidth=2,
                                                transform=Affine2D().rotate_deg_around(*(0, 0),
                                                                                       self.ego_yaw) + self.ax.transData,
                                                fill=True,
                                                fc='green'))

                    # unit_ego_velocity_x = self.ego_v.make_unit_vector().x
                    # unit_ego_velocity_y = self.ego_v.make_unit_vector().y
                    # scaling_constant = 5
                    # plt.arrow(0, 0, unit_ego_velocity_x * scaling_constant, unit_ego_velocity_y * scaling_constant, width=0.2)

                elif actor.id == self.ego.id and self.display:
                    self.ax.add_patch(patches.Rectangle(xy=(- self.ego_width / 2, - self.ego_height / 2),
                                                width=self.ego_width,
                                                height=self.ego_height,
                                                edgecolor='green',
                                                linewidth= 2,
                                                transform=Affine2D().rotate_deg_around(*(0, 0),
                                                                                       self.ego_yaw) + self.ax.transData,
                                                fill=True,
                                                fc='green'))
                    # unit_ego_velocity_x = self.ego_v.make_unit_vector().x
                    # unit_ego_velocity_y = self.ego_v.make_unit_vector().y
                    # scaling_constant = 5
                    # plt.arrow(0, 0, unit_ego_velocity_x * scaling_constant, unit_ego_velocity_y * scaling_constant, width=0.2)

                else:
                    d_from_ego = actor.get_transform().location.distance(self.ego.get_transform().location)
                    random_color = names[i]
                    if d_from_ego < self.range:
                        actor_location = actor.get_transform().location
                        actor_rotation = actor.get_transform().rotation
                        actor_velocity = actor.get_velocity()
                        # bounding_box = Bbox(extent = Vector3(actor.bounding_box.extent.x, actor.bounding_box.extent.y, actor.bounding_box.extent.z),
                        #                     location = Vector3(actor_location.x, actor_location.y, actor_location.z),
                        #                     rotation = Rot(roll = actor_rotation.roll, pitch = actor_rotation.pitch, yaw = actor_rotation.yaw, right_handed=False),
                        #                     velocity = actor_velocity.length())
                        
                        # self.obstacles_list[str(actor.id)] = bounding_box
                        self.obstacles_list[str(actor.id)] = actor

                        if self.display:
                            actor_x = actor_location.x - self.ego_x
                            actor_y = actor_location.y - self.ego_y
                            actor_yaw = actor_rotation.yaw
                            actor_height = 2 * actor.bounding_box.extent.y
                            actor_width = 2 * actor.bounding_box.extent.x
                            unit_relative_velocity_x = (actor_velocity - self.ego_v).make_unit_vector().x
                            unit_relative_velocity_y = (actor_velocity - self.ego_v).make_unit_vector().y
                            scaling_constant = 5
                            plt.arrow(0, 0, unit_relative_velocity_x * scaling_constant, unit_relative_velocity_y * scaling_constant, width=0.3, ec = random_color, fc = random_color)

                            if self.collision_cone:
                                (Px, Py) = (0, 0)
                                (Cx, Cy) = (actor_x, actor_y)
                                a = math.sqrt((actor_width/2)**2 + (actor_height/2)**2)

                                b = math.sqrt((Px - Cx) ** 2 + (Py - Cy) ** 2)  # hypot() also works here
                                th = math.acos(a / b)  # angle theta
                                d = math.atan2(Py - Cy, Px - Cx)  # direction angle of point P from C
                                d1 = d + th  # direction angle of point T1 from C
                                d2 = d - th  # direction angle of point T2 from C

                                T1x = Cx + a * math.cos(d1)
                                T1y = Cy + a * math.sin(d1)
                                T2x = Cx + a * math.cos(d2)
                                T2y = Cy + a * math.sin(d2)

                                plt.plot((Px, T1x), (Py, T1y), color=random_color)
                                plt.plot((Px, T2x), (Py, T2y), color=random_color)
                                plt.plot((Px, -T1x), (Py, -T1y), color=random_color)
                                plt.plot((Px, -T2x), (Py, -T2y), color=random_color)

                                self.ax.add_artist(plt.Circle((Cx, Cy), a, color=random_color))

                            else:
                                self.ax.add_patch(patches.Ellipse(xy=(actor_x, actor_y),
                                                      width=actor_width + buffer,
                                                      height=actor_height + buffer,
                                                      edgecolor='red',
                                                      angle=actor_yaw,
                                                      fill=True,
                                                      fc='red'))
                    i = i + 1

    def plot_trajectory(self):
        rel_traj_x = self.trajectory[:,0] - self.ego_x
        rel_traj_y = self.trajectory[:,1] - self.ego_y
        self.ax.plot(rel_traj_x, rel_traj_y)

    def plot_lanes(self):
        if self.lanes is not None:
            for lane in self.lanes:
                rel_traj_x = lane[:,0] - self.ego_x
                rel_traj_y = lane[:,1] - self.ego_y
                self.ax.plot(rel_traj_x, rel_traj_y)

    def refresh(self, ego, world):
        """
        Method to refresh the Obstacle map after every tick
        :param ego: Refreshing the class' instance of the Ego vehicle
        :param world: Refreshing the class' instance of the world
        :return:
        """
        self.vehicles = world.get_actors().filter('vehicle.*')
        self.walkers = world.get_actors().filter('walker.*')
        self.ego = ego
        self.ego_x = self.ego.get_transform().location.x
        self.ego_y = self.ego.get_transform().location.y
        self.ego_height = 2 * self.ego.bounding_box.extent.y
        self.ego_width = 2 * self.ego.bounding_box.extent.x
        self.ego_yaw = self.ego.get_transform().rotation.yaw
        self.ego_v = self.ego.get_velocity()
        self.obstacles_list = {}

        if self.display:
            self.init_plot()

    def get_obstacle_map(self):
        self.plot_actors(self.vehicles, self.walkers, buffer=1)
        im = None
        if self.display:
            self.plot_trajectory()
            self.plot_lanes()
            self.fig.canvas.draw()
            data = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
            w, h = self.fig.canvas.get_width_height()
            im = data.reshape((int(h), int(w), -1))
            im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        return im, self.obstacles_list
    
# class ObstacleMapROS:

#     def __init__(self, world, trajectory, display=True, range=30):
#         """
#         Initializing the ObstacleMap class with current ego vehicle, and world parameters
#         :param ego: Vehicle object corresponding to the ego vehicle
#         :param world: World object corresponding to the world initiated in the Carla server
#         :param display: Flag to display the obstacle map
#         :param range: Max range of the obstacles to be concerned in metres.
#         """

#         self.obstacles_list = None
#         self.ego = None
#         self.ego_width = None
#         self.ego_height = None
#         self.ego_y = None
#         self.ego_x = None
#         self.ego_yaw = None
#         self.trajectory = np.array(trajectory)[:,:2]

#         self.walkers = None
#         self.vehicles = None

#         self.display = display
#         self.cbf_active = False
#         self.range = range

#         if display:
#             self.fig, self.ax = plt.subplots()
#             self.fig.tight_layout(pad=0)

#         self.refresh(ego, world)

#     def init_plot(self):
#         plt.cla()
#         self.ax.set_xlim(-self.range, self.range)
#         self.ax.set_ylim(-self.range, self.range)
#         self.ax.spines['left'].set_position('center')
#         self.ax.spines['bottom'].set_position('center')
#         self.ax.spines['right'].set_color('none')
#         self.ax.spines['top'].set_color('none')
#         self.ax.invert_yaxis()
#         self.ax.set_xlabel("← West -- East → (metres)", fontsize=10)
#         self.ax.set_ylabel("← South -- North → (metres)", fontsize=10)
#         self.ax.xaxis.set_label_coords(0.2, 0)
#         self.ax.yaxis.set_label_coords(0, 0.2)

#     def plot_actors(self, *actors_list, buffer=1):
#         """buffer: Buffer (in metres) given to the bounding boxes to form viable ellipses for the CBF"""
#         self.obstacles_list = {}
#         for actors in actors_list:
#             for actor in actors:
#                 if actor.id == self.ego.id and self.cbf_active and self.display:
#                     self.ax.add_patch(patches.Rectangle(xy=(- self.ego_width / 2, - self.ego_height / 2),
#                                                 width=self.ego_width,
#                                                 height=self.ego_height,
#                                                 edgecolor='red',
#                                                 linewidth=2,
#                                                 transform=Affine2D().rotate_deg_around(*(0, 0),
#                                                                                        self.ego_yaw) + self.ax.transData,
#                                                 fill=True,
#                                                 fc='green'))

#                 elif actor.id == self.ego.id and self.display:
#                     self.ax.add_patch(patches.Rectangle(xy=(- self.ego_width / 2, - self.ego_height / 2),
#                                                 width=self.ego_width,
#                                                 height=self.ego_height,
#                                                 edgecolor='green',
#                                                 linewidth= 2,
#                                                 transform=Affine2D().rotate_deg_around(*(0, 0),
#                                                                                        self.ego_yaw) + self.ax.transData,
#                                                 fill=True,
#                                                 fc='green'))

#                 else:
#                     d_from_ego = actor.get_transform().location.distance(self.ego.get_transform().location)
#                     if d_from_ego < self.range:
#                         actor_location = actor.get_transform().location
#                         actor_rotation = actor.get_transform().rotation
#                         bounding_box = Bbox(extent = Vector3(actor.bounding_box.extent.x, actor.bounding_box.extent.y, actor.bounding_box.extent.z),
#                                             location = Vector3(actor_location.x, actor_location.y, actor_location.z),
#                                             rotation = Rot(roll = actor_rotation.roll, pitch = actor_rotation.pitch, yaw = actor_rotation.yaw, right_handed=False))
                        
#                         self.obstacles_list[str(actor.id)] = bounding_box

#                         if self.display:
#                             actor_x = actor_location.x - self.ego_x
#                             actor_y = actor_location.y - self.ego_y
#                             actor_yaw = actor_rotation.yaw
#                             actor_height = 2 * actor.bounding_box.extent.y
#                             actor_width = 2 * actor.bounding_box.extent.x
#                             self.ax.add_patch(patches.Ellipse(xy=(actor_x, actor_y),
#                                                       width=actor_width + buffer,
#                                                       height=actor_height + buffer,
#                                                       edgecolor='red',
#                                                       angle=actor_yaw,
#                                                       fill=True,
#                                                       fc='red'))

#     def plot_trajectory(self):
#         rel_traj_x = self.trajectory[:,0] - self.ego_x
#         rel_traj_y = self.trajectory[:,1] - self.ego_y
#         self.ax.plot(rel_traj_x, rel_traj_y)

#     def refresh(self, ego_odom=Odometry(), world):
#         """
#         Method to refresh the Obstacle map after every tick
#         :param ego: Refreshing the class' instance of the Ego vehicle
#         :param world: Refreshing the class' instance of the world
#         :return:
#         """
#         self.vehicles = world.get_actors().filter('vehicle.*')
#         self.walkers = world.get_actors().filter('walker.*')
#         self.ego = ego
#         self.ego_x = self.ego.get_transform().location.x
#         self.ego_y = self.ego.get_transform().location.y
#         self.ego_height = 2 * self.ego.bounding_box.extent.y
#         self.ego_width = 2 * self.ego.bounding_box.extent.x
#         self.ego_yaw = self.ego.get_transform().rotation.yaw
#         self.ego_v = self.ego.get_velocity()
#         self.obstacles_list = {}

#         if self.display:
#             self.init_plot()

#     def get_obstacle_map(self):
#         self.plot_actors(self.vehicles, self.walkers, buffer=1)
#         self.plot_trajectory()
#         im = None
#         if self.display:
#             self.fig.canvas.draw()
#             data = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
#             w, h = self.fig.canvas.get_width_height()
#             im = data.reshape((int(h), int(w), -1))
#             im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
#         return im, self.obstacles_list