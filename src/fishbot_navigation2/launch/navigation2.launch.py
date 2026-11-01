# 导入必要的 Python 标准库
import os

# 导入 ROS 2 Launch 相关模块
import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # ========== 第一步：获取各功能包的共享目录路径 ==========
    # 获取 fishbot_navigation2 功能包的 share 目录路径
    fishbot_navigation2_dir = get_package_share_directory(
        'fishbot_navigation2')
    # 获取 nav2_bringup 功能包的 share 目录路径
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    # 拼接 RViz2 配置文件的完整路径（使用 nav2 默认的 RViz 视图配置）
    rviz_config_dir = os.path.join(
        nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')
    
    # ========== 第二步：创建 LaunchConfiguration 变量 ==========
    # LaunchConfiguration 允许通过命令行参数动态覆盖默认值
    
    # 是否使用仿真时间（Gazebo 时钟），默认为 true
    use_sim_time = launch.substitutions.LaunchConfiguration(
        'use_sim_time', default='true')
    # 地图 YAML 文件路径，默认为 fishbot_navigation2/maps/room.yaml
    map_yaml_path = launch.substitutions.LaunchConfiguration(
        'map', default=os.path.join(fishbot_navigation2_dir, 'maps', 'room.yaml'))
    # Navigation 2 参数配置文件路径，默认为 fishbot_navigation2/config/nav2_params.yaml
    nav2_param_path = launch.substitutions.LaunchConfiguration(
        'params_file', default=os.path.join(fishbot_navigation2_dir, 'config', 'nav2_params.yaml'))

    # ========== 第三步：构建并返回 LaunchDescription ==========
    return launch.LaunchDescription([
        # ---- 声明 Launch 参数（允许用户通过命令行覆盖默认值）----
        launch.actions.DeclareLaunchArgument('use_sim_time', default_value=use_sim_time,
                                             description='Use simulation (Gazebo) clock if true'),
        launch.actions.DeclareLaunchArgument('map', default_value=map_yaml_path,
                                             description='Full path to map file to load'),
        launch.actions.DeclareLaunchArgument('params_file', default_value=nav2_param_path,
                                             description='Full path to param file to load'),

        # ---- 包含 nav2_bringup 的 bringup_launch.py 启动文件 ----
        # 该启动文件会自动启动 Navigation 2 的所有核心节点
        launch.actions.IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [nav2_bringup_dir, '/launch', '/bringup_launch.py']),
            # 将本文件的 Launch 参数传递给被包含的启动文件，实现参数覆盖
            launch_arguments={
                'map': map_yaml_path,
                'use_sim_time': use_sim_time,
                'params_file': nav2_param_path}.items(),    #[('map', 'xxx.yaml'), ('use_sim_time', 'true'), ('params_file', 'xxx.yaml')]
        ),
        
        # ---- 启动 RViz2 可视化工具 ----
        launch_ros.actions.Node(
            package='rviz2',           # 功能包名称
            executable='rviz2',         # 可执行文件名称
            name='rviz2',               # 节点名称
            arguments=['-d', rviz_config_dir],  # 使用指定的 RViz 配置文件
            parameters=[{'use_sim_time': use_sim_time}],  # 启用仿真时间同步
            output='screen'),           # 将日志输出到终端
    ])