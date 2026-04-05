# 完全 AI 驱动软件开发平台架构方案

**版本：** 3.0  
**日期：** 2026-04-05  
**定位：** 通用方案，适用于多个项目  
**核心目标：** 开发者通过 Telegram 发出需求，AI 自主完成规划 → 编码 → 测试 → 部署全流程

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      开发者（任何地方）                           │
│                  通过 Telegram 发送自然语言指令                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                 新加坡 VPS（DigitalOcean）                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               OpenClaw Gateway（核心枢纽）                │   │
│  │                                                         │   │
│  │  Channel Adapters  →  Session Manager  →  Agent Runtime │   │
│  │  （Telegram接入）      （会话/记忆管理）    （任务执行循环）  │   │
│  │                              │                          │   │
│  │                    ┌─────────▼──────────┐               │   │
│  │                    │    Model Router    │               │   │
│  │                    │  主力 → Ollama     │               │   │
│  │                    │  fallback → Cloud  │               │   │
│  │                    └────────────────────┘               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐                   │
│  │   Claude Code    │   │  GitHub Actions  │                   │
│  │  （代码执行引擎） │   │  Self-hosted     │                   │
│  │                  │   │  Runner（CI/CD） │                   │
│  └──────────────────┘   └──────────────────┘                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Tailscale VPN
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    国内 PC（RTX 4090）                            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Ollama（主力推理，90%+ token 消耗在本地）                 │   │
│  │  ├── qwen2.5-coder:32b   代码生成 / 审查 / Debug         │   │
│  │  ├── qwen3:32b           规划 / 分析 / 文档              │   │
│  │  └── nomic-embed-text    RAG 向量嵌入                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

云端 API（按需 fallback，最小化消耗）
  ├── DeepSeek API   复杂推理备用
  └── Claude API     本地连续失败 3 次后的最终兜底
```

---

## 二、OpenClaw：调度中枢详解

OpenClaw 是本方案的神经中枢，负责：Telegram 消息接入、Agent 身份与记忆管理、模型路由与 fallback、心跳自主调度、工具执行。

**它不是另一个需要维护的服务，它本身就是 Agent。**

### 2.1 OpenClaw 核心机制

OpenClaw Gateway 是一个单进程 Node.js 守护程序（systemd 管理），内部包含五个子系统：

| 子系统 | 职责 |
|--------|------|
| Channel Adapters | 接入 Telegram（grammY）等平台，统一消息格式 |
| Session Manager | 解析发送者身份，维护对话上下文，DM 独立会话 |
| Queue | 串行化每个 session 的任务，防止并发冲突 |
| Agent Runtime | 组装上下文 → 调用模型 → 执行工具 → 循环直到完成 |
| Control Plane | WebSocket API（:18789），CLI / Web UI 连接点 |

### 2.2 模型路由配置（openclaw.json）

```json
{
  "models": {
    "primary": {
      "provider": "ollama",
      "baseURL": "http://100.x.x.x:11434",
      "model": "qwen2.5-coder:32b",
      "comment": "主力模型，跑在国内 4090，通过 Tailscale 访问"
    },
    "planner": {
      "provider": "ollama",
      "baseURL": "http://100.x.x.x:11434",
      "model": "qwen3:32b",
      "comment": "规划与分析任务"
    },
    "fallback": [
      {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "trigger": "confidence_low",
        "comment": "本地置信度低时触发"
      },
      {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5",
        "trigger": "local_fail_3x",
        "comment": "最终兜底，连续失败 3 次后触发"
      }
    ],
    "fallbackStrategy": "exponential_backoff"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}",
      "allowedChatIds": ["${YOUR_CHAT_ID}"],
      "comment": "白名单限制，只响应指定用户"
    }
  }
}
```

### 2.3 心跳自主调度（HEARTBEAT.md）

OpenClaw 每 30 分钟自动唤醒，读取 `HEARTBEAT.md` 决定是否主动行动，无需人工触发：

```markdown
# HEARTBEAT.md

