"""RAG 服务：文档分块、向量化、检索、问答。
向量化用本地 bge（与公司向量同源），问答用当前激活的在线/本地 LLM。
"""
import asyncio
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 复用 analyzer 里已加载的本地 embedding 模型，避免重复加载
from app.services.analyzer import embeddings
from app.services.llm import get_llms

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
)


def split_text(text: str) -> List[str]:
    chunks = _splitter.split_text(text or "")
    # 过滤过短的碎块
    return [c.strip() for c in chunks if c and len(c.strip()) >= 30]


async def embed_documents(texts: List[str]) -> List[List[float]]:
    """批量向量化（CPU 密集，放线程池避免阻塞事件循环）。"""
    return await asyncio.to_thread(embeddings.embed_documents, texts)


async def embed_query(text: str) -> List[float]:
    return await asyncio.to_thread(embeddings.embed_query, text)


_answer_prompt = PromptTemplate(
    template=(
        "你是 AI-BOS 的公司情报分析助手。请**仅根据**下面提供的资料片段回答用户的问题。\n"
        "规则：\n"
        "- 只用资料中的事实，不要编造；资料中没有就明确说\"根据现有资料无法确定\"。\n"
        "- 用与问题相同的语言作答（中文问就中文答）。\n"
        "- 回答要具体、可引用数字；适当总结，不要照抄大段原文。\n\n"
        "公司：{company}\n\n"
        "==== 资料片段 ====\n{context}\n==== 资料结束 ====\n\n"
        "{history}用户问题：{question}\n\n回答："
    ),
    input_variables=["company", "context", "history", "question"],
)


async def answer(company_name: str, question: str, chunks: List[str], history_text: str = "") -> str:
    _, text_llm = get_llms()
    context = "\n\n---\n\n".join(chunks) if chunks else "(无相关资料)"
    chain = _answer_prompt | text_llm | StrOutputParser()
    return await chain.ainvoke({
        "company": company_name,
        "context": context,
        "history": history_text,
        "question": question,
    })
