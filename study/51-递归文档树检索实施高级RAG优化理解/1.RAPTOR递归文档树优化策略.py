#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/8/7 11:18
@Author  : thezehui@gmail.com
@File    : 16.RAPTOR递归文档树优化策略.py

RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) 递归文档树优化策略
======================================================================================

一、核心思想
-----------
RAPTOR 是一种高级 RAG 优化策略，通过构建多层递归文档树来改进检索效果。传统的 RAG 只检索
与查询最相似的文档块，而 RAPTOR 会在多个抽象层级上进行检索，既能检索到细粒度的具体信息，
也能检索到粗粒度的宏观概览。

二、整体运行流程
----------------
1. 文档加载与分块
   - 使用 UnstructuredFileLoader 加载多个文档（流浪地球.txt、电商产品数据.txt、API文档.md）
   - 使用 RecursiveCharacterTextSplitter 将文档分割成较小的文本块（chunk_size=500）

2. 递归构建文档树（核心部分）
   - Level 1（叶子层）：
     * 对所有文本块进行嵌入（使用 gte-small 模型）
     * 使用 UMAP + GMM 对嵌入向量进行聚类
     * 对每个聚类中的文本使用 LLM 生成摘要
   - Level 2（中间层）：
     * 对 Level 1 生成的摘要再次进行嵌入、聚类、总结
   - Level 3（根节点层）：
     * 继续对 Level 2 的摘要进行同样的处理
   - 递归终止条件：达到最大层级(n_levels=3) 或 聚类数变为1

3. 聚类算法详解
   - 全局降维(global_cluster_embeddings): 使用 UMAP 将高维嵌入降到指定维度
   - 全局聚类: 使用 GMM + BIC 准则确定最优聚类数
   - 局部聚类: 在每个全局聚类内部再进行细粒度聚类
   - 概率阈值: 如果一个文档属于多个聚类（概率>threshold），会被分配到多个聚类

4. 存储与检索
   - 将所有文本块和各级摘要全部存入向量数据库（Weaviate）
   - 检索时使用 MMR (最大边际相关) 算法，既考虑相关性又考虑多样性
   - 因为同时包含了细粒度（原始块）和粗粒度（摘要）的信息，检索更全面

三、为什么需要递归摘要？
-----------------------
1. 解决长文档跨段落理解问题：单个文档块可能只包含部分信息，摘要可以整合多个块的信息
2. 多粒度检索：不同层级代表不同抽象级别，可以回答不同类型的问题
3. 减少检索噪声：通过摘要层级的过滤，可以减少不相关内容的干扰

四、示例：假设有100个文档块
   Level 1: 100个块 → 聚类成10个组 → 生成10个摘要
   Level 2: 10个摘要 → 聚类成3个组 → 生成3个摘要
   Level 3: 3个摘要 → 聚类成1个组 → 生成1个摘要
   最终向量库包含: 100个原始块 + 10+3+1=14个摘要 = 114条文本
