🪐 OpenClaw v4.0 项目实施蓝图

1. 核心架构状态 (Current Status)

组件

状态

技术栈

物理位置

执行肢体 (Executor)

✅ 已部署

Docker (Ubuntu 22.04)

新加坡 VPS (1vCPU/2GB)

项目意识 (Soul)

✅ 已建立

SOUL.md (Markdown)

VPS /app 目录

逻辑大脑 (Planner)

✅ 已挂载

Qwen2.5-Coder:32b

远程 4090 (Tailscale)

通信中枢 (Gateway)

✅ 已联通

Python (Asyncio)

VPS 运行

2. 核心配置文件 (openclaw.json)

存放在 VPS 的 ~/AI/ 目录下：

{
  "telegram_token": "8626847285:AAGCI4bCXDo91NKJSTicwLfZuztJUqyqUqc",
  "allowed_chat_id": "8322611128",
  "ollama_url": "http://[4090_Tailscale_IP]:11434/api/generate",
  "project_path": "/root/AI/cmangos-web",
  "sandbox_name": "openclaw-sandbox"
}


3. 中枢代码实现 (openclaw_gateway.py)

该脚本负责接收 Telegram 指令，调用 4090 推理，并在 Docker 沙箱中执行。

(注：代码已实现异步非阻塞请求及 SOUL.md 注入)

# 核心逻辑摘要：
# 1. 拦截非授权 ID
# 2. 读取 SOUL.md 注入 System Prompt
# 3. 异步请求 Ollama API (Timeout: 120s)
# 4. 正则提取 COMMAND 或 Markdown 代码块
# 5. docker exec 执行并回传结果


4. 关键环境指令 (Rebuild Commands)

4.1 重建 Docker 沙箱

docker run -d --name openclaw-sandbox \
  -v /root/AI/cmangos-web:/app \
  -w /app \
  ubuntu:22.04 \
  tail -f /dev/null


4.2 启动中枢服务

# 安装依赖
pip3 install httpx python-telegram-bot

# 后台运行
nohup python3 openclaw_gateway.py > openclaw.log 2>&1 &


5. 已定义的开发规约 (SOUL.md)

技术栈：Drupal 10 (后端) + Astro (前端)。

权限：所有内部操作使用 openclaw 用户（UID 1000）。

路径：代码库挂载于沙箱内的 /app。

原则：Planner 必须先进行路径分析，Executor 严禁删除根目录。

6. 下一步行动计划 (Roadmap)

阶段四：环境依赖注入

在沙箱中安装 PHP 8.1+, Composer, Node.js 18+。

配置 Drush 工具链。

阶段五：代码库初始化

使用 OpenClaw 自动下载并配置 Drupal 10 核心。

建立 Astro 基础架构。

阶段六：自动化流水线

实现“一键同步”，将沙箱代码推送到本地 4090 或预览服务器。

最后更新时间：2026-04-05
