import os
# 1. 魔法级配置：设置 HuggingFace 国内镜像源，防止向量模型下载被墙导致连接失败
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import asyncio
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.services.taxonomy import SECTORS

# 初始化 768维 的本地 Embedding 模型 (如果之前没下完，这次会从镜像极速下载)
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-base-en-v1.5")

# LLM 由多 Provider 层动态提供（本地 Ollama 默认，可切 DeepSeek/OpenAI/Qwen/Claude）。
# get_llms() 返回 (json_llm, text_llm)；analyzer 在每次调用时按当前激活 provider 构建链。
from app.services.llm import get_llms

# ==========================================================================
# A. 公司总体情报抽取 (Company Overview)
# ==========================================================================
class CompanyIntelligence(BaseModel):
    industry: str = Field(description="The specific industry of the company in its own words, e.g. 'Cloud data analytics', '工业机器人'")
    sector: str = Field(description="The single best-fitting standard sector. MUST be EXACTLY one of the allowed values provided.")
    intelligence_score: int = Field(description="A score from 0 to 100 assessing the company's financial health, tech capability, and market potential based on the text")
    summary: str = Field(description="A concise 2-sentence executive summary of the document")

parser = JsonOutputParser(pydantic_object=CompanyIntelligence)

prompt = PromptTemplate(
    template="You are an expert financial and business analyst agent for AI-BOS.\n"
             "Analyze the following company document extract and provide the exact requested information.\n"
             "For 'sector', you MUST choose EXACTLY ONE value from this fixed list (copy it verbatim):\n"
             "{sectors}\n\n"
             "{format_instructions}\n\n"
             "Document Extract:\n{context}\n",
    input_variables=["context"],
    partial_variables={
        "format_instructions": parser.get_format_instructions(),
        "sectors": ", ".join(SECTORS),
    },
)

# 链在调用时按当前 provider 构建（见各 analyze_* 函数）


# ==========================================================================
# B. 详细财报抽取 (Financial Intelligence) —— 核心增强
# ==========================================================================
class FinancialPeriod(BaseModel):
    period: str = Field(description="The reporting period label, e.g. 'FY2023' or 'Q3 2024'")
    year: Optional[int] = Field(default=None, description="Fiscal year as integer, e.g. 2023")
    quarter: Optional[int] = Field(default=None, description="Quarter 1-4. Null if this is a full-year figure")
    revenue: Optional[float] = Field(default=None, description="Total revenue / net sales in the report's currency units (use raw numbers, not 'millions')")
    gross_profit: Optional[float] = Field(default=None, description="Gross profit")
    operating_profit: Optional[float] = Field(default=None, description="Operating income / operating profit")
    net_profit: Optional[float] = Field(default=None, description="Net income / net profit attributable to shareholders")
    rnd_spending: Optional[float] = Field(default=None, description="Research and development expense")
    total_assets: Optional[float] = Field(default=None, description="Total assets")
    total_liabilities: Optional[float] = Field(default=None, description="Total liabilities")
    total_debt: Optional[float] = Field(default=None, description="Total interest-bearing debt (short + long term)")
    cash_and_equivalents: Optional[float] = Field(default=None, description="Cash and cash equivalents")
    operating_cash_flow: Optional[float] = Field(default=None, description="Net cash from operating activities")
    free_cash_flow: Optional[float] = Field(default=None, description="Free cash flow")
    employee_count: Optional[int] = Field(default=None, description="Number of employees if stated")


class SegmentItem(BaseModel):
    name: str = Field(description="Segment / region name")
    value: float = Field(description="Revenue attributed to this segment/region")