"""
from typing import Optional

import dotenv
import numpy as np
import pandas
import pandas as pd
import umap
import weaviate
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_weaviate import WeaviateVectorStore
from sklearn.mixture import GaussianMixture
from weaviate.auth import AuthApiKey

dotenv.load_dotenv()

# 1.定义随机数种子、文本嵌入模型、大语言模型、向量数据库
RANDOM_SEED = 224
embd = HuggingFaceEmbeddings(
    model_name="thenlper/gte-small",
    cache_folder="./embeddings/",
    encode_kwargs={"normalize_embeddings": True},
)
model = ChatOpenAI(model="gpt-3.5-turbo-16k", temperature=0)
db = WeaviateVectorStore(
    client=weaviate.connect_to_local("localhost", "8080"),
    index_name="RaptorRAG",
    text_key="text",
    embedding=embd,
)


def global_cluster_embeddings(
        embeddings: np.ndarray, dim: int, n_neighbors: Optional[int] = None, metric: str = "cosine",
) -> np.ndarray:
    """
    使用UMAP对传递嵌入向量进行全局降维

    作用：在进行聚类之前，首先将高维嵌入向量降到低维，这样可以：
    1. 加快聚类速度
    2. 减少噪声的影响
    3. 使聚类结果更稳定

    :param embeddings: 需要降维的嵌入向量
    :param dim: 降低后的维度
    :param n_neighbors: 每个向量需要考虑的邻居数量，如果没有提供默认为嵌入数量的开方
    :param metric: 用于UMAP的距离度量，默认为余弦相似性
    :return: 一个降维到指定维度的numpy嵌入数组
    """
    if n_neighbors is None:
        n_neighbors = int((len(embeddings) - 1) ** 0.5)
    return umap.UMAP(n_neighbors=n_neighbors, n_components=dim, metric=metric).fit_transform(embeddings)


def local_cluster_embeddings(
        embeddings: np.ndarray, dim: int, n_neighbors: int = 10, metric: str = "cosine",
) -> np.ndarray:
    """
    使用UMAP对嵌入进行局部降维处理，通常在全局聚类之后进行。

    局部降维 vs 全局降维的区别:
    - 全局降维: 考虑所有数据点的全局结构，适合发现整体模式
    - 局部降维: 在已分割的子集上单独降维，保留局部邻域的结构
    这里先用全局降维划分大区域，再在每个区域内用局部降维细分

    :param embeddings: 需要降维的嵌入向量
    :param dim: 降低后的维度
    :param n_neighbors: 每个向量需要考虑的邻居数量（默认10，比全局多）
    :param metric: 用于UMAP的距离度量，默认为余弦相似性
    :return: 一个降维到指定维度的numpy嵌入数组
    """
    return umap.UMAP(
        n_neighbors=n_neighbors, n_components=dim, metric=metric,
    ).fit_transform(embeddings)


def get_optimal_clusters(
        embeddings: np.ndarray, max_clusters: int = 50, random_state: int = RANDOM_SEED,
) -> int:
    """
    使用高斯混合模型结合贝叶斯信息准则（BIC）确定最佳的聚类数目。

    原理：BIC (Bayesian Information Criterion) 会在模型复杂度和拟合度之间寻求平衡。
    BIC = -2 * log(L) + k * log(n)
    - log(L): 对数似然（模型拟合程度）
    - k: 模型参数数量
    - n: 样本数量

    BIC 值越低，表示聚类效果越好（既不过拟合也不欠拟合）

    :param embeddings: 需要聚类的嵌入向量
    :param max_clusters: 最大聚类数
    :param random_state: 随机数
    :return: 返回最优聚类数
    """
    # 1.获取最大聚类树，最大聚类数不能超过嵌入向量的数量
    max_clusters = min(max_clusters, len(embeddings))
    n_clusters = np.arange(1, max_clusters)

    # 2.逐个设置聚类树并找出最优聚类数
    bics = []
    for n in n_clusters:
        # 3.创建高斯混合模型，并计算聚类结果
        gm = GaussianMixture(n_components=n, random_state=random_state)
        gm.fit(embeddings)
        bics.append(gm.bic(embeddings))

    return n_clusters[np.argmin(bics)]


def gmm_cluster(embeddings: np.ndarray, threshold: float, random_state: int = 0) -> tuple[list, int]:
    """
    使用基于概率阈值的高斯混合模型（GMM）对嵌入进行聚类。

    与传统硬聚类（如K-Means）不同，GMM是软聚类，给出每个样本属于各个聚类的概率。
    这里使用阈值来允许一个文档属于多个聚类（概率 > threshold），这对于边界模糊的文档很有用。

    :param embeddings: 需要聚类的嵌入向量（降维）
    :param threshold: 概率阈值（默认0.1，即概率>10%的聚类都算属于该聚类）
    :param random_state: 用于可重现的随机性种子
    :return: 包含聚类标签和确定聚类数目的元组
    """
    # 1.获取最优聚类数
    n_clusters = get_optimal_clusters(embeddings)

    # 2.创建高斯混合模型对象并嵌入数据
    gm = GaussianMixture(n_components=n_clusters, random_state=random_state)
    gm.fit(embeddings)

    # 3.预测每个样本属于各个聚类的概率
    probs = gm.predict_proba(embeddings)

    # 4.根据概率阈值确定每个嵌入的聚类标签
    labels = [np.where(prob > threshold)[0] for prob in probs]

    # 5.返回聚类标签和聚类数目
    return labels, n_clusters


def perform_clustering(embeddings: np.ndarray, dim: int, threshold: float) -> list[np.ndarray]:
    """
    对嵌入进行聚类，首先全局降维，然后使用高斯混合模型进行聚类，最后在每个全局聚类中进行局部聚类。

    两阶段聚类的好处:
    1. 全局聚类: 将所有文档分成几个大类，发现宏观主题结构
    2. 局部聚类: 在每个大类内部再细分，发现更精细的子主题
    3. 这种层次化的聚类方式比直接对所有数据聚类更稳定

    示例:
    假设有100个文档：
    - 全局聚类: 分成3大类 (科技、商业、娱乐)
    - 局部聚类: 每个大类内部再细分
      * 科技类 → 5个子类 (AI、硬件、软件...)
      * 商业类 → 4个子类 (金融、零售...)
      * 娱乐类 → 3个子类 (电影、音乐...)
    - 最终: 100个文档被分配到12个细粒度聚类中

    :param embeddings: 需要执行操作的嵌入向量列表
    :param dim: 指定的降维维度
    :param threshold: 概率阈值（默认0.1，允许一个文档属于多个聚类）
    :return: 包含每个嵌入的聚类ID的列表，每个数组代表一个嵌入的聚类标签。
    """
    # 1.检测传入的嵌入向量，当数据量不足时不进行聚类
    if len(embeddings) <= dim + 1:
        return [np.array([0]) for _ in range(len(embeddings))]

    # 2.调用函数进行全局降维
    reduced_embeddings_global = global_cluster_embeddings(embeddings, dim)

    # 3.对降维后的数据进行全局聚类
    global_clusters, n_global_clusters = gmm_cluster(reduced_embeddings_global, threshold)

    # 4.初始化一个空列表，用于存储所有嵌入的局部聚类标签
    all_local_clusters = [np.array([]) for _ in range(len(embeddings))]
    total_clusters = 0

    # 5.遍历每个全局聚类以执行局部聚类
    for i in range(n_global_clusters):
        # 6.提取属于当前全局聚类的嵌入向量
        global_cluster_embeddings_ = embeddings[
            np.array([i in gc for gc in global_clusters])
        ]

        # 7.如果当前全局聚类中没有嵌入向量则跳过循环
        if len(global_cluster_embeddings_) == 0:
            continue

        # 8.如果当前全局聚类中的嵌入量很少，直接将它们分配到一个聚类中
        if len(global_cluster_embeddings_) <= dim + 1:
            local_clusters = [np.array([0]) for _ in global_cluster_embeddings_]
            n_local_clusters = 1
        else:
            # 9.执行局部降维和聚类
            reduced_embeddings_local = local_cluster_embeddings(global_cluster_embeddings_, dim)
            local_clusters, n_local_clusters = gmm_cluster(reduced_embeddings_local, threshold)

        # 10.分配局部聚类ID，调整已处理的总聚类数目
        for j in range(n_local_clusters):
            local_cluster_embeddings_ = global_cluster_embeddings_[
                np.array([j in lc for lc in local_clusters])
            ]
            indices = np.where(
                (embeddings == local_cluster_embeddings_[:, None]).all(-1)
            )[1]
            for idx in indices:
                all_local_clusters[idx] = np.append(all_local_clusters[idx], j + total_clusters)

        total_clusters += n_local_clusters

    return all_local_clusters


def embed(texts: list[str]) -> np.ndarray:
    """
    将传递的的文本列表转换成嵌入向量列表

    嵌入(Embedding)是将文本转换为数值向量的过程，使语义相似的文本在向量空间中距离相近。
    这里使用的是 HuggingFace 的 gte-small 模型，是一个轻量但效果不错的中文支持模型。

    :param texts: 需要转换的文本列表
    :return: 生成的嵌入向量列表并转换成numpy数组
    """
    text_embeddings = embd.embed_documents(texts)
    return np.array(text_embeddings)


def embed_cluster_texts(texts: list[str]) -> pandas.DataFrame:
    """
    对文本列表进行嵌入和聚类,并返回一个包含文本、嵌入和聚类标签的数据框。
    该函数将嵌入生成和聚类结合成一个步骤。

    返回的DataFrame结构:
    ┌──────┬─────────────────────────────┬────────────────────┬─────────────┐
    │ index│ text                       │ embd               │ cluster     │
    ├──────┼─────────────────────────────┼────────────────────┼─────────────┤
    │  0   │ 文本内容1                   │ [0.1, 0.3, ...]   │ [0, 3]     │
    │  1   │ 文本内容2                   │ [0.2, 0.1, ...]   │ [1]         │
    │  2   │ 文本内容3                   │ [0.5, 0.8, ...]   │ [2, 5]     │
    └──────┴─────────────────────────────┴────────────────────┴─────────────┘
    注意: cluster列是一个数组，一个文本可能属于多个聚类（软聚类）

    :param texts: 需要处理的文本列表
    :return: 返回包含文本、嵌入和聚类标签的数据框
    """
    text_embeddings_np = embed(texts)
    cluster_labels = perform_clustering(text_embeddings_np, 10, 0.1)
    df = pd.DataFrame()
    df["text"] = texts
    df["embd"] = list(text_embeddings_np)
    df["cluster"] = cluster_labels
    return df


def fmt_txt(df: pd.DataFrame) -> str:
    """
    将数据框中的文本格式化成单个字符串

    作用：将同一聚类中的多个文本块合并成一个字符串，
    作为LLM生成摘要的上下文输入。

    例如:
    输入: ["第一段内容", "第二段内容", "第三段内容"]
    输出: "第一段内容 --- --- \n --- --- 第二段内容 --- --- \n --- --- 第三段内容"

    :param df: 需要处理的数据框，内部涵盖text、embd、cluster三个字段
    :return: 返回合并格式化后的字符串
    """
    unique_txt = df["text"].tolist()
    return "--- --- \n --- ---".join(unique_txt)


def embed_cluster_summarize_texts(texts: list[str], level: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    对传入的文本列表进行嵌入、聚类和总结。
    该函数首先问文本生成嵌入，基于相似性对他们进行聚类，扩展聚类分配以便处理，然后总结每个聚类中的内容。

    处理流程:
    1. 嵌入: 使用embedding模型将文本转为向量
    2. 聚类: 对嵌入向量执行两阶段聚类（全局+局部）
    3. 扩展: 将文本-聚类关系展开（一个文本可能属于多个聚类）
    4. 摘要: 对每个聚类中的所有文本用LLM生成摘要

    :param texts: 需要处理的文本列表
    :param level: 一个整数，可以定义处理的深度（用于标识当前是第几层递归）
    :return: 包含两个数据框的元组
    - 第一个 DataFrame (df_clusters) 包括原始文本、它们的嵌入以及聚类分配。
    - 第二个 DataFrame (df_summary) 包含每个聚类的摘要信息、指定的处理级别以及聚类标识符。
    """
    # 1.嵌入和聚类文本，生成包含text、embd、cluster的数据框
    df_clusters = embed_cluster_texts(texts)

    # 2.定义变量，用于扩展数据框，以便更方便地操作聚类
    expanded_list = []

    # 3.扩展数据框条目，将文档和聚类配对，便于处理
    for index, row in df_clusters.iterrows():
        for cluster in row["cluster"]:
            expanded_list.append(
                {"text": row["text"], "embd": row["embd"], "cluster": cluster}
            )

    # 4.从扩展列表创建一个新的数据框
    expanded_df = pd.DataFrame(expanded_list)

    # 5.获取唯一的聚类标识符以进行处理
    all_clusters = expanded_df["cluster"].unique()

    # 6.创建汇总Prompt、汇总链
    template = """Here is a sub-set of LangChain Expression Language doc. 

    LangChain Expression Language provides a way to compose chain in LangChain.

    Give a detailed summary of the documentation provided.

    Documentation:
    {context}
    """
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model | StrOutputParser()

    # 7.格式化每个聚类中的文本以进行总结
    summaries = []
    for i in all_clusters:
        df_cluster = expanded_df[expanded_df["cluster"] == i]
        formatted_txt = fmt_txt(df_cluster)
        summaries.append(chain.invoke({"context": formatted_txt}))

    # 8.创建一个DataFrame来存储总结及其对应的聚类和级别
    df_summary = pd.DataFrame(
        {
            "summaries": summaries,
            "level": [level] * len(summaries),
            "cluster": list(all_clusters),
        }
    )

    return df_clusters, df_summary


