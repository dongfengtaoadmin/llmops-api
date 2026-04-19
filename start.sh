#!/bin/bash
# -*- coding: utf-8 -*-

# =============================================================================
# LLMOps API 快速启动脚本
# =============================================================================
#
# 【使用方式】
#   ./start.sh              # 开发模式（带热更新）
#   ./start.sh prod         # 生产模式
#   ./start.sh dev 8080     # 开发模式指定端口
#
# 【热更新说明】
#   开发模式下，修改代码后服务器自动重启，无需手动停止再启动
#   注意：部分文件（如配置文件）可能需要手动重启才能生效
# =============================================================================

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
HOST="127.0.0.1"
PORT="${2:-9000}"
MODE="${1:-dev}"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}       LLMOps API 启动工具          ${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓ 检测到虚拟环境，正在激活...${NC}"
    source .venv/bin/activate
else
    echo -e "${YELLOW}⚠ 未检测到 .venv 虚拟环境${NC}"
fi

# 根据模式启动
case "$MODE" in
    prod|production)
        echo -e "${GREEN}🚀 启动生产模式...${NC}"
        echo "   地址: http://$HOST:$PORT"
        echo "   热更新: 关闭"
        echo ""
        python start.py --prod --host $HOST --port $PORT
        ;;
    dev|development|*)
        echo -e "${GREEN}🔧 启动开发模式...${NC}"
        echo "   地址: http://$HOST:$PORT"
        echo "   热更新: 已启用"
        echo -e "${YELLOW}   提示: 修改代码后自动重启，按 Ctrl+C 停止${NC}"
        echo ""
        python start.py --host $HOST --port $PORT
        ;;
esac
