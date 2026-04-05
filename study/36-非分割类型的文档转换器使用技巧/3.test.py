from langchain_community.document_transformers import DoctranTextTranslator
from langchain_core.documents import Document
import dotenv
dotenv.load_dotenv()
# 1. 准备要翻译的文档
documents = [Document(page_content="Hello, this is a document about AI.")]

# 2. 初始化翻译器，设置目标语言为西班牙语
translator = DoctranTextTranslator(openai_api_model="gpt-4o-mini",language="zh-CN")

# 3. 执行翻译
translated_docs = translator.transform_documents(documents)

# 4. 查看翻译结果
print(translated_docs[0].page_content)
# 输出类似: "Hola, este es un documento sobre IA."