def recursive_embed_cluster_summarize(
        texts: list[str], level: int = 1, n_levels: int = 3,
) -> dict[int, tuple[pd.DataFrame, pd.DataFrame]]:
    """
    递归地嵌入、聚类和总结文本，直到达到指定的级别或唯一聚类数变为1，将结果存储在每个级别处。

    递归流程示例（假设n_levels=3）：
    ┌─────────────────────────────────────────────────────────┐
    │  Level 1: [文本1, 文本2, 文本3, ... 文本100]           │
    │           ↓ 嵌入+聚类                                  │
    │           [聚类1: 文本1-10] → 摘要A                     │
    │           [聚类2: 文本11-25] → 摘要B                    │
    │           [聚类3: 文本26-40] → 摘要C                    │
    │           ... (共10个聚类，生成10个摘要)                │
    └─────────────────────────────────────────────────────────┘
                            ↓
    ┌─────────────────────────────────────────────────────────┐
    │  Level 2: [摘要A, 摘要B, 摘要C, ... 摘要J]            │
    │           ↓ 嵌入+聚类                                   │
    │           [聚类1: 摘要A-D] → 摘要α                      │
    │           [聚类2: 摘要E-H] → 摘要β                      │
    │           [聚类3: 摘要I-J] → 摘要γ                       │
    │           (共3个聚类，生成3个摘要)                      │
    └─────────────────────────────────────────────────────────┘
                            ↓
    ┌─────────────────────────────────────────────────────────┐
    │  Level 3: [摘要α, 摘要β, 摘要γ]                        │
    │           ↓ 嵌入+聚类                                    │
    │           [聚类1: 全部摘要] → 摘要Ω                      │
    │           (共1个聚类，生成1个摘要)                       │
    └─────────────────────────────────────────────────────────┘

    :param texts: 要处理的文本列表
    :param level: 当前递归级别（从1开始）
    :param n_levels: 递归地最大深度（默认为3）
    :return: 一个字典，其中键是递归级别，值是包含该级别处聚类DataFrame和总结DataFrame的元组。
    """
    # 1.定义字典用于存储每个级别处的结果
    results = {}

    # 2.对当前级别执行嵌入、聚类和总结
    df_clusters, df_summary = embed_cluster_summarize_texts(texts, level)

    # 3.存储当前级别的结果
    results[level] = (df_clusters, df_summary)

    # 4.确定是否可以继续递归并且有意义
    unique_clusters = df_summary["cluster"].nunique()
    if level < n_levels and unique_clusters > 1:
        # 5.使用总结作为下一级递归的输入文本
        new_texts = df_summary["summaries"].tolist()
        next_level_results = recursive_embed_cluster_summarize(
            new_texts, level + 1, n_levels
        )

        # 6.将下一级的结果合并到当前结果字典中
        results.update(next_level_results)

    return results


