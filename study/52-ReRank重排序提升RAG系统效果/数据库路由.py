from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
import dotenv
dotenv.load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 模拟不同数据库的检索函数
@tool
def search_mysql(query: str) -> str:
    """查询结构化业务数据，如订单、用户、产品信息"""
    print(f"查询结构化业务数据，如订单、用户、产品信息: {query}111111")
    return f"[MySQL结果] 关于 '{query}' 的结构化数据..."

@tool
def search_elasticsearch(query: str) -> str:
    """全文搜索文档、新闻、日志等非结构化文本"""
    return f"[ES结果] 关于 '{query}' 的全文搜索结果..."

@tool
def search_vector_db(query: str) -> str:
    """语义向量检索，适合知识库、FAQ、语义相似问题"""
    return f"[向量库结果] 关于 '{query}' 的语义相关内容..."

# Agent 会根据问题自动选择工具（即数据库路由）
tools = [search_mysql, search_elasticsearch, search_vector_db]

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个智能助手，根据用户问题选择合适的数据源进行检索，然后综合回答。"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# 测试
result = agent_executor.invoke({"input": "查询用户ID为123的最近订单"})
print(result["output"])