# 使用 Ubuntu 作为基底，方便调试和扩展
FROM ubuntu:22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

# 1. 安装基础工具和 PHP 8.2 (针对 Drupal 10)
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    git \
    unzip \
    && add-apt-repository pnpm:ondrej/php -y \
    && apt-get update && apt-get install -y \
    php8.2-cli \
    php8.2-common \
    php8.2-mysql \
    php8.2-zip \
    php8.2-gd \
    php8.2-mbstring \
    php8.2-curl \
    php8.2-xml \
    php8.2-bcmath \
    && rm -rf /var/lib/apt/lists/*

# 2. 安装 Composer 和 Drush (Drupal 核心工具)
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
RUN curl -fsSL -o /usr/local/bin/drush https://github.com/drush-ops/drush-launcher/releases/latest/download/drush.phar \
    && chmod +x /usr/local/bin/drush

# 3. 安装 Node.js 20 & Pnpm (针对 Astro 前端)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm

# 4. 设置工作目录
WORKDIR /app

# 5. 创建非 root 用户 (安全考量)
# 确保 UID/GID 与你 VPS 上的用户一致，防止挂载权限问题
RUN useradd -m -u 1000 openclaw
USER openclaw

# 保持容器运行，等待 OpenClaw 指令
CMD ["tail", "-f", "/dev/null"]