# ============================================================================
# 代码执行流程详解
# ============================================================================

# 步骤1: 定义文档加载器、文本分割器
# ------------------------------------------------
# - UnstructuredFileLoader: 从指定路径加载非结构化文档（支持txt、md等格式）
# - RecursiveCharacterTextSplitter: 递归分割文本，按separator列表依次尝试分割
#   * chunk_size=500: 每个文本块最大500个字符
#   * chunk_overlap=0: 块之间不重叠
#   * separators: 按优先级尝试的分隔符（先尝试大的段落分隔符，再尝试句子、单词）
#   * is_separator_regex=True: 使用正则表达式匹配分隔符（支持中文标点）

loaders = [
    UnstructuredFileLoader("./流浪地球.txt"),
    UnstructuredFileLoader("./电商产品数据.txt"),
    UnstructuredFileLoader("./项目API文档.md"),
]
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=0,
    separators=["\n\n", "\n", "。|！|？", "\.\s|\!\s|\?\s", "；|;\s", "，|,\s", " ", ""],
    is_separator_regex=True,
)

# 步骤2: 循环分割并加载文本
# ------------------------------------------------
# 遍历每个加载器，调用load_and_split方法：
# 1. load(): 加载整个文档
# 2. split(): 使用text_splitter分割成小块
# 最终docs列表包含所有文档的所有文本块

