# ROS2 Launch 文件相关库
import launch
import launch_ros
import os
# 用于获取功能包 share 目录的工具函数
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # ========== 1. 获取功能包下的默认文件路径 ==========
    # 获取 fishbot_description 功能包的 share 目录路径
    urdf_tutorial_path = get_package_share_directory('fishbot_description')
    # 拼接 URDF 模型文件的绝对路径（默认模型）
    default_model_path = os.path.join(urdf_tutorial_path, 'urdf', 'first_robot.urdf')
    # 拼接 RViz 配置文件的绝对路径
    default_rviz_config_path = os.path.join(urdf_tutorial_path, 'config', 'rviz', 'display_model.rviz')

    # ========== 2. 声明 Launch 参数 ==========
    # 声明一个名为 'model' 的 Launch 参数，允许用户在启动时通过
    # `ros2 launch fishbot_description display_robot.launch.py model:=/path/to/robot.urdf`
    # 来指定自己的模型文件，默认使用上面拼接的路径
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='URDF 的绝对路径')

    # ========== 3. 将 URDF 文件内容转换为 robot_description 参数 ==========
    # 使用 xacro 命令（xacro /path/to/robot.xacro）对模型文件进行处理（支持 .xacro 文件展开），
    # 然后将输出结果作为字符串 ParameterValue，提供给 robot_state_publisher 使用。
    # LaunchConfiguration('model') 会在运行时获取上面声明的 'model' 参数值。
    robot_description = launch_ros.parameter_descriptions.ParameterValue(
        launch.substitutions.Command(
            # ['cat ', launch.substitutions.LaunchConfiguration('model')]),     # 如果是xacro文件，直接cat /path/to/robot.urdf
            ['xacro ', launch.substitutions.LaunchConfiguration('model')]),     # 如果是用的.xacro,则使用xacro /path/to/robot.xacro，注意上面的参数默认为.urdf文件，此时需传参model:=/path/to/robot.xacro
        value_type=str)

    # ========== 4. 定义需要启动的 ROS2 节点 ==========

    # robot_state_publisher：
    #   订阅 /joint_states 话题，根据 URDF 模型计算 tf 树并发布。
    #   必须传入 robot_description 参数（即 URDF 字符串）。
    robot_state_publisher_node = launch_ros.actions.Node(   # 原命令是ros2 run robot_state_publisher robot_state_publisher --robot_description urdf描述字符串
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # joint_state_publisher：
    #   一个"虚拟"的关节状态发布节点，用于没有实际硬件或仿真时，
    #   提供默认的关节角度（全部为 0），驱动 robot_state_publisher 发布 tf。
    #   如果有真实的 /joint_states 来源，可以去掉此节点。
    joint_state_publisher_node = launch_ros.actions.Node(   # 原命令是ros2 run joint_state_publisher joint_state_publisher
        package='joint_state_publisher',
        executable='joint_state_publisher',
    )

    # RViz2：
    #   可视化节点，'-d' 参数指定启动时加载的配置文件，
    #   这样打开后就会自动按预设配置显示机器人模型、TF、话题等。
    rviz_node = launch_ros.actions.Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', default_rviz_config_path],   # 原命令是ros2 run rviz2 rviz2 -d /path/to/rviz/config.rviz
    )

    # ========== 5. 组装 LaunchDescription 并返回 ==========
    # LaunchDescription 是 Launch 文件的入口对象，按顺序放入所有要执行的 action。
    # 顺序建议：先声明参数，再启动节点。
    return launch.LaunchDescription([
        action_declare_arg_mode_path,    # 参数声明（必须放在使用它的节点之前）
        joint_state_publisher_node,      # 关节状态发布
        robot_state_publisher_node,      # 机器人状态发布（依赖 robot_description）
        rviz_node                        # 可视化
    ])