class FinancialIntelligence(BaseModel):
    currency: str = Field(default="USD", description="Reporting currency code, e.g. USD, EUR, CNY")
    fiscal_year: str = Field(default="", description="The most recent fiscal year covered, e.g. '2023'")
    financial_health_score: int = Field(description="0-100 overall financial health")
    growth_score: int = Field(description="0-100 revenue & earnings growth quality")
    profitability_score: int = Field(description="0-100 margin strength and profitability")
    liquidity_score: int = Field(description="0-100 cash position and ability to cover liabilities")
    risk_score: int = Field(description="0-100 financial risk where HIGHER means MORE risk (leverage, burn, volatility)")
    executive_summary: str = Field(description="A 3-4 sentence CFO-level summary of financial performance")
    periods: List[FinancialPeriod] = Field(description="One entry per reporting period found. Include multiple years/quarters when available so trends can be charted.")
    key_findings: List[str] = Field(description="3-6 concrete, number-backed findings")
    growth_drivers: List[str] = Field(description="2-5 drivers behind revenue/profit changes")
    risks: List[str] = Field(description="2-5 financial risks or red flags")
    opportunities: List[str] = Field(description="2-5 financial opportunities")
    segment_revenue: List[SegmentItem] = Field(default_factory=list, description="Revenue by business segment if disclosed")
    geographic_revenue: List[SegmentItem] = Field(default_factory=list, description="Revenue by geography/region if disclosed")


fin_parser = JsonOutputParser(pydantic_object=FinancialIntelligence)

fin_prompt = PromptTemplate(
    template=(
        "You are a CFA-level financial analyst working for AI-BOS. Think like a buy-side equity "
        "analyst and a CFO chief of staff.\n\n"
        "From the financial document extract below, extract ALL available financial figures and "
        "produce a structured analysis. The document may be an annual report OR a due-diligence / "
        "narrative report where figures are embedded in prose — extract figures from prose too.\n"
        "RULES:\n"
        "- For the FIGURE fields inside each period (revenue, net_profit, ...): NEVER invent numbers; "
        "if a specific figure is not in the text, set THAT field to null.\n"
        "- The five SCORE fields (financial_health_score, growth_score, profitability_score, "
        "liquidity_score, risk_score) are MANDATORY integers 0-100 and must NEVER be null. Even with "
        "limited data, give your best professional estimate from the qualitative evidence "
        "(e.g. negative gross margin → low profitability_score; heavy cash burn → high risk_score).\n"
        "- Normalize all monetary values to the SAME unit (raw currency units). If the report says "
        "'in millions' / '百万' / '亿', multiply accordingly (e.g. 8.2亿 → 820000000).\n"
        "- Extract every distinct reporting period you can find (multiple years or quarters) so trends "
        "can be charted. List them oldest-first. Always include at least the most recent period if any "
        "revenue/profit figure is mentioned anywhere.\n"
        "- For risk_score, higher = more risk.\n"
        "- Do NOT merely restate numbers in findings; explain what they MEAN for the business.\n"
        "- Write all natural-language text (executive_summary, key_findings, growth_drivers, risks, "
        "opportunities) in the SAME language as the source document (Chinese in → Chinese out).\n\n"
        "{format_instructions}\n\n"
        "Financial Document Extract:\n{context}\n"
    ),
    input_variables=["context"],
    partial_variables={"format_instructions": fin_parser.get_format_instructions()},
)

# fin_chain 在 analyze_financials 内构建


# ==========================================================================
# C. 竞争情报抽取 (Competitive Intelligence) —— Agent 03
# ==========================================================================
class CompetitorEntry(BaseModel):
    name: str = Field(description="Competitor company name")
    type: str = Field(default="Direct", description="One of: Direct, Indirect, Substitute, Emerging")
    description: str = Field(default="", description="One-line description of what they do")
    strengths: List[str] = Field(default_factory=list, description="1-3 of this competitor's strengths")
    weaknesses: List[str] = Field(default_factory=list, description="1-3 of this competitor's weaknesses")
    threat_level: int = Field(default=3, description="Threat to our company, 1 (low) to 5 (severe)")


class Battlecard(BaseModel):
    competitor: str = Field(description="Competitor name this battlecard targets")
    why_we_win: List[str] = Field(default_factory=list, description="Reasons our company beats them")
    why_we_lose: List[str] = Field(default_factory=list, description="Reasons we lose to them")
    objection_handling: List[str] = Field(default_factory=list, description="How to handle objections in their favor")


