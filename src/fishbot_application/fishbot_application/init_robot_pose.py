# -*- coding: utf-8 -*-
"""
代码用途：初始化机器人在地图中的初始位姿

本节点的功能是向 Navigation 2 的定位模块（AMCL）发送机器人的初始位姿，
告诉导航系统 "机器人此刻在地图坐标系的哪个位置、朝向哪个方向"。
用代码实现了 RViz2 中 2D Pose Estimate 工具的功能。

执行流程：
    1. 初始化 ROS 2 客户端
    2. 创建 BasicNavigator 对象（封装了 Navigation 2 的常用接口）
    3. 构建 PoseStamped 消息，设置位姿为 (0, 0, 朝向正前方)
    4. 调用 setInitialPose() 发布初始位姿
    5. 调用 waitUntilNav2Active() 等待 Navigation 2 完全启动
    6. 保持节点运行

使用前提：
    - Navigation 2 节点已启动
    - TF 树中有 map -> odom 的变换（由定位模块发布）
"""

from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
import rclpy


def main():
    # 初始化 ROS 2 客户端
    rclpy.init()

    # 创建 BasicNavigator 对象
    # BasicNavigator 是 nav2_simple_commander 提供的高层导航接口，
    # 封装了导航目标发送、位姿设置、导航状态等待等常用操作
    navigator = BasicNavigator()

    # ========== 构建初始位姿消息 ==========
    initial_pose = PoseStamped()

    # 设置参考坐标系为 'map'（全局地图坐标系）
    initial_pose.header.frame_id = 'map'

    # 设置时间戳为当前时刻（使用 Navigation 2 的时钟，支持仿真时间）
    initial_pose.header.stamp = navigator.get_clock().now().to_msg()

    # 设置位置：地图原点 (x=0, y=0)
    initial_pose.pose.position.x = 0.0
    initial_pose.pose.position.y = 0.0

    # 设置朝向：四元数 (x=0, y=0, z=0, w=1) 表示无旋转，即朝向正前方
    # 等价于欧拉角 yaw=0°
    initial_pose.pose.orientation.w = 1.0

    # ========== 发布初始位姿 ==========
    # 向 /initialpose 话题发布初始位姿，AMCL 接收到后会以此为基础开始定位
    navigator.setInitialPose(initial_pose)

    # 等待 Navigation 2 所有关键节点（地图服务器、定位器、规划器、控制器）
    # 全部启动并处于活跃状态，避免后续导航命令因节点未就绪而失败
    navigator.waitUntilNav2Active()

    # 保持节点运行，处理 ROS 2 回调
    rclpy.spin(navigator)

    # 节点关闭前清理资源
    rclpy.shutdown()


if __name__ == '__main__':
    main()