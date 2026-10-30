# ========== 导入依赖 ==========
import launch
import launch_ros
import os
# 用于获取功能包 share 目录路径
from ament_index_python.packages import get_package_share_directory
# 用于在 launch 中 include 其他 launch 文件
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # ========== 1. 定义基础变量 ==========
    robot_name_in_model = "fishbot"           # Gazebo 中生成的实体名（可通过 gazebo 界面看到）
    urdf_tutorial_path = get_package_share_directory('fishbot_description') # 获取 fishbot_description 包 share 目录路径
    # 默认使用 fishbot 的完整 xacro（含底盘、传感器、轮子、Gazebo 插件等）
    default_model_path = os.path.join(urdf_tutorial_path, 'urdf/fishbot/fishbot.urdf.xacro')
    # Gazebo 世界文件（自定义房间场景）
    default_world_path = os.path.join(urdf_tutorial_path, 'world/custom_room.world')

    # ========== 2. 声明 Launch 参数 ==========
    # 允许启动时通过 model:=/path/to/xxx.xacro 覆盖默认模型
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='URDF/Xacro 文件的绝对路径')

    # ========== 3. 解析模型文件为 robot_description 参数 ==========
    # 运行时执行 xacro 命令，将 .xacro 展开为 .urdf XML 字符串
    robot_description = launch_ros.parameter_descriptions.ParameterValue(
        launch.substitutions.Command(
            ['xacro ', launch.substitutions.LaunchConfiguration('model')]),
        value_type=str)

    # ========== 4. 定义各节点 ==========

    # robot_state_publisher：
    #   发布 /robot_description，供 Gazebo spawn_entity 和 TF 树计算使用。
    #   Gazebo 仿真时 joint_state_publisher 由 ros2_control 接管，这里不需要启动。
    #   相当于命令行: ros2 run robot_state_publisher robot_state_publisher --ros-args -p robot_description:="这里填完整URDF字符串"
    robot_state_publisher_node = launch_ros.actions.Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    # 启动 Gazebo 仿真环境：
    #   通过 IncludeLaunchDescription 直接 include gazebo_ros 包自带的 gazebo.launch.py，
    #   并向它传递 world 参数（场景文件路径）和 verbose 参数（打印详细日志）。
    #   相当于命令行: ros2 launch gazebo_ros gazebo.launch.py world:=xxx verbose:=true
    launch_gazebo = launch.actions.IncludeLaunchDescription(
        PythonLaunchDescriptionSource([get_package_share_directory(
            'gazebo_ros'), '/launch', '/gazebo.launch.py']),
        launch_arguments=[('world', default_world_path), ('verbose', 'true')]
    )

    # 请求 Gazebo 将机器人模型生成到仿真世界中：
    #   -topic /robot_description：从该话题订阅 URDF XML（由 robot_state_publisher 发布）
    #   -entity fishbot：在 Gazebo 中的实体名
    #   -相当于命令行: ros2 run gazebo_ros spawn_entity.py -topic /robot_description -entity fishbot
    spawn_entity_node = launch_ros.actions.Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', '/robot_description',
                   '-entity', robot_name_in_model, ])

    # ========== 5. 定义 ros2_control 控制器加载命令 ==========
    # 这些控制器由 URDF 里的 <ros2_control> 标签声明，需要等机器人 spawn 到 Gazebo 后再加载。
    # 这里用 ExecuteProcess 执行等价的命令行：ros2 control load_controller --set-state active xxx

    # 5a. joint_state_broadcaster：
    #     负责把 Gazebo 里每个关节的实际角度/速度发布到 /joint_states，
    #     取代了 display_robot.launch.py 里 joint_state_publisher 的作用。
    load_joint_state_controller = launch.actions.ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'fishbot_joint_state_broadcaster'],
        output='screen'
    )

    # 5b. effort_controller（本文件中暂未被事件链引用，但可以手动启用）
    # load_fishbot_effort_controller = launch.actions.ExecuteProcess(
    #     cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
    #          'fishbot_effort_controller'],
    #     output='screen')

    # 5c. diff_drive_controller：
    #     差速驱动控制器，订阅 /cmd_vel（线速度+角速度），
    #     转换成左右轮的 effort 指令发给 Gazebo 仿真引擎。
    # load_fishbot_diff_drive_controller = launch.actions.ExecuteProcess(
    #     cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
    #          'fishbot_diff_drive_controller'],
    #     output='screen')

    # ========== 6. 组装 LaunchDescription ==========
    # 启动顺序 & 事件链（关键！不能乱）：
    #   ① robot_state_publisher 发布 /robot_description
    #   ② Gazebo 启动仿真环境
    #   ③ spawn_entity 把机器人生成到 Gazebo 世界
    #   ④ (事件) spawn_entity 退出后 → 加载 joint_state_broadcaster
    #   ⑤ (事件) joint_state_broadcaster 加载完 → 加载 diff_drive_controller
    #
    # 为什么要事件链？
    #   ros2_control 控制器必须等 <ros2_control> 硬件接口被 Gazebo 插件注册好之后才能加载，
    #   否则会报 "ControllerManager could not find hardware interface" 错误。
    return launch.LaunchDescription([
        action_declare_arg_mode_path,
        robot_state_publisher_node,
        launch_gazebo,
        spawn_entity_node,
        # 事件 1：spawn_entity 进程退出（成功加载机器人）后，触发加载 joint_state_broadcaster
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=spawn_entity_node,
                on_exit=[load_joint_state_controller],)
        ),
        # # 事件 2：joint_state_broadcaster 加载完后，触发加载 diff_drive_controller
        # launch.actions.RegisterEventHandler(
        #     event_handler=launch.event_handlers.OnProcessExit(
        #         target_action=load_joint_state_controller,
        #         on_exit=[load_fishbot_diff_drive_controller],)
        # ),
    ])


#  时间 ──────────────────────────────────────────────────────────►
#     │
#     │ ① robot_state_publisher ──发布──► /robot_description
#     │
#     │ ② Gazebo 启动（加载 custom_room.world）
#     │
#     │ ③ spawn_entity 订阅 /robot_description
#     │    └─► 把 fishbot 生成到 Gazebo 世界里 ✓
#     │
#     │    ⬇ OnProcessExit 事件触发
#     │
#     │ ④ ros2 control load_controller fishbot_joint_state_broadcaster
#     │    └─► 开始发布 /joint_states ✓
#     │
#     │    ⬇ OnProcessExit 事件触发
#     │
#     │ ⑤ ros2 control load_controller fishbot_diff_drive_controller
#     │    └─► 开始订阅 /cmd_vel ✓
#     │
#     ▼ 仿真就绪，可以发速度指令了