class CompetitiveIntelligence(BaseModel):
    market_position: str = Field(description="One-sentence summary of the company's competitive position")
    positioning_score: int = Field(description="0-100, strength of competitive moat / defensibility")
    strengths: List[str] = Field(description="SWOT - 3-5 internal strengths")
    weaknesses: List[str] = Field(description="SWOT - 3-5 internal weaknesses")
    opportunities: List[str] = Field(description="SWOT - 3-5 external opportunities")
    threats: List[str] = Field(description="SWOT - 3-5 external threats")
    competitors: List[CompetitorEntry] = Field(description="3-8 competitors with assessment")
    battlecards: List[Battlecard] = Field(default_factory=list, description="Battlecards for the 2-3 most threatening competitors")
    technology_trends: List[str] = Field(default_factory=list, description="2-5 relevant technology/industry trends")


comp_parser = JsonOutputParser(pydantic_object=CompetitiveIntelligence)

comp_prompt = PromptTemplate(
    template=(
        "You are a senior competitive intelligence analyst at AI-BOS. Think like Gartner and Bain.\n"
        "Analyze the document for {company_name} and produce structured competitive intelligence.\n\n"
        "RULES:\n"
        "- Identify direct competitors, indirect competitors, substitutes and emerging players.\n"
        "- If competitors are named in the document, use them. If none are named, infer the most likely "
        "competitors from the industry and business model, and mark them as inferred in the description.\n"
        "- Produce a real SWOT, not generic platitudes. Tie each point to evidence or clear business logic.\n"
        "- Build battlecards only for the 2-3 highest threat_level competitors.\n"
        "- positioning_score: higher = stronger moat.\n"
        "- Write all natural-language text in the SAME language as the source document "
        "(Chinese in → Chinese out); keep competitor names in their original form.\n\n"
        "{format_instructions}\n\n"
        "Document Extract:\n{context}\n"
    ),
    input_variables=["context", "company_name"],
    partial_variables={"format_instructions": comp_parser.get_format_instructions()},
)

# comp_chain 在 analyze_competition 内构建


# ==========================================================================
# D. 尽职调查抽取 (Due Diligence) —— Agent 07
# ==========================================================================
class RiskCategory(BaseModel):
    key: str = Field(description="One of: financial, legal, operational, commercial, technology")
    label: str = Field(description="Human label for the risk category, in the document's language")
    score: int = Field(description="0-100 where HIGHER means MORE risk")
    summary: str = Field(description="2-3 sentence assessment of this risk category")
    findings: List[str] = Field(default_factory=list, description="1-4 concrete findings / evidence")


class DueDiligenceIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code of the language used for the text fields, e.g. 'zh' or 'en'")
    overall_score: int = Field(description="0-100 overall investment/acquisition attractiveness (higher = better)")
    recommendation: str = Field(description="Clear go / no-go / conditional recommendation with rationale")
    executive_summary: str = Field(description="3-5 sentence due-diligence executive summary")
    risk_categories: List[RiskCategory] = Field(description="Exactly 5 categories: financial, legal, operational, commercial, technology")
    red_flags: List[str] = Field(description="2-6 critical red flags / deal-breakers (empty list if none)")
    opportunities: List[str] = Field(description="2-5 upside opportunities")


dd_parser = JsonOutputParser(pydantic_object=DueDiligenceIntelligence)