## 定时检查清单
- [ ] 检查 GitHub Actions 最近一次 pipeline 状态，若失败则通知开发者
- [ ] 检查各项目健康端点（/health），超时则告警
- [ ] 检查是否有未处理超过 2 小时的 Issue，若有则摘要汇报
- [ ] 检查 Ollama 服务是否可达（Tailscale 连接），不可达则切换 fallback
```

---

## 三、Agent 设计（基于 SOUL.md）

OpenClaw 使用 `SOUL.md` 定义 Agent 的身份、能力和行为规则，不需要写代码，配置即 Agent。

本方案设计 **4 个专职 Agent**，通过 OpenClaw 的 Multi-Agent Routing 实现隔离与协作。

### Agent 1：Planner（规划师）

```markdown
# SOUL.md — Planner Agent

## 身份
你是一名资深技术项目经理，负责将开发者的自然语言需求拆解为可执行的子任务序列。

## 使用模型
qwen3:32b（通过 Ollama，Tailscale 访问）

## 核心能力
- 理解需求意图，识别技术边界
- 将任务拆解为粒度合适的子任务（每个子任务预计执行时间 < 30 分钟）
- 为每个子任务指定执行 Agent、所需工具、验收标准
- 输出结构化 JSON 任务列表

## 输出格式（严格遵守）
{
  "tasks": [
    {
      "id": "task_001",
      "title": "任务标题",
      "agent": "coder|reviewer|devops",
      "description": "具体描述",
      "acceptance_criteria": ["验收标准1", "验收标准2"],
      "estimated_minutes": 20
    }
  ]
}

## 行为规则
- 不执行代码，只做规划
- 若需求不清晰，先向开发者确认，再拆解
- 拆解完成后通过 Telegram 回复任务列表摘要，等待确认后再分发

## 禁止行为
- 不得直接修改任何文件
- 不得跳过验收标准定义
```

### Agent 2：Coder（开发者）

```markdown
# SOUL.md — Coder Agent

## 身份
你是一名全栈开发工程师，负责根据 Planner 分配的子任务，通过 Claude Code 实际编写和修改代码。

## 使用模型
qwen2.5-coder:32b（主力），置信度 < 7 时自动升级至 DeepSeek API

## 核心能力
- 读取项目 CLAUDE.md 了解规范和约束
- 通过 RAG 检索相关代码上下文
- 调用 Claude Code 执行具体文件操作和命令
- 每次只修改一个关注点，输出 confidence 分数

## 每次执行前必须注入的上下文
1. 项目 CLAUDE.md（规范文件）
2. RAG 检索出的相关代码（top-5 片段）
3. 当前子任务描述和验收标准
4. 前几次失败的原因（如有）

## 输出要求
在每次代码输出末尾附加：
<confidence>8</confidence>  <!-- 0-10，低于 7 自动升级模型 -->
<changed_files>src/pages/products.astro</changed_files>
<summary>新增产品列表页，从 Drupal JSON:API 获取数据</summary>

## 工具权限（allowedTools 白名单）
- Read（读取文件）
- Write（写入文件）
- Bash: npm test, npm run build, drush, composer
- 禁止：rm -rf, DROP TABLE, 修改 .env, 操作生产数据库

## 失败处理
- 同一任务失败 2 次 → 自动升级至 Claude API 重试
- 失败 3 次 → 暂停，通过 Telegram 通知开发者人工介入
```

### Agent 3：Reviewer（审查员）

```markdown
# SOUL.md — Reviewer Agent

## 身份
你是一名高级代码审查工程师，负责在代码合并前进行质量和安全审查。

## 使用模型
qwen2.5-coder:32b

## 审查维度
1. 功能正确性：是否满足任务验收标准
2. 安全性：SQL 注入、XSS、敏感信息泄露、权限越界
3. 规范符合度：是否符合项目 CLAUDE.md 中的编码规范
4. 破坏性变更：是否影响现有功能（需标记）
5. 测试覆盖：新增代码是否有对应测试

