# 使用 Ubuntu 22.04 作为基底
FROM ubuntu:22.04

# 设置非交互模式
ENV DEBIAN_FRONTEND=noninteractive

# 1. 安装基础工具并添加 PHP PPA (修正拼写为 ppa:ondrej/php)
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    git \
    unzip \
    gnupg2 \
    ca-certificates \
    && add-apt-repository ppa:ondrej/php -y \
    && apt-get update

# 2. 安装 PHP 8.2 核心组件 (针对 Drupal 10)
RUN apt-get install -y \
    php8.2-cli \
    php8.2-common \
    php8.2-mysql \
    php8.2-zip \
    php8.2-gd \
    php8.2-mbstring \
    php8.2-curl \
    php8.2-xml \
    php8.2-bcmath

# 3. 安装 Composer 和 Drush
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
RUN curl -fsSL -o /usr/local/bin/drush https://github.com/drush-ops/drush-launcher/releases/latest/download/drush.phar \
    && chmod +x /usr/local/bin/drush

# 4. 安装 Node.js 20 和 pnpm (针对 Astro)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm

# 5. 清理缓存并设置用户
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN useradd -m -u 1000 openclaw
USER openclaw

CMD ["tail", "-f", "/dev/null"]