dd_prompt = PromptTemplate(
    template=(
        "You are a senior due-diligence analyst at a top private-equity / M&A advisory firm "
        "(Agent 07 of AI-BOS). Analyze the document for an investment or acquisition decision.\n\n"
        "Assess these FIVE risk categories, each scored 0-100 where HIGHER = MORE risk:\n"
        "- financial (財務/财务): leverage, burn, revenue quality, working capital\n"
        "- legal (法律): litigation, compliance, IP ownership, regulatory\n"
        "- operational (運營/运营): management, processes, supply chain, key-person\n"
        "- commercial (商業/商业): market, customer concentration, competition, demand\n"
        "- technology (技術/技术): tech debt, scalability, security, obsolescence\n\n"
        "RULES:\n"
        "- NEVER invent facts. Base findings on the document; if a category lacks evidence, say so and score conservatively.\n"
        "- IMPORTANT: Write ALL natural-language text fields (label, summary, findings, recommendation, "
        "executive_summary, red_flags, opportunities) in the SAME language as the source document. "
        "If the document is in Chinese, respond in Chinese.\n"
        "- overall_score is attractiveness (higher = better); category scores are risk (higher = worse).\n\n"
        "{format_instructions}\n\n"
        "Document Extract:\n{context}\n"
    ),
    input_variables=["context"],
    partial_variables={"format_instructions": dd_parser.get_format_instructions()},
)

# dd_chain 在 analyze_due_diligence 内构建


async def analyze_due_diligence(context: str):
    """尽职调查深度解析（Agent 07）。输入为已构建好的分析上下文（digest）。"""
    json_llm, _ = get_llms()
    return await (dd_prompt | json_llm | dd_parser).ainvoke({"context": context})


# ==========================================================================
# E. CEO 执行简报 (Agent 08) —— 综合各维度情报
# ==========================================================================
class BriefingIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code of language used, e.g. 'zh' or 'en'")
    summary: str = Field(description="One-sentence headline conclusion for leadership")
    what_happened: str = Field(description="2-4 sentences: the key facts/situation")
    why_it_matters: str = Field(description="2-4 sentences: business significance")
    recommended_actions: List[str] = Field(description="3-6 prioritized, concrete recommendations")
    key_risks: List[str] = Field(description="2-5 most important risks")
    opportunities: List[str] = Field(description="2-5 most important opportunities")
    next_actions: List[str] = Field(description="3-6 immediate next steps")


brief_parser = JsonOutputParser(pydantic_object=BriefingIntelligence)

brief_prompt = PromptTemplate(
    template=(
        "You are the chief of staff to a Fortune 500 CEO (Agent 08 of AI-BOS). Synthesize the "
        "multi-dimensional intelligence below into a crisp executive briefing. Maximum clarity, "
        "maximum business value, no fluff. Answer the implicit questions: what happened, why it "
        "matters, what leadership should do, what risks/opportunities exist, what to do next.\n"
        "RULES: base everything on the provided intelligence; do not invent figures. "
        "Write ALL text in the SAME language as the intelligence (Chinese in → Chinese out).\n\n"
        "{format_instructions}\n\n"
        "==== Company Intelligence ====\n{intel}\n"
    ),
    input_variables=["intel"],
    partial_variables={"format_instructions": brief_parser.get_format_instructions()},
)


async def generate_briefing(intel_text: str):
    """生成 CEO 执行简报。输入为汇总后的情报文本。"""
    json_llm, _ = get_llms()
    return await (brief_prompt | json_llm | brief_parser).ainvoke({"intel": intel_text})


# ==========================================================================
# F. 战略情报 (Agent 06) —— 战略选项 + 排序建议 + 波特五力
# ==========================================================================
class StrategicOption(BaseModel):
    title: str = Field(description="Short title of the strategic option")
    description: str = Field(description="1-2 sentences describing the option")
    impact: int = Field(description="Business impact 1 (low) to 5 (high)")
    feasibility: int = Field(description="Feasibility 1 (hard) to 5 (easy)")
    risk: int = Field(description="Risk 1 (low) to 5 (high)")
    investment: str = Field(description="Investment required: Low / Medium / High")
    rationale: str = Field(default="", description="Why this matters / supporting logic")


class StrategyRecommendation(BaseModel):
    title: str = Field(description="The recommendation")
    rationale: str = Field(default="", description="Why")
    expected_outcome: str = Field(default="", description="Expected result")


