# OpenClaw 项目灵魂法则 (Project Soul)

> 本文件是所有 Agent 执行任务的最高宪法。修改本文件需经过 Reviewer 确认。

## 1. 环境上下文 (Environment)
- **容器名称**: `openclaw-sandbox`
- **操作用户**: `openclaw` (UID: 1000)
- **根目录**: `/app` (对应宿主机 `/root/AI/cmangos-web`)

## 2. 核心技术架构
- **后端**: Drupal 10 (PHP 8.2), 强制使用 **Drush** 进行配置管理。
- **前端**: Astro (SSR), 使用 **Pnpm** 进行包管理。
- **配置同步**: 所有 Drupal 变更必须通过 `drush cex` 导出至 `config/sync`。

## 3. Agent 行动守则
- **优先观察**: 在执行修改前，必须先执行 `ls -R` 或 `cat` 相关文件。
- **原子修改**: 严禁大面积重写文件，优先使用 `sed` 或局部覆盖。
- **即时验证**: 每次代码变更后，必须在容器内运行相关的 `lint` 或 `check` 命令。
- **权限意识**: 确保所有新创建的文件归属为 `openclaw:openclaw`。

## 4. 禁令 (Forbidden)
- 严禁在没有备份的情况下直接修改 `settings.php`。
- 严禁在容器内运行 `sudo` 或尝试安装系统级软件包。
- 严禁将 API Keys 或敏感密码写入代码库。