## 输出格式
{
  "verdict": "approve|reject",
  "issues": [
    {
      "severity": "critical|major|minor",
      "file": "文件路径",
      "line": 42,
      "description": "问题描述",
      "suggestion": "修改建议"
    }
  ],
  "summary": "整体评价"
}

## 强制拒绝条件（发现任何一条必须 reject）
- 存在安全漏洞（severity: critical）
- 破坏现有测试
- 违反 CLAUDE.md 中的禁止操作
- 硬编码密钥或密码
```

### Agent 4：DevOps（部署工程师）

```markdown
# SOUL.md — DevOps Agent

## 身份
你是一名 DevOps 工程师，负责将通过审查的代码提交、触发 CI/CD 流水线，并监控部署结果。

## 使用模型
qwen3:32b

## 工作流程
1. 接收 Reviewer 的 approve 信号
2. 执行 git add → git commit（生成规范的 commit message）→ git push
3. 监听 GitHub Actions webhook，等待 pipeline 结果（超时 10 分钟）
4. pipeline 成功 → 执行健康检查 → Telegram 通知开发者
5. pipeline 失败 → 自动执行 git revert → Telegram 告警

## Commit Message 规范
类型(范围): 简短描述

详细说明（如有）

任务ID: task_001
执行Agent: Coder
置信度: 8/10

## 健康检查
- HTTP GET /health，期望 200
- 响应时间 < 2s
- 失败则触发回滚

## 通知模板
✅ 部署成功
项目: {project_name}
任务: {task_title}
提交: {commit_hash}
预览: {url}
耗时: {duration}

🚨 部署失败（已回滚）
项目: {project_name}
失败原因: {error}
日志: {github_actions_url}
需要人工介入: 是
```

---

## 四、完整执行流程

### 4.1 一次完整的任务执行（状态机）

```
开发者 Telegram 发送：
"给 Drupal 网站加一个产品展示内容类型，Astro 前端生成产品列表页"
                │
                ▼
[OpenClaw Gateway 接收消息]
[Session Manager 识别开发者身份，加载项目上下文]
                │
                ▼
[Planner Agent 启动]
  qwen3:32b 分析需求
  输出子任务列表：
  - task_001: Drupal 创建产品内容类型（Coder）
  - task_002: 配置 JSON:API 端点（Coder）
  - task_003: Astro 新建 /products 页面（Coder）
  - task_004: 部署上线（DevOps）
  Telegram 回复摘要，等待开发者确认
                │
                ▼（开发者回复"确认"）
[task_001 → Coder Agent]
  RAG 检索项目相关代码
  Claude Code 执行：
    drush en field_ui -y
    drush generate content-type --label="Product"
    drush field:create node.product ...
  输出 confidence: 8
                │
                ▼
[task_001 → Reviewer Agent]
  审查 Drush 操作记录
  检查字段配置完整性
  verdict: approve
                │
                ▼（继续 task_002, task_003...）
                │
                ▼
[task_004 → DevOps Agent]
  git commit -m "feat(drupal+astro): 新增产品展示功能"
  git push → 触发 GitHub Actions
  等待 CI/CD 结果...
  健康检查通过
                │
                ▼
[Telegram 通知]
✅ 部署成功
项目: cmangos-web
任务: 产品展示功能
预览: https://your-domain.com/products
耗时: 12 分钟
```

### 4.2 失败处理流程

```
Coder 生成代码
    │
    ├─ confidence < 7 ──▶ 升级到 DeepSeek API 重试
    │
    ├─ Reviewer reject ──▶ Coder 根据 issues 修复，最多 2 次
    │                       └─ 第 3 次仍失败 ──▶ Telegram 通知人工介入
    │
    ├─ 测试不通过 ──▶ Coder 修复，最多 2 次
    │                 └─ 仍失败 ──▶ Claude API 兜底 + Telegram 告警
    │
    └─ CI/CD 失败 ──▶ DevOps 自动 git revert + Telegram 🚨 告警