class PorterForce(BaseModel):
    force: str = Field(description="One of: Competitive Rivalry, Threat of New Entrants, Threat of Substitutes, Bargaining Power of Suppliers, Bargaining Power of Buyers")
    level: int = Field(description="0-100, higher = stronger/more adverse force")
    summary: str = Field(description="One-sentence assessment")


class StrategyIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code, e.g. 'zh' or 'en'")
    executive_summary: str = Field(description="3-4 sentence strategic outlook")
    strategic_options: List[StrategicOption] = Field(description="3-6 strategic options, scored by impact/feasibility/risk")
    recommendations: List[StrategyRecommendation] = Field(description="3-6 recommendations, ORDERED by priority (most important first)")
    porters_five_forces: List[PorterForce] = Field(description="Exactly 5 Porter's forces")
    growth_opportunities: List[str] = Field(description="3-6 concrete growth / expansion / partnership / M&A opportunities")


strat_parser = JsonOutputParser(pydantic_object=StrategyIntelligence)

strat_prompt = PromptTemplate(
    template=(
        "You are a former McKinsey senior partner (Agent 06 of AI-BOS). Based on the company "
        "intelligence below, produce a rigorous strategy analysis using frameworks (SWOT, Porter's "
        "Five Forces, Ansoff/BCG thinking, Blue Ocean).\n"
        "RULES:\n"
        "- Generate concrete strategic OPTIONS and score each by impact, feasibility, risk (1-5) and "
        "investment (Low/Medium/High).\n"
        "- RANK recommendations by priority (impact × feasibility, adjusted for risk) — most important first.\n"
        "- Porter's Five Forces: exactly 5, each scored 0-100 (higher = stronger/adverse).\n"
        "- Base everything on the intelligence; do not invent figures. Write ALL text in the SAME "
        "language as the intelligence (Chinese in → Chinese out).\n\n"
        "{format_instructions}\n\n"
        "==== Company Intelligence ====\n{intel}\n"
    ),
    input_variables=["intel"],
    partial_variables={"format_instructions": strat_parser.get_format_instructions()},
)


async def generate_strategy(intel_text: str):
    """生成战略情报。输入为汇总后的情报文本。"""
    json_llm, _ = get_llms()
    return await (strat_prompt | json_llm | strat_parser).ainvoke({"intel": intel_text})


# ==========================================================================
# G. 销售情报 (Agent 04) —— ICP / 买家画像 / 痛点 / 机会
# ==========================================================================
class BuyerPersona(BaseModel):
    role: str = Field(description="Buyer/decision-maker role or title")
    goals: List[str] = Field(default_factory=list, description="1-3 goals")
    pain_points: List[str] = Field(default_factory=list, description="1-3 pain points")


class ICPSegment(BaseModel):
    segment: str = Field(description="Ideal customer segment name")
    description: str = Field(default="", description="Who they are")
    why_fit: str = Field(default="", description="Why they're a good fit")


class SalesIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code, e.g. 'zh' or 'en'")
    executive_summary: str = Field(description="2-3 sentence go-to-market summary")
    icp: List[ICPSegment] = Field(description="2-4 ideal customer profiles")
    buyer_personas: List[BuyerPersona] = Field(description="2-4 buyer personas")
    pain_points: List[str] = Field(description="3-6 customer pain points this company addresses")
    buying_triggers: List[str] = Field(description="3-5 events/signals that trigger buying")
    sales_opportunities: List[str] = Field(description="3-6 concrete sales opportunities / plays")


sales_parser = JsonOutputParser(pydantic_object=SalesIntelligence)
sales_prompt = PromptTemplate(
    template=(
        "You are an enterprise sales director (Agent 04 of AI-BOS). From the company intelligence, "
        "determine who buys, why they buy, what pain they have, and how to win. Produce actionable "
        "sales intelligence: ICP, buyer personas, pain points, buying triggers, sales opportunities.\n"
        "RULES: base on the intelligence; no invented facts. Write ALL text in the SAME language as "
        "the intelligence (Chinese in → Chinese out).\n\n{format_instructions}\n\n"
        "==== Company Intelligence ====\n{intel}\n"
    ),
    input_variables=["intel"],
    partial_variables={"format_instructions": sales_parser.get_format_instructions()},
)


