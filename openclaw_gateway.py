import logging
import json
import subprocess
import re
import httpx
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- 1. 配置管理 ---
CONFIG_FILE = 'openclaw.json'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("OpenClaw-Gateway")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return None

config = load_config()

# --- 2. 核心逻辑 ---

def extract_commands(text):
    """
    增强版指令提取逻辑：
    1. 优先提取 Markdown 代码块中的内容。
    2. 如果没有代码块，则尝试提取 COMMAND: 标记。
    3. 特殊处理 cat << 'EOF' 类型的多行 Shell 指令。
    4. 最后的容错处理：简短且无中文的回复视为直接指令。
    """
    cmds = []
    
    # 模式 A: 提取 Markdown 代码块 (优先级最高)
    code_blocks = re.findall(r'
http://googleusercontent.com/immersive_entry_chip/0

---

**更新步骤提示：**
1. 在 VPS 终端输入 `pkill -f openclaw_gateway.py`。
2. 输入 `cat << 'EOF' > openclaw_gateway.py`。
3. 粘贴上面的代码。
4. 在最后一行手动输入 `EOF` 并回车。
5. 运行 `python3 openclaw_gateway.py`。
