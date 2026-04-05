OpenClaw 项目架构与交接手册 (v1.0)

1. 项目背景

OpenClaw 是一个基于 AI 驱动的自动化开发系统，目标是维护和升级 CMaNGOS Web 管理后台。系统通过 Telegram 远程调度部署在 4090 算力机上的 Ollama 大模型，并在隔离的 Docker 环境中执行指令。

2. 核心架构拓扑

大脑 (Reasoning): 本地 4090 运行的 ollama (模型: qwen2.5-coder:32b)。

中枢 (Gateway): openclaw_gateway.py (运行在宿主机)。

功能：监听 Telegram 指令 -> 请求 AI 规划 Bash 命令 -> 调度 Docker 执行 -> 返回回显。

肢体 (Execution): Docker 容器 openclaw-sandbox (基于 Ubuntu 22.04)。

挂载点：宿主机 /root/AI/cmangos-web <=> 容器 /app。

运行身份：非 root 用户 openclaw。

3. 已完成的工程链路 (Milestones)

AI 通信链路：成功实现 httpx 异步请求 Ollama API，支持 120s 超时处理（应对复杂推理）。

安全隔离：实现了基于 Docker 的指令截断与执行，防止 AI 直接操作宿主机文件系统。

身份鉴权：Gateway 仅响应 allowed_chat_id 定义的管理员 Telegram ID。

灵魂约束：引入 SOUL.md 机制，作为 AI 的 System Prompt，确保其理解项目准则。

4. 关键配置文件

openclaw.json: 存储 telegram_token, ollama_url, allowed_chat_id, sandbox_name。

SOUL.md: 存储 AI 的开发准则和架构偏好。

openclaw_gateway.py: 核心 Python 调度逻辑。

5. 开发规范 (给接手 AI 的提示词)

"如果你是接手此项目的 AI，请务必读取 /app/SOUL.md。在生成 Bash 指令时，请优先考虑在 /app 路径下的操作。如果遇到权限问题，请提醒用户使用 sudo 或修改宿主机 /root/AI/cmangos-web 的权限。"

6. 维护命令

查看网关日志: tail -f openclaw.log (如果使用 nohup)

重启网关: pkill -f openclaw_gateway.py && python3 openclaw_gateway.py

重启沙箱: docker restart openclaw-sandbox