async def generate_sales(intel_text: str):
    json_llm, _ = get_llms()
    return await (sales_prompt | json_llm | sales_parser).ainvoke({"intel": intel_text})


# ==========================================================================
# H. 市场情报 (Agent 05) —— TAM/SAM/SOM / 趋势 / 驱动 / 壁垒
# ==========================================================================
class MarketSegment(BaseModel):
    name: str = Field(description="Market segment name")
    description: str = Field(default="", description="Brief description")


class MarketIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code, e.g. 'zh' or 'en'")
    executive_summary: str = Field(description="2-3 sentence market outlook")
    tam: str = Field(default="", description="Total Addressable Market, with figure + basis if estimable")
    sam: str = Field(default="", description="Serviceable Addressable Market")
    som: str = Field(default="", description="Serviceable Obtainable Market")
    market_growth: str = Field(default="", description="Growth rate / CAGR with horizon")
    trends: List[str] = Field(description="3-6 key market trends")
    drivers: List[str] = Field(description="3-5 market growth drivers")
    barriers: List[str] = Field(description="2-5 barriers to entry")
    segments: List[MarketSegment] = Field(default_factory=list, description="2-5 market segments")


market_parser = JsonOutputParser(pydantic_object=MarketIntelligence)
market_prompt = PromptTemplate(
    template=(
        "You are a senior market research consultant (Agent 05 of AI-BOS). Estimate the market: "
        "TAM/SAM/SOM, growth rate, drivers, barriers, trends and segments. Where exact figures aren't "
        "available, give a clearly-labeled estimate with the reasoning basis (do NOT fabricate precise "
        "numbers as if certain). Always identify opportunities.\n"
        "Write ALL text in the SAME language as the intelligence (Chinese in → Chinese out).\n\n"
        "{format_instructions}\n\n==== Company Intelligence ====\n{intel}\n"
    ),
    input_variables=["intel"],
    partial_variables={"format_instructions": market_parser.get_format_instructions()},
)


async def generate_market(intel_text: str):
    json_llm, _ = get_llms()
    return await (market_prompt | json_llm | market_parser).ainvoke({"intel": intel_text})


# ==========================================================================
# I. Playbook 生成 (Agent 09) —— 把情报转成可执行方法论
# ==========================================================================
class PlaybookStep(BaseModel):
    title: str = Field(description="Step title")
    objective: str = Field(default="", description="What this step achieves")
    owner: str = Field(default="", description="Suggested role/owner")
    deliverable: str = Field(default="", description="Concrete deliverable of this step")
    kpi: str = Field(default="", description="Measurable KPI / success metric")


class PlaybookIntelligence(BaseModel):
    language: str = Field(default="en", description="ISO code, e.g. 'zh' or 'en'")
    title: str = Field(description="Playbook title")
    objective: str = Field(description="Overall objective")
    category: str = Field(default="", description="e.g. Sales, Market Entry, Fundraising, Growth")
    difficulty: str = Field(default="Medium", description="Easy / Medium / Hard")
    estimated_time: str = Field(default="", description="e.g. '8-12 weeks'")
    expected_outcome: str = Field(default="", description="Expected outcome")
    steps: List[PlaybookStep] = Field(description="5-10 ordered, executable steps")
    deliverables: List[str] = Field(description="3-6 key deliverables")
    kpis: List[str] = Field(description="3-6 KPIs")
    success_criteria: List[str] = Field(description="3-5 success conditions")


pb_parser = JsonOutputParser(pydantic_object=PlaybookIntelligence)
pb_prompt = PromptTemplate(
    template=(
        "You are a business operating system architect (Agent 09 of AI-BOS). Convert the company "
        "intelligence and the stated GOAL into a concrete, EXECUTABLE playbook — not a document. "
        "Each step must be actionable with an owner role, a deliverable and a measurable KPI.\n"
        "RULES: ground steps in the company's actual situation (financials, competition, strategy); "
        "5-10 ordered steps. Write ALL text in the SAME language as the intelligence "
        "(Chinese in → Chinese out).\n\n"
        "GOAL: {goal}\n\n{format_instructions}\n\n==== Company Intelligence ====\n{intel}\n"
    ),
    input_variables=["intel", "goal"],
    partial_variables={"format_instructions": pb_parser.get_format_instructions()},
)


