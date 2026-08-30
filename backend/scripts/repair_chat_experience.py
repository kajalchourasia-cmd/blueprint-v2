"""Apply the canonical, idempotent Ask Blueprint chat contract to the n8n export."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "n8n" / "BP-CHAT-01-research-copilot.json"


VALIDATE_CHAT_REQUEST = r"""const raw=$input.first()?.json??{};let b=raw.body??raw;if(typeof b==='string'){try{b=JSON.parse(b)}catch{b={}}}const headers=Object.fromEntries(Object.entries(raw.headers??{}).map(([k,v])=>[String(k).toLowerCase(),v]));const message=String(b.message??'').trim();const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const authorization=String(headers.authorization??'').trim();const projectId=String(b.project_id??'');const testMode=raw.test_mode===true;const actionVerb='(?:send|email|ping|call|contact|post|publish|buy|pay|book|schedule|delete|remove)';const explicitAction=new RegExp(`^\\s*(?:please\\s+)?${actionVerb}\\b|\\b(?:can|could|would)\\s+you\\s+(?:please\\s+)?${actionVerb}\\b|\\bi\\s+want\\s+you\\s+to\\s+${actionVerb}\\b`,'i').test(message);const draftOnly=/\b(draft|write|prepare|outline|template)\b/i.test(message);const action=explicitAction&&!draftOnly;const errors=[];if(message.length<1||message.length>4000)errors.push('MESSAGE_LENGTH');if(!uuid.test(projectId))errors.push('PROJECT_ID');if(!testMode&&!/^Bearer\s+\S+$/i.test(authorization))errors.push('AUTHORIZATION_REQUIRED');const history=(Array.isArray(b.conversation_history)?b.conversation_history:[]).slice(-8).map(item=>({role:item?.role==='assistant'?'assistant':'user',content:String(item?.content??'').trim().slice(0,4000)})).filter(item=>item.content);return [{json:{valid:errors.length===0&&!action,scope_denied:action,errors,status_code:action?422:(errors.includes('AUTHORIZATION_REQUIRED')?401:400),message,project_id:projectId,run_id:uuid.test(String(b.run_id??''))?b.run_id:null,thread_id:uuid.test(String(b.thread_id??''))?b.thread_id:null,correlation_id:String(b.correlation_id??`bp-chat-${Date.now()}`).slice(0,200),confirmed_command:b.confirmed_command===true,authorization,test_mode:testMode,section_key:String(b.section_key??'').toLowerCase()||null,conversation_history:history,context:raw.context??null}}];"""


CLASSIFY_CHAT_INTENT = r"""const x=$input.first().json;const m=x.message.toLowerCase();let intent='QUESTION',target=null;const sourceQuestion=/\b(source|sources|citation|citations|evidence|where did|support this|prove this)\b/.test(m);const nextQuestion=/\bnext\b|what should i do|recommend.*step|how (?:do|can) i (?:start|complete|act)/.test(m);const explicitCancel=/^\s*(?:please\s+)?(?:cancel|stop)\b.*\b(?:run|research|workflow|process|blueprint)\b/.test(m);const explicitRun=/\b(run|rerun|re-run|redo|refresh|repeat|start|conduct|perform)\b/.test(m)&&/\b(research|analysis|investigation|module|customer|user|competitor|market|financial|validation)\b/.test(m);if(/compet/.test(m))target='competitor_intelligence';else if(/customer|user|demand|pain|willing/.test(m))target='customer_demand';else if(/market|industry|econom/.test(m))target='market_economics';else if(/financ|budget|runway|price|break.?even/.test(m))target='financial_readiness';else if(/validat|experiment|test/.test(m))target='validation_proof';if(explicitCancel)intent='CANCEL';else if(explicitRun&&target)intent='RUN_MODULE';else if(sourceQuestion)intent='SOURCE_TRACE';else if(nextQuestion)intent='NEXT_STEP';else if(/phase|status|progress|what was done|what (?:did|does).*(?:find|say|show)/.test(m))intent='EXPLAIN_PHASE';else if(/wrong|correct|change my|update my/.test(m))intent='CORRECTION';const runAllowed=intent==='RUN_MODULE'&&target&&x.confirmed_command;const needsConfirmation=intent==='RUN_MODULE'&&target&&!x.confirmed_command;return [{json:{...x,intent,target_module:target,run_allowed:runAllowed,needs_confirmation:needsConfirmation,answer_allowed:!['RUN_MODULE','CANCEL'].includes(intent)||!runAllowed}}];"""


PREPARE_GROUNDED_COPILOT = r"""const x=$input.first().json;const tasks=(x.context.orchestration_tasks??[]).slice(0,24);const allowedEvidence=(x.context.accepted_evidence??[]).slice(0,40);const blueprintRow=x.context.current_blueprint??{};const blueprint=blueprintRow.blueprint??blueprintRow.payload??blueprintRow;const blueprintSections=Array.isArray(blueprint.sections)?blueprint.sections:[];const selectedTask=tasks.find(t=>t.module_key===x.section_key)??null;const selectedBlueprintSection=blueprintSections.find(s=>s.section_key===x.section_key)??null;const context={run:x.context.run??{},project:x.context.project??{},requested_section:x.section_key,selected_section_context:{task:selectedTask,blueprint_section:selectedBlueprintSection},sections:(x.context.sections??[]).slice(0,20),orchestration_tasks:tasks,current_blueprint:blueprintRow,latest_verdict:x.context.latest_verdict??null,next_actions:(x.context.next_actions??[]).slice(0,12),accepted_evidence:allowedEvidence,quality_checks:(x.context.quality_checks??[]).slice(0,5),errors:(x.context.errors??[]).slice(0,5),conversation_history:x.conversation_history??[]};const system=`You are Ask Blueprint, the founder-facing assistant inside one Blueprint project. Give the useful answer first in plain language, then the reasoning or steps needed. Prioritize requested_section and selected_section_context when the user says this, that, it, the result, or the actionable.

Use three answer lanes deliberately:
1. PROJECT FACTS: Findings, scores, competitors, market claims, customer claims, and verdict reasons must come from the supplied Blueprint or accepted evidence. Cite accepted evidence IDs for external factual claims.
2. PLAIN-LANGUAGE EXPLANATION: You may explain stable product, business, research, finance, or validation concepts without citations. Clearly frame this as a general explanation, never as evidence about this founder's market.
3. ACTION COACHING: You may turn an existing Blueprint actionable into practical founder-run steps using the supplied goal and constraints. Label additions as guidance, not completed work or proven fact.

Do not reply with only UNKNOWN. When project evidence is missing, say what is known, what specific fact is missing, and the smallest safe way to obtain it. Ask at most one precise follow-up question when necessary. Do not force a rerun when founder input or an explanation is enough. For a genuinely unrelated query, briefly say Ask Blueprint is limited to this project's research, validation, finances, and actionables. Never invent a metric, source, customer quote, competitor feature, willingness to pay, or completed action. A rerun is only a proposal until the user confirms it. Never expose hidden reasoning or contact, send, publish, buy, book, pay, or delete. Return JSON with status (ANSWERED, PARTIALLY_ANSWERED, or INSUFFICIENT_EVIDENCE), answer, citations (accepted evidence IDs only), suggested_actions, limitations, and grounding_status (GROUNDED, PARTIALLY_GROUNDED, NO_ACCEPTED_EVIDENCE, or NOT_REQUIRED).`;return [{json:{...x,request:{model:'Qwen/Qwen3-30B-A3B-Instruct-2507',temperature:0.15,max_tokens:1800,response_format:{type:'json_object'},messages:[{role:'system',content:system},{role:'user',content:JSON.stringify({message:x.message,intent:x.intent,requested_section:x.section_key,conversation_history:x.conversation_history??[],context})}]}}}];"""


VALIDATE_GROUNDED_ANSWER = r"""const x=$('Classify Chat Intent Deterministically').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error('CHAT_MODEL_EMPTY');let a;try{a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c}catch{throw new Error('CHAT_MODEL_JSON_PARSE_FAILED')}const allowed=new Set((x.context.accepted_evidence??[]).map(e=>e.id??e.evidence_id));const citations=Array.isArray(a.citations)?[...new Set(a.citations.filter(id=>allowed.has(id)))]:[];let answer=String(a.answer??'').trim();answer=answer.replace(/^UNKNOWN\s*(?:[-:—]\s*)?/i,'I do not have enough project evidence to answer that yet. ');if(!answer)answer='I could not produce a safe answer from the available project context. Ask what information is missing or which evidence would resolve it.';const statuses=new Set(['ANSWERED','PARTIALLY_ANSWERED','INSUFFICIENT_EVIDENCE']);const grounding=new Set(['GROUNDED','PARTIALLY_GROUNDED','NO_ACCEPTED_EVIDENCE','NOT_REQUIRED']);const status=statuses.has(a.status)?a.status:(/not enough|missing|could not/i.test(answer)?'PARTIALLY_ANSWERED':'ANSWERED');const groundingStatus=grounding.has(a.grounding_status)?a.grounding_status:(citations.length?'GROUNDED':'NOT_REQUIRED');return [{json:{status_code:200,response:{status,intent:x.intent,answer:answer.slice(0,8000),citations,suggested_actions:Array.isArray(a.suggested_actions)?a.suggested_actions.filter(v=>v&&typeof v==='object').slice(0,6):[],command:null,limitations:Array.isArray(a.limitations)?a.limitations.map(String).slice(0,8):[],grounding_status:groundingStatus,correlation_id:x.correlation_id}}}];"""


NODE_CODE = {
    "Validate Chat Request and Scope": VALIDATE_CHAT_REQUEST,
    "Classify Chat Intent Deterministically": CLASSIFY_CHAT_INTENT,
    "Prepare Grounded Copilot Answer": PREPARE_GROUNDED_COPILOT,
    "Validate Grounded Chat Answer": VALIDATE_GROUNDED_ANSWER,
}


def apply_contract(path: Path = WORKFLOW_PATH) -> None:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    nodes = {node["name"]: node for node in workflow["nodes"]}
    missing = sorted(set(NODE_CODE) - set(nodes))
    if missing:
        raise RuntimeError(f"Chat workflow is missing required nodes: {', '.join(missing)}")
    for name, code in NODE_CODE.items():
        nodes[name]["parameters"]["jsCode"] = code
    path.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    apply_contract()