docs = []
for loader in loaders:
    docs.extend(loader.load_and_split(text_splitter))

# 步骤3: 构建文档树（递归嵌入-聚类-摘要）
# ------------------------------------------------
# 这是RAPTOR的核心步骤，会构建多层文档树：
# - 输入: 所有原始文本块（叶子节点）
# - 处理: 对每个层级执行嵌入→聚类→生成摘要
# - 输出: 包含3个层级的结果字典

leaf_texts = [doc.page_content for doc in docs]  # 提取所有文本块的内容
results = recursive_embed_cluster_summarize(leaf_texts, level=1, n_levels=3)

# results字典结构:
# {
#     1: (df_clusters_level1, df_summary_level1),  # Level 1: 原始块聚类结果+摘要
#     2: (df_clusters_level2, df_summary_level2),  # Level 2: Level1摘要的聚类结果+摘要
#     3: (df_clusters_level3, df_summary_level3),  # Level 3: Level2摘要的聚类结果+摘要
# }

# 步骤4: 提取所有层级的文本并合并
# ------------------------------------------------
# 将原始文本块（叶子节点）和所有层级的摘要都收集起来
# 这样检索时可以同时检索到细粒度和粗粒度的信息

all_texts = leaf_texts.copy()  # 先复制原始文本块
for level in sorted(results.keys()):
    # 遍历每个层级，取出该层级的所有摘要
    summaries = results[level][1]["summaries"].tolist()
    all_texts.extend(summaries)  # 追加到列表中

# 步骤5: 将所有文本存入向量数据库
# ------------------------------------------------
# 这里将原始文本块 + Level1摘要 + Level2摘要 + Level3摘要 全部存入
# 优点: 检索时可以根据相似度匹配到最相关的内容，无论它是原始块还是某个层级的摘要

db.add_texts(all_texts)

# 步骤6: 执行相似性检索（使用MMR算法）
# ------------------------------------------------
# MMR (Maximum Marginal Relevance) 最大边际相关算法:
# - 不仅考虑与查询的相关性
# - 还考虑结果之间的多样性
# - 避免返回过于相似的多个结果
#
# 检索流程:
# 1. 计算查询与所有文本的相似度
# 2. 选择最相关的文本
# 3. 同时考虑已选结果，尽量选择与已选结果不同的内容
# 4. 重复直到选够所需数量的结果

retriever = db.as_retriever(search_type="mmr")
search_docs = retriever.invoke("流浪地球中的人类花了多长时间才流浪到新的恒星系？")

print(search_docs)
print(len(search_docs))