async def generate_playbook(intel_text: str, goal: str):
    json_llm, _ = get_llms()
    return await (pb_prompt | json_llm | pb_parser).ainvoke({"intel": intel_text, "goal": goal or "Growth & execution"})


# ==========================================================================
# J. 商业模拟引擎 (Module 7 Academy)
# ==========================================================================
class SimTurn(BaseModel):
    outcome: str = Field(default="", description="The consequence of the student's decision (empty on the first turn)")
    feedback: str = Field(default="", description="Mentor coaching feedback on the decision (empty on first turn)")
    score: int = Field(default=0, description="0-100 score for this decision (0 on first turn)")
    situation: str = Field(description="The current/next business situation the student faces")
    options: List[str] = Field(description="2-4 suggested decision options; the student may also free-type")
    is_final: bool = Field(default=False, description="True when the simulation should end")
    final_assessment: str = Field(default="", description="Overall assessment when is_final")
    final_scores: dict = Field(default_factory=dict, description="When final: {dimension: 0-100}, e.g. strategy/execution/finance/leadership")


sim_parser = JsonOutputParser(pydantic_object=SimTurn)
sim_prompt = PromptTemplate(
    template=(
        "You are a business-school simulation engine AND a mentor. Run an interactive, turn-based "
        "business simulation and coach the student.\n"
        "SCENARIO: {scenario}\n\n"
        "HISTORY so far (situations, decisions, outcomes):\n{history}\n\n"
        "This is round {round} (aim to conclude around round 5-6).\n"
        "STUDENT'S LATEST DECISION: {decision}\n\n"
        "Rules:\n"
        "- If the decision is '(开始)' / '(START)', just set up the opening situation + 2-4 options "
        "(leave outcome/feedback empty, score 0).\n"
        "- Otherwise: narrate a realistic consequence (outcome), give concise mentor feedback, score the "
        "decision 0-100, then present the next situation with 2-4 options.\n"
        "- If round >= 5 or the scenario reaches a natural conclusion, set is_final=true and provide "
        "final_assessment + final_scores (dimensions like strategy, execution, finance, leadership 0-100).\n"
        "- Write everything in the SAME language as the scenario (Chinese scenario → Chinese).\n\n"
        "{format_instructions}\n"
    ),
    input_variables=["scenario", "history", "round", "decision"],
    partial_variables={"format_instructions": sim_parser.get_format_instructions()},
)


async def generate_sim_turn(scenario: str, history_text: str, decision: str, round_no: int):
    json_llm, _ = get_llms()
    return await (sim_prompt | json_llm | sim_parser).ainvoke(
        {"scenario": scenario, "history": history_text or "(none)", "decision": decision, "round": round_no})


# ==========================================================================
# 流水线编排 & 长文档 map-reduce
# ==========================================================================
from langchain_core.output_parsers import StrOutputParser

# 短于该阈值则直接整篇分析；长文档走 map-reduce 摘要
_DIGEST_THRESHOLD = 14000
_CHUNK_SIZE = 8000
# 超大文档（如数百页招股书）会切出几十块，本地串行 Ollama 跑不动。
# 按"信息密度"挑选最关键的若干块，兼顾速度与覆盖。
_MAX_CHUNKS = 14
_KEY_TERMS = [
    # 中文
    "营业收入", "收入", "利润", "毛利", "净利", "现金流", "资产", "负债", "风险",
    "竞争", "客户", "研发", "募集", "股权", "诉讼", "供应商", "产能", "毛利率",
    # English
    "revenue", "profit", "margin", "cash flow", "debt", "asset", "risk",
    "competitor", "customer", "r&d", "equity", "litigation",
]