```

---

## 五、项目接入规范

每个项目接入 AI 驱动开发，只需准备以下文件：

### 5.1 CLAUDE.md（必须，每个项目根目录）

```markdown
# 项目规范 — [项目名]

## 技术栈
- 后端：Drupal 10.x / PHP 8.2
- 前端：Astro 4.x / React 18
- 数据库：MySQL 8.0
- 部署：Docker Compose + Nginx

## 禁止操作（AI 严格遵守）
- 不得直接操作生产数据库（只能通过 Drush 或 migration）
- 不得修改 .env 和 .env.production 文件
- 不得删除 config/sync 目录下的任何文件
- 不得在未经 Reviewer 审查的情况下 push 到 main 分支

## 代码规范
- PHP：遵循 Drupal Coding Standards
- JS/TS：ESLint + Prettier，配置见 .eslintrc
- Commit：feat/fix/docs/refactor/test 前缀

## 测试要求
- 新功能必须有对应测试（PHPUnit 或 Vitest）
- 不得降低现有测试覆盖率
- npm run build 必须无报错

## 环境变量
- 开发：.env.local
- 生产：通过 Docker secret 注入，不存储在代码库
```

### 5.2 HEARTBEAT.md（可选，项目级监控）

```markdown
# HEARTBEAT.md — [项目名]

- [ ] 检查网站首页 HTTP 状态（期望 200）
- [ ] 检查 Drupal cron 最近执行时间（超过 24h 则告警）
- [ ] 检查 Astro 构建缓存是否过期（超过 7 天则触发重建）
- [ ] 检查 GitHub 是否有未处理的 Dependabot 安全更新
```

---

## 六、部署架构

### 6.1 新加坡 VPS 服务分布

| 服务 | 部署方式 | 端口 | 说明 |
|------|---------|------|------|
| OpenClaw Gateway | systemd 守护进程 | 18789 (WS) | 核心枢纽，常驻运行 |
| Claude Code | npm 全局安装 | — | 被 Coder Agent 调用 |
| GitHub Actions Runner | Docker | — | 自托管 CI/CD Runner |
| Qdrant | Docker | 6333 | RAG 向量数据库 |
| Nginx | 系统级 | 80/443 | 反代 + 静态资源托管 |
| 各项目服务 | Docker Compose | 各异 | 每个项目独立 compose |

### 6.2 Tailscale 网络配置（关键）

```bash
# 国内 PC：让 Ollama 监听 Tailscale 网卡
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"

sudo systemctl daemon-reload && sudo systemctl restart ollama

# 防火墙：只允许 Tailscale IP 段访问 Ollama
sudo ufw allow from 100.64.0.0/10 to any port 11434

# 新加坡 VPS：验证连通性
curl http://$(tailscale ip -4 home-pc):11434/api/tags
```

### 6.3 OpenClaw 安装与启动

```bash
# 新加坡 VPS
npx openclaw onboard   # 交互式引导，配置 Telegram、模型、workspace

# 验证运行状态
openclaw status

# 查看实时日志
openclaw logs --follow

# 注册 Agent（每个 SOUL.md 对应一个 Agent）
openclaw agents add --file ./agents/planner/SOUL.md
openclaw agents add --file ./agents/coder/SOUL.md
openclaw agents add --file ./agents/reviewer/SOUL.md
openclaw agents add --file ./agents/devops/SOUL.md

