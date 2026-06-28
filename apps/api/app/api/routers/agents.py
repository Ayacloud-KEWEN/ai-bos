"""Agent Studio（Module 4）：可配置 AI 助手 + 对话（可选公司知识库 RAG）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.database import get_db
from app.models.agent import Agent
from app.models.knowledge import KnowledgeChunk
from app.models.knowledge_base import KnowledgeBaseChunk
from app.models.company import Company
from app.services import rag
from app.services.llm import build_text_llm

router = APIRouter()

# 预设助手模板（规范 Agent Types 节选）
TEMPLATES = [
    {"key": "cfo", "name": "AI CFO Assistant", "role": "AI CFO Assistant", "icon": "Wallet",
     "goal": "分析财务表现、现金流与风险，给出 CFO 级建议。",
     "system_prompt": "你是 CFA 级别的 AI 财务总监助手。基于提供的资料分析财务健康、盈利、现金流与风险，"
                      "解释数字背后的含义，给出可执行的财务建议。不要编造数字。用提问的语言作答。"},
    {"key": "strategy", "name": "AI Strategy Consultant", "role": "AI Strategy Consultant", "icon": "Compass",
     "goal": "提供战略选项与建议，按影响力/可行性排序。",
     "system_prompt": "你是前麦肯锡合伙人。运用 SWOT、波特五力等框架，给出战略选项并按影响力、可行性、风险排序。"
                      "结论要具体、可落地。用提问的语言作答。"},
    {"key": "sales", "name": "AI Sales Director", "role": "AI Sales Director", "icon": "Target",
     "goal": "识别 ICP、痛点、买点与销售机会。",
     "system_prompt": "你是企业销售总监。判断谁会买、为何买、有何痛点、如何赢单，给出可执行的销售情报。用提问的语言作答。"},
    {"key": "market", "name": "AI Market Analyst", "role": "AI Market Research Analyst", "icon": "Globe",
     "goal": "估算市场规模、增长、趋势与壁垒。",
     "system_prompt": "你是资深市场研究顾问。估算 TAM/SAM/SOM、增长率、驱动与壁垒；估算需明确标注、不杜撰精确数字。用提问的语言作答。"},
    {"key": "dd", "name": "AI Due Diligence Analyst", "role": "AI Due Diligence Analyst", "icon": "ShieldCheck",
     "goal": "评估投资/收购的财务、法律、运营、商业、技术风险。",
     "system_prompt": "你是尽职调查分析师。从五大风险维度评估投资/收购标的，指出红旗与机会，给出明确建议。用提问的语言作答。"},
]


@router.get("/templates", tags=["Agents"])
async def list_templates():
    return {"templates": TEMPLATES}


class AgentInput(BaseModel):
    name: str
    role: str | None = None
    goal: str | None = None
    system_prompt: str | None = None
    provider: str | None = ""
    temperature: float | None = 0.3
    knowledge_company_id: str | None = None
    use_knowledge_base: bool | None = None
    icon: str | None = "Bot"


def _card(a: Agent) -> dict:
    return {"id": a.id, "name": a.name, "role": a.role, "goal": a.goal,
            "system_prompt": a.system_prompt, "provider": a.provider, "temperature": a.temperature,
            "knowledge_company_id": a.knowledge_company_id, "use_knowledge_base": bool(a.use_knowledge_base),
            "icon": a.icon}


@router.post("", tags=["Agents"])
async def create_agent(body: AgentInput, db: AsyncSession = Depends(get_db)):
    a = Agent(name=body.name, role=body.role, goal=body.goal, system_prompt=body.system_prompt or "",
              provider=body.provider or "", temperature=body.temperature or 0.3,
              knowledge_company_id=body.knowledge_company_id,
              use_knowledge_base=bool(body.use_knowledge_base), icon=body.icon or "Bot")
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return {"id": a.id}


@router.post("/from-template/{key}", tags=["Agents"])
async def create_from_template(key: str, db: AsyncSession = Depends(get_db)):
    tpl = next((t for t in TEMPLATES if t["key"] == key), None)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    a = Agent(name=tpl["name"], role=tpl["role"], goal=tpl["goal"],
              system_prompt=tpl["system_prompt"], icon=tpl["icon"])
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return {"id": a.id}


@router.get("", tags=["Agents"])
async def list_agents(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Agent).order_by(Agent.created_at.desc()))).scalars().all()
    return [_card(a) for a in rows]


@router.get("/{agent_id}", tags=["Agents"])
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    kn = None
    if a.knowledge_company_id:
        c = (await db.execute(select(Company).where(Company.id == a.knowledge_company_id))).scalar_one_or_none()
        kn = c.name if c else None
    return {**_card(a), "knowledge_company_name": kn}


@router.patch("/{agent_id}", tags=["Agents"])
async def update_agent(agent_id: str, body: AgentInput, db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    for f in ("name", "role", "goal", "system_prompt", "provider", "temperature", "knowledge_company_id", "use_knowledge_base", "icon"):
        v = getattr(body, f)
        if v is not None:
            setattr(a, f, v)
    await db.commit()
    return {"msg": "updated"}


@router.delete("/{agent_id}", tags=["Agents"])
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(sa_delete(Agent).where(Agent.id == agent_id))
    await db.commit()
    return {"msg": "deleted"}


_agent_prompt = PromptTemplate(
    template="{system}\n\n{knowledge}{history}用户：{question}\n\n助手：",
    input_variables=["system", "knowledge", "history", "question"],
)


class ChatMsg(BaseModel):
    role: str
    content: str


class AgentChatInput(BaseModel):
    question: str
    history: list[ChatMsg] | None = None


@router.post("/{agent_id}/chat", tags=["Agents"])
async def chat(agent_id: str, body: AgentChatInput, db: AsyncSession = Depends(get_db)):
    a = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty question")

    sources = []
    snippets = []
    if a.knowledge_company_id or a.use_knowledge_base:
        qvec = await rag.embed_query(q)
        if a.knowledge_company_id:
            rows = (await db.execute(
                select(KnowledgeChunk).where(KnowledgeChunk.company_id == a.knowledge_company_id)
                .order_by(KnowledgeChunk.embedding.cosine_distance(qvec)).limit(5)
            )).scalars().all()
            for r in rows:
                snippets.append(r.content); sources.append({"snippet": r.content[:160], "source": "company"})
        if a.use_knowledge_base:
            kb = (await db.execute(
                select(KnowledgeBaseChunk).order_by(KnowledgeBaseChunk.embedding.cosine_distance(qvec)).limit(5)
            )).scalars().all()
            for r in kb:
                snippets.append(f"[{r.title}] {r.content}")
                sources.append({"snippet": r.content[:160], "source": "knowledge_base", "title": r.title})
    knowledge = ("可参考资料（仅据此回答相关问题）：\n" + "\n---\n".join(snippets) + "\n\n") if snippets else ""

    history_text = ""
    if body.history:
        recent = body.history[-6:]
        history_text = "\n".join(f"{'用户' if m.role == 'user' else '助手'}：{m.content}" for m in recent) + "\n"

    system = a.system_prompt or f"你是 {a.role or a.name}。"
    llm = build_text_llm(a.provider, a.temperature or 0.3)
    chain = _agent_prompt | llm | StrOutputParser()
    answer = await chain.ainvoke({"system": system, "knowledge": knowledge, "history": history_text, "question": q})
    return {"answer": answer, "sources": sources}