def _select_chunks(chunks: list[str]) -> list[str]:
    """文档块过多时，按关键词密度选出信息量最大的块（始终含首块=概览），
    再按原文顺序返回以保留叙述连贯性。"""
    if len(chunks) <= _MAX_CHUNKS:
        return chunks

    def density(c: str) -> int:
        low = c.lower()
        return sum(low.count(t.lower()) for t in _KEY_TERMS)

    ranked = sorted(range(len(chunks)), key=lambda i: density(chunks[i]), reverse=True)
    keep = set(ranked[: _MAX_CHUNKS]) | {0}
    return [chunks[i] for i in sorted(keep)]

_digest_prompt = PromptTemplate(
    template=(
        "你是文档信息提炼引擎。请把下面的文档片段压缩成稠密的事实摘要，"
        "必须完整、逐字保留所有关键事实：财务数字与金额、日期、人名、公司与竞争对手名称、"
        "股权比例、法律/诉讼、运营/团队、业务/行业、风险点。不要遗漏任何数字。"
        "禁止添加评论或分析。用文档原本的语言输出。\n\n"
        "文档片段：\n{chunk}\n\n稠密事实摘要："
    ),
    input_variables=["chunk"],
)
# _digest_chain 在 build_analysis_context 内按当前 provider 构建


def _load_text(file_path: str) -> str:
    """统一文档抽取（PDF含OCR / DOCX / PPTX / XLSX / TXT…）。"""
    from app.services.extract import extract_text
    return extract_text(file_path)


async def _load_text_async(file_path: str) -> str:
    """PyPDF 解析是同步阻塞操作，放到线程池执行，避免卡死整个 async 事件循环（API 会失去响应）。"""
    return await asyncio.to_thread(_load_text, file_path)


async def build_analysis_context(file_path: str) -> str:
    """从文件构建分析上下文（PDF → 文本 → 摘要）。"""
    full_text = await _load_text_async(file_path)
    return await build_context_from_text(full_text)


async def build_context_from_text(full_text: str) -> str:
    """从已有文本构建分析上下文（供联网抓取的文本使用）。
    短文本直接返回；长文本走 map-reduce 摘要。"""
    full_text = full_text or ""
    if len(full_text) <= _DIGEST_THRESHOLD:
        return full_text

    chunks = [full_text[i:i + _CHUNK_SIZE] for i in range(0, len(full_text), _CHUNK_SIZE)]
    chunks = _select_chunks(chunks)  # 超大文档只保留信息最密集的若干块
    _, text_llm = get_llms()
    digest_chain = _digest_prompt | text_llm | StrOutputParser()
    # 在线 provider 可真正并发；本地 Ollama 串行也无妨
    summaries = await asyncio.gather(*[digest_chain.ainvoke({"chunk": c}) for c in chunks])
    return "\n\n".join((s or "").strip() for s in summaries if s and str(s).strip())


async def analyze_document(file_path: str):
    """总体情报 + 向量化（上传同步阶段，保持快速）。仅用文档开头快速给出概览。"""
    full_text = await _load_text_async(file_path)
    context_text = full_text[:6000] if len(full_text) > 6000 else full_text

    json_llm, _ = get_llms()
    intelligence_data = await (prompt | json_llm | parser).ainvoke({"context": context_text})
    vector = await embeddings.aembed_query(context_text)

    return intelligence_data, vector


async def analyze_financials(context: str):
    """财报深度解析。输入为已构建好的分析上下文（digest）。"""
    json_llm, _ = get_llms()
    return await (fin_prompt | json_llm | fin_parser).ainvoke({"context": context})


async def analyze_competition(context: str, company_name: str = ""):
    """竞争情报深度解析（Agent 03）。输入为已构建好的分析上下文（digest）。"""
    json_llm, _ = get_llms()
    return await (comp_prompt | json_llm | comp_parser).ainvoke(
        {"context": context, "company_name": company_name or "the company"}
    )