# 查看已注册 Agent
openclaw agents list
```

### 6.4 CI/CD 流水线

```yaml
# .github/workflows/deploy.yml
name: AI-Driven Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test   # 或 composer test，按项目替换

  deploy:
    needs: test
    runs-on: self-hosted
    steps:
      - name: Deploy
        run: |
          docker compose pull
          docker compose up -d --no-deps --remove-orphans

      - name: Health check
        run: |
          sleep 15
          curl -f http://localhost:${APP_PORT}/health || exit 1

      - name: Notify success via OpenClaw
        if: success()
        run: |
          curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}&text=✅ 部署成功: ${GITHUB_REF_NAME} @ $(date)"

      - name: Rollback and notify failure
        if: failure()
        run: |
          git revert HEAD --no-edit && git push
          curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${CHAT_ID}&text=🚨 部署失败已回滚，请查看: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
```

---

## 七、模型分工与成本控制

| 任务 | 模型 | 位置 | 触发条件 |
|------|------|------|---------|
| 需求规划、文档生成 | qwen3:32b | 本地 4090 | 默认 |
| 代码生成、审查、Debug | qwen2.5-coder:32b | 本地 4090 | 默认 |
| RAG 向量嵌入 | nomic-embed-text | 本地 4090 | 索引时 |
| 复杂推理（备用） | DeepSeek API | 云端 | confidence < 7 |
| 最终兜底 | Claude API | 云端 | 本地连续失败 3 次 |

**预期 token 分布：** 本地 90%+ / 云端 < 10%

---

## 八、安全边界

| 风险 | 防护措施 |
|------|---------|
| AI 误操作生产数据库 | CLAUDE.md 禁止操作 + allowedTools 白名单 |
| Telegram Bot 被滥用 | openclaw.json 白名单 chat_id |
| Prompt 注入攻击 | Reviewer Agent 安全审查，拒绝危险模式 |
| 代码含恶意逻辑 | Reviewer 强制拒绝条件，critical 问题必须人工确认 |
| Ollama 端口暴露 | Tailscale 限制，ufw 只允许 100.64.0.0/10 |
| 密钥泄露 | Reviewer 检测硬编码密钥，发现立即 reject |

---

## 九、快速启动检查清单

```bash
# Step 1：国内 PC — 启动 Ollama
OLLAMA_HOST=0.0.0.0 ollama serve
ollama pull qwen2.5-coder:32b
ollama pull qwen3:32b
ollama pull nomic-embed-text

# Step 2：新加坡 VPS — 安装 OpenClaw
npm install -g openclaw
openclaw onboard

# Step 3：配置 openclaw.json（模型路由 + Telegram）
vim ~/.openclaw/openclaw.json

# Step 4：注册 4 个 Agent
openclaw agents add --file ./agents/planner/SOUL.md
openclaw agents add --file ./agents/coder/SOUL.md
openclaw agents add --file ./agents/reviewer/SOUL.md
openclaw agents add --file ./agents/devops/SOUL.md

# Step 5：为项目创建 CLAUDE.md 和 HEARTBEAT.md

# Step 6：安装 GitHub Actions Self-hosted Runner
# GitHub 仓库 → Settings → Actions → Runners → New self-hosted runner

# Step 7：测试全流程
# 向 Telegram Bot 发送："帮我在首页加一个 Hello World 横幅并部署"
# 预期：12-20 分钟内收到部署成功通知
```

---

## 十、演进路线

| 阶段 | 目标 | 关键动作 |
|------|------|---------|
| Phase 1（当前） | 基础闭环 | OpenClaw + 4 Agent + 单项目跑通全流程 |
| Phase 2 | 去掉人工确认 | Planner 任务列表直接执行，不等确认 |
| Phase 3 | 主动监控修复 | HEARTBEAT 发现线上错误自动提 Issue 并修复 |
| Phase 4 | 多项目并行 | 多 workspace，任务队列支持优先级调度 |
| Phase 5 | Agent 自进化 | Coder Agent 发现重复任务，自动创建新 Skill 写入 ClawHub |

---

*本方案基于真实已部署基础设施设计。OpenClaw (github.com/openclaw/openclaw) 为 MIT 开源协议，所有组件均为真实存在的工具。*
