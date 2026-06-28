import subprocess
import sys
import os

# 使用当前正在运行的 Python。这样 Windows、macOS、虚拟环境都能跑。
python_path = sys.executable
print(f"当前使用的 Python 路径为：{python_path}")

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
local_libs = os.path.join(project_root, '.python-libs')
matplotlib_cache = os.path.join(project_root, '.matplotlib-cache')
os.makedirs(matplotlib_cache, exist_ok=True)
env = os.environ.copy()
env['PYTHONPATH'] = local_libs + os.pathsep + env.get('PYTHONPATH', '')
env['MPLBACKEND'] = 'Agg'
env['MPLCONFIGDIR'] = matplotlib_cache

# 脚本列表
scripts = [
    'md2xlsx.py',
    'P_study_time.py',
    'P_acc.py',
    'R_study_time.py',
    'R_acc.py',
    'P_acc_eng.py',
]

# 依次执行每个脚本
for script in scripts:
    print(f"\033[94m正在运行 {script}...\033[0m")  # 输出蓝色文字
    subprocess.run([python_path, script], check=True, env=env)
    print(f"\033[32m{script} 运行完成\033[0m\n\n\n")  # 输出绿色文字
