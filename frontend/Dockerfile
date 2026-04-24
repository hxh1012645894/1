# ============================================================
# Vue 3 + Vite 前端 Dockerfile
# 多阶段构建: Node.js 打包 -> Nginx 运行
# ============================================================

# ============ 阶段1: 构建 ============
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json* ./

# 安装依赖
RUN npm ci --prefer-offline --no-audit || npm install

# 复制源代码
COPY . .

# 设置生产环境变量
ENV NODE_ENV=production

# 执行构建，产物输出到 /app/dist
RUN npm run build

# ============ 阶段2: 生产运行 ============
FROM nginx:alpine AS production

# 复制自定义 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制打包产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 健康检查：检查 nginx 是否正常运行
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]