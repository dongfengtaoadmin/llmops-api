python -m venv .venv
source .venv/bin/activate

启动步骤
1. 进入项目目录
cd /Users/apple/Desktop/code/LLMOps/llmops-api
2.（可选）激活虚拟环境
若项目里有 env/ 虚拟环境：

source env/bin/activate
3. 安装依赖
pip install -r requirements.txt
4. 启动服务
python -m app.http.app




启动方式：
                                                                                                                                                                                                             
# 开发模式（带热更新）
python start.py                                                                                                                                                                                            
                                                        
# 生产模式
python start.py --prod

# 指定端口
python start.py --port 8080

或者使用 shell 脚本：

./start.sh        # 开发模式
./start.sh prod   # 生产模式






















