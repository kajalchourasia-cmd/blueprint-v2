from __future__ import annotations

import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "n8n"
NEBIUS_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"
SUPABASE_URL = "https://gudsbrmphrokpnzmrlqd.supabase.co"
NEBIUS_ID = "ewsT8nomHwfqyWCx"
SUPABASE_PUBLIC_ID = "fguxqwSfKfj2xfo9"


def uid(name: str) -> str:
    return str(uuid.uuid5(uuid.UUID("5d23f930-cba8-4b6b-861a-37867b64a884"), name))


def node(name: str, node_type: str, x: int, y: int, parameters: dict, version=2) -> dict:
    return {
        "parameters": parameters,
        "id": uid(name),
        "name": name,
        "type": node_type,
        "typeVersion": version,
        "position": [x, y],
    }


def code(name: str, x: int, y: int, js: str) -> dict:
    return node(name, "n8n-nodes-base.code", x, y, {"jsCode": js}, 2)


def manual(name: str, x: int, y: int) -> dict:
    return node(name, "n8n-nodes-base.manualTrigger", x, y, {}, 1)


def sub_trigger(name: str, x: int, y: int) -> dict:
    return node(name, "n8n-nodes-base.executeWorkflowTrigger", x, y, {"inputSource": "passthrough"}, 1.2)


def webhook(name: str, path: str, x: int, y: int) -> dict:
    n = node(name, "n8n-nodes-base.webhook", x, y, {"httpMethod": "POST", "path": path, "responseMode": "responseNode", "options": {}}, 2.1)
    n["webhookId"] = uid(name + "-webhook")
    return n


def if_true(name: str, x: int, y: int, expression: str) -> dict:
    return node(name, "n8n-nodes-base.if", x, y, {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
            "conditions": [{
                "id": uid(name + "-condition"),
                "leftValue": expression,
                "rightValue": True,
                "operator": {"type": "boolean", "operation": "true", "singleValue": True},
            }],
            "combinator": "and",
        },
        "options": {},
    }, 2.2)


def http_nebius(name: str, x: int, y: int, timeout=30000) -> dict:
    n = node(name, "n8n-nodes-base.httpRequest", x, y, {
        "method": "POST",
        "url": NEBIUS_URL,
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": True,
        "contentType": "raw",
        "rawContentType": "application/json",
        "body": "={{ JSON.stringify($json.request) }}",
        "options": {"timeout": timeout},
    }, 4.5)
    n["credentials"] = {"httpHeaderAuth": {"id": NEBIUS_ID, "name": "BP Nebius Token Factory"}}
    n["onError"] = "continueRegularOutput"
    n["retryOnFail"] = True
    n["maxTries"] = 2
    n["waitBetweenTries"] = 1500
    return n


def http_supabase_rpc(name: str, rpc_name: str, x: int, y: int, timeout=20000) -> dict:
    n = node(name, "n8n-nodes-base.httpRequest", x, y, {
        "method": "POST",
        "url": f"{SUPABASE_URL}/rest/v1/rpc/{rpc_name}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": True,
        "headerParameters": {"parameters": [
            {"name": "Authorization", "value": "={{ $json.authorization }}"},
            {"name": "Content-Type", "value": "application/json"},
        ]},
        "sendBody": True,
        "contentType": "raw",
        "rawContentType": "application/json",
        "body": "={{ JSON.stringify($json.rpc_body) }}",
        "options": {"timeout": timeout},
    }, 4.5)
    n["credentials"] = {"httpHeaderAuth": {"id": SUPABASE_PUBLIC_ID, "name": "BP Supabase Public"}}
    n["onError"] = "continueRegularOutput"
    return n


def execute_workflow(name: str, workflow_id: str, x: int, y: int) -> dict:
    n = node(name, "n8n-nodes-base.executeWorkflow", x, y, {
        "source": "database",
        "workflowId": {"__rl": True, "value": workflow_id, "mode": "id"},
        "mode": "once",
        "options": {"waitForSubWorkflow": True},
    }, 1.3)
    n["onError"] = "continueRegularOutput"
    return n


def respond(name: str, x: int, y: int, body_expression: str, status_expression="={{ $json.status_code ?? 200 }}") -> dict:
    return node(name, "n8n-nodes-base.respondToWebhook", x, y, {
        "respondWith": "json",
        "responseBody": body_expression,
        "options": {
            "responseCode": status_expression,
            "responseHeaders": {"entries": [{"name": "Content-Type", "value": "application/json"}]},
        },
    }, 1.1)


def connect(connections: dict, source: str, target: str, output=0) -> None:
    outputs = connections.setdefault(source, {"main": []})["main"]
    while len(outputs) <= output:
        outputs.append([])
    outputs[output].append({"node": target, "type": "main", "index": 0})


def workflow(workflow_id: str, name: str, nodes: list[dict], connections: dict, timeout=120) -> dict:
    return {
        "id": workflow_id,
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "pinData": {},
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "timezone": "Asia/Calcutta",
            "errorWorkflow": "bp90ErrorAudit01",
            "executionTimeout": timeout,
        },
        "versionId": uid(workflow_id + "-version"),
        "meta": {"templateCredsSetupCompleted": True},
        "tags": [],
    }


def build_quality() -> dict:
    nodes = [
        manual("Run Quality Gate Test", -1040, -180),
        code("Create Safe Quality Fixture", -820, -180, r"""return [{json:{blueprint:{schema_version:'bp-blueprint-v1',status:'PARTIAL',product_idea:'An evidence workspace for founders validating an existing idea.',starting_position:{idea_text:'An evidence workspace for founders validating an existing idea.'},dashboard:{completion_percent:65,open_assumptions:3,positive_signals:4,open_risks:2},executive_decision:{decision:'VALIDATE_NEXT',reason:'Directional evidence exists but payment proof is unknown.'},sections:[{section_key:'customer_demand',status:'AGENT_DONE',completion_percent:70,summary:{finding:'Founders report manual validation work.'},open_questions:['Will founders pay?'],evidence_ids:['ev-test-1']}],financial_plan:{limitations:['Scenario, not forecast.']},citations:[{evidence_id:'ev-test-1',source_url:'https://example.com/founder-research',excerpt:'Founders report manual validation work.',limitations:['Directional excerpt only.'],auditor_verdict:'ACCEPT_WITH_LIMITATION'}],next_route:'VALIDATION',limitations:['Willingness to pay remains unknown.']},revision_count:0,correlation_id:'bp-quality-safe-test',test_mode:true}}];"""),
        sub_trigger("When Called for Blueprint Quality", -1040, 80),
        code("Validate Quality Contract", -580, 0, r"""const src=$input.first()?.json??{};const b=src.blueprint??src;if(!b||typeof b!=='object'||Array.isArray(b))throw new Error('QUALITY_INPUT_MISSING_BLUEPRINT');const required=['schema_version','status','product_idea','starting_position','dashboard','sections','next_route'];const missing=required.filter(k=>b[k]==null);if(missing.length)throw new Error('QUALITY_SCHEMA_MISSING:'+missing.join(','));if(!Array.isArray(b.sections)||!Array.isArray(b.citations??[]))throw new Error('QUALITY_SCHEMA_ARRAYS');const revision=Math.max(0,Math.min(1,Number(src.revision_count??0)));return [{json:{blueprint:b,revision_count:revision,correlation_id:String(src.correlation_id??`bp-quality-${Date.now()}`).slice(0,200),test_mode:src.test_mode===true}}];"""),
        code("Prepare Independent Blueprint Critic", -340, 0, r"""const x=$input.first().json;const rubric={groundedness:'Every material factual statement is supported by an accepted citation or explicitly labelled assumption/unknown.',completeness:'Requested sections have a useful result or an explicit blocker/question.',consistency:'Sections, dashboard, decision and next route do not contradict each other.',actionability:'Next actions are specific, bounded and measurable.',assumption_hygiene:'Facts, calculations, recommendations, assumptions and unknowns are separated.',calculation_integrity:'Financial values are deterministic scenarios with inputs and limitations, never invented forecasts.',scope_compliance:'No messaging, publishing, buying, booking, paying, deleting or other external write is claimed.'};return [{json:{...x,request:{model:'openai/gpt-oss-120b',reasoning_effort:'low',temperature:0,max_tokens:1400,response_format:{type:'json_object'},messages:[{role:'system',content:'You are Blueprint Final Quality Critic, independent from research and synthesis. Score the supplied Blueprint against every rubric item from 0 to 1. Return JSON with verdict PASS|REPAIR|FAIL|HUMAN_REVIEW, overall_score, rubric_scores with all seven named keys, failed_rules array, repair_instructions array, requires_human boolean, and critic_notes array. PASS requires overall_score >= 0.78, groundedness >= 0.80, assumption_hygiene >= 0.80, calculation_integrity >= 0.80, scope_compliance = 1, no unsupported high-stakes claim, and valid citations. REPAIR only when exact bounded edits can fix it. HUMAN_REVIEW is for contradictions or authority. Never reward confident prose.'},{role:'user',content:JSON.stringify({rubric,blueprint:x.blueprint})}]}}}];"""),
        http_nebius("Nebius — Blueprint Quality Critic", -100, 0),
        code("Parse and Enforce Quality Verdict", 140, 0, r"""const x=$('Validate Quality Contract').first().json;const r=$input.first().json;const content=r.choices?.[0]?.message?.content;if(!content)throw new Error('QUALITY_CRITIC_EMPTY_OR_PROVIDER_FAILURE');let q;try{q=typeof content==='string'?JSON.parse(content.replace(/^```json\s*|\s*```$/g,'')):content}catch{throw new Error('QUALITY_CRITIC_JSON_PARSE_FAILED')}const keys=['groundedness','completeness','consistency','actionability','assumption_hygiene','calculation_integrity','scope_compliance'];const scores=q.rubric_scores&&typeof q.rubric_scores==='object'?q.rubric_scores:{};for(const k of keys)if(!Number.isFinite(Number(scores[k])))throw new Error('QUALITY_SCORE_MISSING:'+k);const cited=new Set((x.blueprint.citations??[]).map(c=>c.evidence_id));const badRefs=(x.blueprint.sections??[]).flatMap(s=>(s.evidence_ids??[]).filter(id=>!cited.has(id)));const highStake=JSON.stringify(x.blueprint).match(/(?:TAM|SAM|SOM|market size|will pay|conversion rate|revenue forecast)/gi)??[];const deterministicPass=Number(q.overall_score)>=0.78&&Number(scores.groundedness)>=0.8&&Number(scores.assumption_hygiene)>=0.8&&Number(scores.calculation_integrity)>=0.8&&Number(scores.scope_compliance)>=0.999&&badRefs.length===0;let verdict=['PASS','REPAIR','FAIL','HUMAN_REVIEW'].includes(q.verdict)?q.verdict:'FAIL';if(verdict==='PASS'&&!deterministicPass)verdict=x.revision_count<1?'REPAIR':'FAIL';const instructions=Array.isArray(q.repair_instructions)?q.repair_instructions.map(String).slice(0,12):[];const repair=verdict==='REPAIR'&&x.revision_count<1&&instructions.length>0;return [{json:{...x,quality:{...q,verdict,failed_rules:[...(Array.isArray(q.failed_rules)?q.failed_rules:[]),...(badRefs.length?[`Unknown evidence IDs: ${[...new Set(badRefs)].join(', ')}`]:[])],repair_instructions:instructions,requires_human:q.requires_human===true||verdict==='HUMAN_REVIEW',diagnostics:{unknown_evidence_ids:[...new Set(badRefs)],high_stakes_terms_seen:[...new Set(highStake)]}},repair_needed:repair,critic_model:r.model}}];"""),
        if_true("One Blueprint Revision?", 380, 0, "={{ $json.repair_needed }}"),
        code("Prepare Bounded Blueprint Revision", 620, -120, r"""const x=$input.first().json;return [{json:{...x,request:{model:'Qwen/Qwen3-235B-A22B-Instruct-2507',temperature:0.05,max_tokens:3000,response_format:{type:'json_object'},messages:[{role:'system',content:'You are the bounded Blueprint Reviser. Apply only the supplied critic instructions to the supplied Blueprint. Preserve all supported content and citation IDs. Do not add research, sources, market numbers, willingness-to-pay claims, forecasts or external actions. Unknowns stay unknown. Return the complete revised Blueprint JSON only.'},{role:'user',content:JSON.stringify({blueprint:x.blueprint,repair_instructions:x.quality.repair_instructions})}]}}}];"""),
        http_nebius("Nebius — One Blueprint Revision", 860, -120, 45000),
        code("Parse Bounded Revision", 1100, -120, r"""const x=$('Parse and Enforce Quality Verdict').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error('BLUEPRINT_REVISION_EMPTY');let parsed;try{parsed=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c}catch{throw new Error('BLUEPRINT_REVISION_JSON_PARSE_FAILED')}let b=parsed.blueprint??parsed;for(const k of ['schema_version','status','product_idea','starting_position','dashboard','sections','next_route'])if(b[k]==null)throw new Error('BLUEPRINT_REVISION_SCHEMA_MISSING:'+k);const originalCitations=x.blueprint.citations??[];const citationById=new Map(originalCitations.map(e=>[e.evidence_id,e]));const attemptedIds=new Set([...(b.citations??[]).map(e=>e.evidence_id),...(b.sections??[]).flatMap(s=>s.evidence_ids??[])]);const invented=[...attemptedIds].filter(id=>!citationById.has(id));b.citations=originalCitations;const sectionKeys=new Set(['foundation','customer_demand','competitor_intelligence','market_economics','operating_model','financial_readiness','validation','launch_distribution','growth_optimization','final_blueprint']);const statuses=new Set(['NOT_REQUESTED','BLOCKED','NEEDS_INPUT','IN_PROGRESS','AGENT_DONE','HUMAN_REVIEW','COMPLETED','PARTIAL','SAFE_FAILED']);b.sections=(Array.isArray(b.sections)?b.sections:[]).filter(s=>sectionKeys.has(s.section_key)).map(s=>({section_key:s.section_key,status:statuses.has(s.status)?s.status:'PARTIAL',completion_percent:Math.max(0,Math.min(100,Math.round(Number(s.completion_percent)||0))),summary:s.summary??{},open_questions:Array.isArray(s.open_questions)?s.open_questions.map(String):[],evidence_ids:Array.isArray(s.evidence_ids)?s.evidence_ids.filter(id=>citationById.has(id)):[]}));b.limitations=[...(Array.isArray(b.limitations)?b.limitations:[]),...(invented.length?[`Revision attempted unapproved evidence IDs and they were removed: ${invented.join(', ')}`]:[])];return [{json:{...x,blueprint:b,revision_count:1,before_quality:x.quality,revision_diagnostics:{invented_evidence_ids_removed:invented},request:{model:'openai/gpt-oss-120b',reasoning_effort:'low',temperature:0,max_tokens:1200,response_format:{type:'json_object'},messages:[{role:'system',content:'Final independent re-score after the only allowed Blueprint revision. Use the same seven rubric keys. Return JSON with verdict PASS|FAIL|HUMAN_REVIEW, overall_score, rubric_scores, failed_rules, repair_instructions as an empty array, requires_human, and critic_notes. Do not request another revision. Fail closed on unsupported high-stakes claims, invented facts, removed/unapproved evidence, or broken citations.'},{role:'user',content:JSON.stringify({blueprint:b,previous_critic:x.quality,revision_diagnostics:{invented_evidence_ids_removed:invented}})}]}}}];"""),
        http_nebius("Nebius — Final Blueprint Re-Critic", 1340, -120),
        code("Finalize Revised Quality", 1580, -120, r"""const x=$('Parse Bounded Revision').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error('FINAL_QUALITY_CRITIC_EMPTY');let q;try{q=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c}catch{throw new Error('FINAL_QUALITY_JSON_PARSE_FAILED')}const s=q.rubric_scores??{};const pass=q.verdict==='PASS'&&Number(q.overall_score)>=0.78&&Number(s.groundedness)>=0.8&&Number(s.assumption_hygiene)>=0.8&&Number(s.calculation_integrity)>=0.8&&Number(s.scope_compliance)>=0.999;return [{json:{blueprint:x.blueprint,quality:{...q,verdict:pass?'PASS':(q.requires_human?'HUMAN_REVIEW':'FAIL'),repair_instructions:[]},before_quality:x.before_quality,revision_count:1,quality_improved:Number(q.overall_score)>Number(x.before_quality.overall_score),status:pass?'QUALITY_PASSED':(q.requires_human?'HUMAN_REVIEW':'QUALITY_FAILED'),next_route:pass?'MEMORY_INDEX':(q.requires_human?'HUMAN_REVIEW':'PARTIAL_COMPLETE'),correlation_id:x.correlation_id,agent_trace:[...(x.blueprint.agent_trace??[]),{agent:'BLUEPRINT_CRITIC',model:r.model,status:pass?'SUCCEEDED':'PARTIAL',revision_count:1}]}}];"""),
        code("Use First Quality Verdict", 620, 120, r"""const x=$input.first().json;const pass=x.quality.verdict==='PASS';return [{json:{blueprint:x.blueprint,quality:x.quality,before_quality:null,revision_count:x.revision_count,quality_improved:null,status:pass?'QUALITY_PASSED':(x.quality.requires_human?'HUMAN_REVIEW':'QUALITY_FAILED'),next_route:pass?'MEMORY_INDEX':(x.quality.requires_human?'HUMAN_REVIEW':'PARTIAL_COMPLETE'),correlation_id:x.correlation_id,agent_trace:[...(x.blueprint.agent_trace??[]),{agent:'BLUEPRINT_CRITIC',model:x.critic_model,status:pass?'SUCCEEDED':'PARTIAL',revision_count:x.revision_count}]}}];"""),
    ]
    c = {}
    connect(c, "Run Quality Gate Test", "Create Safe Quality Fixture")
    connect(c, "Create Safe Quality Fixture", "Validate Quality Contract")
    connect(c, "When Called for Blueprint Quality", "Validate Quality Contract")
    connect(c, "Validate Quality Contract", "Prepare Independent Blueprint Critic")
    connect(c, "Prepare Independent Blueprint Critic", "Nebius — Blueprint Quality Critic")
    connect(c, "Nebius — Blueprint Quality Critic", "Parse and Enforce Quality Verdict")
    connect(c, "Parse and Enforce Quality Verdict", "One Blueprint Revision?")
    connect(c, "One Blueprint Revision?", "Prepare Bounded Blueprint Revision", 0)
    connect(c, "Prepare Bounded Blueprint Revision", "Nebius — One Blueprint Revision")
    connect(c, "Nebius — One Blueprint Revision", "Parse Bounded Revision")
    connect(c, "Parse Bounded Revision", "Nebius — Final Blueprint Re-Critic")
    connect(c, "Nebius — Final Blueprint Re-Critic", "Finalize Revised Quality")
    connect(c, "One Blueprint Revision?", "Use First Quality Verdict", 1)
    return workflow("bpQa01BlueprintQuality", "BP-QA-01 Blueprint Quality Gate", nodes, c, 120)


def build_supervisor() -> dict:
    nodes = [
        manual("Run Supervisor Test", -1080, -180),
        code("Create Safe Supervisor Fixture", -860, -180, r"""return [{json:{command:'START',idea_text:'A private evidence workspace that helps an early-stage founder validate an existing product idea before committing a large build budget.',optional_industry:'Founder tools',geography:'Global',requested_modules:['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation'],founder_inputs:{available_budget:5000,monthly_build_budget:1000,hours_per_week:12,target_monthly_price:49,currency:'USD',current_stage:'idea',work_completed:[],constraints:['solo founder']},correlation_id:'bp-supervisor-safe-test',state:{transition_count:0,search_cycle_count:0,tool_call_count:0,revision_count:0},test_mode:true}}];"""),
        sub_trigger("When Called by Start Chat or Resume", -1080, 80),
        code("Validate Supervisor Contract and Guard Scope", -620, 0, r"""const src=$input.first()?.json??{};const command=String(src.command??'START').toUpperCase();const allowedCommands=['START','RESUME','RUN_MODULE','ANSWER_CHAT','CANCEL'];if(!allowedCommands.includes(command))throw new Error('SUPERVISOR_COMMAND_INVALID');const idea=String(src.idea_text??src.state?.project?.idea_text??'').trim();const forbidden=['recipient','email_to','message_to','phone_number','payment','publish_target','delete_target'];const forbiddenFields=forbidden.filter(k=>src[k]!=null);const actionText=String(src.message??'').trim();const operational=/\b(send|email|message|ping|call|contact|post|publish|buy|pay|book|schedule|delete|remove)\b/i.test(actionText);const draftOnly=/\b(draft|write|prepare)\b/i.test(actionText)&&!/\b(send|ping|call|contact|post|publish|buy|pay|book|schedule|delete|remove)\b/i.test(actionText);const external=operational&&!draftOnly;const allowedModules=['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation','launch_distribution','growth_optimization'];const requested=Array.isArray(src.requested_modules)?[...new Set(src.requested_modules.filter(x=>allowedModules.includes(x)))]:[];const s=src.state&&typeof src.state==='object'?src.state:{};const counters={transition_count:Number(s.transition_count??0),search_cycle_count:Number(s.search_cycle_count??0),tool_call_count:Number(s.tool_call_count??0),revision_count:Number(s.revision_count??0)};const budgetExceeded=counters.transition_count>=20||counters.search_cycle_count>=3||counters.tool_call_count>=80||counters.revision_count>=3;const scopeDenied=forbiddenFields.length>0||external;const missing=[];if(command!=='CANCEL'&&idea.length<10)missing.push('Describe the product or business idea in at least one clear sentence.');const route=scopeDenied?{route:'SAFE_FAIL',reason_code:'OUT_OF_SCOPE',confidence:1,next_status:'SAFE_FAILED',requires_human:false,terminal:true}:budgetExceeded?{route:'SAFE_FAIL',reason_code:'RUN_BUDGET_EXHAUSTED',confidence:1,next_status:'SAFE_FAILED',requires_human:false,terminal:true}:command==='CANCEL'?{route:'CANCEL',reason_code:'FOUNDER_CANCELLED',confidence:1,next_status:'CANCELLED',requires_human:false,terminal:true}:missing.length?{route:'FOUNDER_INPUT',reason_code:'MISSING_IDEA',confidence:1,next_status:'NEEDS_INPUT',requires_human:true,terminal:false}:{route:'RESEARCH_SUITE',reason_code:command==='RUN_MODULE'?'FOUNDER_REQUESTED_MODULE':'VALID_START',confidence:1,next_status:'RESEARCHING',requires_human:false,terminal:false};return [{json:{schema_version:'bp-supervisor-state-v1',command,authorization:String(src.authorization??''),owner_id:src.owner_id??null,project_id:src.project_id??null,run_id:src.run_id??null,correlation_id:String(src.correlation_id??`bp-supervisor-${Date.now()}`).slice(0,200),idea_text:idea,optional_industry:String(src.optional_industry??'').trim()||null,geography:String(src.geography??'').trim()||null,requested_modules:requested.length?requested:['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation'],founder_inputs:src.founder_inputs&&typeof src.founder_inputs==='object'?src.founder_inputs:{},human_decision:src.human_decision??null,state:s,test_mode:src.test_mode===true,route_decision:{...route,missing_information:missing,allowed_next_routes:route.route==='RESEARCH_SUITE'?['BLUEPRINT_QUALITY','FOUNDER_INPUT','HUMAN_REVIEW','PARTIAL_COMPLETE']:[],route_evidence:[route.reason_code],budget_snapshot:counters},should_execute_core:route.route==='RESEARCH_SUITE'}}];"""),
        if_true("Run Research Engine?", -380, 0, "={{ $json.should_execute_core }}"),
        code("Build Visible Supervisor Outcome", -140, 160, r"""const x=$input.first().json;const denied=x.route_decision.reason_code==='OUT_OF_SCOPE';return [{json:{schema_version:'bp-supervisor-result-v1',status:x.route_decision.next_status,route:x.route_decision.route,terminal:x.route_decision.terminal,requires_human:x.route_decision.requires_human,message:denied?'Blueprint can research and evaluate a founder idea, but it cannot contact people, send messages, publish, purchase, book, pay, or delete anything.':(x.route_decision.route==='FOUNDER_INPUT'?x.route_decision.missing_information[0]:(x.route_decision.route==='CANCEL'?'The Blueprint run was cancelled safely.':'The run reached a configured safety limit and stopped safely.')),missing_information:x.route_decision.missing_information,route_decision:x.route_decision,correlation_id:x.correlation_id,persistence_envelope:{owner_id:x.owner_id,project_id:x.project_id,run_id:x.run_id}}}];"""),
        execute_workflow("Execute BP-CORE-45 Research Engine", "bpCore45Evidence01", -140, -120),
        code("Inspect Research Result and Route", 100, -120, r"""const b=$input.first()?.json??{};const hasBlueprint=b.schema_version==='bp-blueprint-v1'&&Array.isArray(b.sections);if(!hasBlueprint)throw new Error('RESEARCH_ENGINE_INVALID_OUTPUT');const needsHuman=['HUMAN_REVIEW','NEEDS_INPUT','SAFE_FAILED'].includes(b.status)||['HUMAN_REVIEW','FOUNDER_INPUT','SAFE_FAIL'].includes(b.next_route);return [{json:{blueprint:b,revision_count:Number(b.audit?.revision_count??0),correlation_id:b.persistence_envelope?.correlation_id??'bp-supervisor',research_requires_human:needsHuman,supervisor_route:needsHuman?'HUMAN_REVIEW':'BLUEPRINT_QUALITY'}}];"""),
        if_true("Research Needs Human?", 340, -120, "={{ $json.research_requires_human }}"),
        code("Build Research Human Checkpoint", 580, 20, r"""const x=$input.first().json;return [{json:{schema_version:'bp-supervisor-result-v1',status:'HUMAN_REVIEW',route:'HUMAN_REVIEW',terminal:false,requires_human:true,message:'Research completed partially and needs a founder decision or clarification before it can continue.',blueprint:x.blueprint,questions:x.blueprint.sections.flatMap(s=>s.open_questions??[]).slice(0,8),limitations:x.blueprint.limitations??[],correlation_id:x.correlation_id}}];"""),
        execute_workflow("Execute BP-QA-01 Quality Gate", "bpQa01BlueprintQuality", 580, -220),
        code("Finalize Supervisor Decision", 820, -220, r"""const q=$input.first()?.json??{};if(!q.quality||!q.blueprint)throw new Error('QUALITY_GATE_INVALID_OUTPUT');const pass=q.status==='QUALITY_PASSED'&&q.quality.verdict==='PASS';const human=q.status==='HUMAN_REVIEW'||q.quality.requires_human===true;const citations=(q.blueprint.citations??[]).filter(c=>['ACCEPT','ACCEPT_WITH_LIMITATION'].includes(c.auditor_verdict));return [{json:{schema_version:'bp-supervisor-result-v1',status:pass?'COMPLETED':(human?'HUMAN_REVIEW':'PARTIAL'),route:pass?'MEMORY_INDEX':(human?'HUMAN_REVIEW':'PARTIAL_COMPLETE'),terminal:pass||!human,requires_human:human,message:pass?'Blueprint passed the independent final quality gate. Accepted evidence is ready for project-isolated memory indexing.':(human?'The Blueprint needs a founder or reviewer decision.':'The best safe partial Blueprint has been preserved with its quality warning.'),blueprint:q.blueprint,quality:q.quality,revision_count:q.revision_count,quality_improved:q.quality_improved,accepted_evidence_for_memory:pass?citations:[],memory_write_authorized:pass,correlation_id:q.correlation_id,agent_trace:[...(q.agent_trace??[]),{agent:'SUPERVISOR',status:pass?'SUCCEEDED':(human?'PARTIAL':'SUCCEEDED'),route:pass?'MEMORY_INDEX':(human?'HUMAN_REVIEW':'PARTIAL_COMPLETE')}],persistence_envelope:q.blueprint.persistence_envelope??{}}}];"""),
        code("Prepare Supervisor Persistence", 1060, -20, r"""const result=$input.first()?.json??{};const v=$('Validate Supervisor Contract and Guard Scope').first().json;const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const enriched={...result,command:v.command,owner_id:v.owner_id,project_id:v.project_id,run_id:v.run_id,persistence_envelope:{...(result.persistence_envelope??{}),owner_id:v.owner_id,project_id:v.project_id,run_id:v.run_id,correlation_id:v.correlation_id}};const persist_required=!v.test_mode&&uuid.test(String(v.owner_id??''))&&uuid.test(String(v.project_id??''))&&uuid.test(String(v.run_id??''))&&/^Bearer\s+\S+$/i.test(v.authorization);return [{json:{result:enriched,persist_required,authorization:v.authorization,rpc_body:{p_result:enriched}}}];"""),
        if_true("Persist Production Supervisor Result?", 1300, -20, "={{ $json.persist_required }}"),
        http_supabase_rpc("Persist Supervisor Result Atomically", "persist_supervisor_result", 1540, -120),
        code("Return Persisted Supervisor Result", 1780, -120, r"""const prep=$('Prepare Supervisor Persistence').first().json;const p=$input.first()?.json??{};if(p.error||p.persisted!==true)return [{json:{...prep.result,status:'HUMAN_REVIEW',route:'HUMAN_REVIEW',terminal:false,requires_human:true,message:'The research result was preserved in this execution, but durable persistence failed. Review the audit before retrying.',persistence:{persisted:false,reason:'SUPABASE_PERSISTENCE_FAILED'}}}];return [{json:{...prep.result,persistence:p}}];"""),
        code("Return Nonproduction Supervisor Result", 1540, 100, r"""const x=$input.first().json;return [{json:{...x.result,persistence:{persisted:false,reason:$('Validate Supervisor Contract and Guard Scope').first().json.test_mode?'TEST_MODE':'AUTHENTICATED_CONTEXT_REQUIRED'}}}];"""),
    ]
    c = {}
    connect(c, "Run Supervisor Test", "Create Safe Supervisor Fixture")
    connect(c, "Create Safe Supervisor Fixture", "Validate Supervisor Contract and Guard Scope")
    connect(c, "When Called by Start Chat or Resume", "Validate Supervisor Contract and Guard Scope")
    connect(c, "Validate Supervisor Contract and Guard Scope", "Run Research Engine?")
    connect(c, "Run Research Engine?", "Execute BP-CORE-45 Research Engine", 0)
    connect(c, "Run Research Engine?", "Build Visible Supervisor Outcome", 1)
    connect(c, "Execute BP-CORE-45 Research Engine", "Inspect Research Result and Route")
    connect(c, "Inspect Research Result and Route", "Research Needs Human?")
    connect(c, "Research Needs Human?", "Build Research Human Checkpoint", 0)
    connect(c, "Research Needs Human?", "Execute BP-QA-01 Quality Gate", 1)
    connect(c, "Execute BP-QA-01 Quality Gate", "Finalize Supervisor Decision")
    connect(c, "Build Visible Supervisor Outcome", "Prepare Supervisor Persistence")
    connect(c, "Build Research Human Checkpoint", "Prepare Supervisor Persistence")
    connect(c, "Finalize Supervisor Decision", "Prepare Supervisor Persistence")
    connect(c, "Prepare Supervisor Persistence", "Persist Production Supervisor Result?")
    connect(c, "Persist Production Supervisor Result?", "Persist Supervisor Result Atomically", 0)
    connect(c, "Persist Supervisor Result Atomically", "Return Persisted Supervisor Result")
    connect(c, "Persist Production Supervisor Result?", "Return Nonproduction Supervisor Result", 1)
    return workflow("bp00Supervisor", "BP-00 Adaptive Supervisor", nodes, c, 240)


def build_chat() -> dict:
    nodes = [
        webhook("POST Blueprint Research Chat", "blueprint/chat", -1220, 0),
        manual("Run Research Copilot Test", -1220, -220),
        code("Create Safe Chat Fixture", -1000, -220, r"""return [{json:{body:{message:'What should I validate next and which evidence supports that?',project_id:'00000000-0000-4000-8000-000000000001',run_id:null,thread_id:null,correlation_id:'bp-chat-safe-test',confirmed_command:false},test_mode:true,context:{run:{status:'COMPLETED',current_route:'COMPLETE'},project:{idea_text:'An evidence workspace for founders.'},sections:[{section_key:'customer_demand',status:'AGENT_DONE',open_questions:['Will founders pay for this?'],evidence_ids:['ev-test-1']}],accepted_evidence:[{id:'ev-test-1',claim:'Founders report manual validation work.',source_url:'https://example.com/founder-research',auditor_verdict:'ACCEPT_WITH_LIMITATION'}],quality_checks:[{verdict:'PASS'}]}}}];"""),
        code("Validate Chat Request and Scope", -760, 0, r"""const raw=$input.first()?.json??{};let b=raw.body??raw;if(typeof b==='string'){try{b=JSON.parse(b)}catch{b={}}}const headers=Object.fromEntries(Object.entries(raw.headers??{}).map(([k,v])=>[String(k).toLowerCase(),v]));const message=String(b.message??'').trim();const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const authorization=String(headers.authorization??'').trim();const projectId=String(b.project_id??'');const testMode=raw.test_mode===true;const operational=/\b(send|email|message|ping|call|contact|post|publish|buy|pay|book|schedule|delete|remove)\b/i.test(message);const draftOnly=/\b(draft|write|prepare)\b/i.test(message)&&!/\b(send|ping|call|contact|post|publish|buy|pay|book|schedule|delete|remove)\b/i.test(message);const action=operational&&!draftOnly;const errors=[];if(message.length<1||message.length>4000)errors.push('MESSAGE_LENGTH');if(!uuid.test(projectId))errors.push('PROJECT_ID');if(!testMode&&!/^Bearer\s+\S+$/i.test(authorization))errors.push('AUTHORIZATION_REQUIRED');return [{json:{valid:errors.length===0&&!action,scope_denied:action,errors,status_code:action?422:(errors.includes('AUTHORIZATION_REQUIRED')?401:400),message,project_id:projectId,run_id:uuid.test(String(b.run_id??''))?b.run_id:null,thread_id:uuid.test(String(b.thread_id??''))?b.thread_id:null,correlation_id:String(b.correlation_id??`bp-chat-${Date.now()}`).slice(0,200),confirmed_command:b.confirmed_command===true,authorization,test_mode:testMode,context:raw.context??null}}];"""),
        if_true("Chat Request Allowed?", -520, 0, "={{ $json.valid }}"),
        code("Build Chat Denial or Validation Error", -280, 160, r"""const x=$input.first().json;return [{json:{status_code:x.status_code,response:{status:x.scope_denied?'OUT_OF_SCOPE':'SAFE_FAILED',intent:x.scope_denied?'OUT_OF_SCOPE':'AMBIGUOUS',answer:x.scope_denied?'Blueprint can discuss and research your idea, but it cannot contact people, send messages, publish, purchase, book, pay, or delete anything. I can turn that request into a founder-run experiment or draft.':'The chat request is invalid or the session is missing. Please sign in and try again.',citations:[],suggested_actions:[],command:null,limitations:x.errors,correlation_id:x.correlation_id}}}];"""),
        if_true("Use Embedded Test Context?", -280, -80, "={{ $json.test_mode }}"),
        code("Use Safe Embedded Context", -40, -180, r"""const x=$('Validate Chat Request and Scope').first().json;return [{json:{...x,context:x.context??{}}}];"""),
        node("Verify Chat Supabase User", "n8n-nodes-base.httpRequest", -40, 20, {"url": f"{SUPABASE_URL}/auth/v1/user", "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $('Validate Chat Request and Scope').first().json.authorization }}"}]}, "options": {"timeout": 15000}}, 4.5),
        code("Prepare Supervisor Context Request", 200, 20, r"""const v=$('Validate Chat Request and Scope').first().json;const u=$input.first().json;if(!u.id)throw new Error('CHAT_UNAUTHENTICATED');if(!v.run_id)throw new Error('CHAT_RUN_REQUIRED_FOR_RESEARCH_QA');return [{json:{...v,authenticated_user_id:u.id,rpc_body:{p_run_id:v.run_id}}}];"""),
        node("Load Grounded Supervisor Context", "n8n-nodes-base.httpRequest", 440, 20, {"method": "POST", "url": f"{SUPABASE_URL}/rest/v1/rpc/get_supervisor_context", "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth", "sendHeaders": True, "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $json.authorization }}"}, {"name": "Content-Type", "value": "application/json"}]}, "sendBody": True, "contentType": "raw", "rawContentType": "application/json", "body": "={{ JSON.stringify($json.rpc_body) }}", "options": {"timeout": 15000}}, 4.5),
        code("Attach Loaded Chat Context", 680, 20, r"""const v=$('Validate Chat Request and Scope').first().json;const ctx=$input.first().json;if(ctx.error)throw new Error('CHAT_CONTEXT_LOAD_FAILED');return [{json:{...v,context:ctx}}];"""),
        code("Classify Chat Intent Deterministically", 920, -100, r"""const x=$input.first().json;const m=x.message.toLowerCase();let intent='QUESTION',target=null;if(/\b(cancel|stop)\b/.test(m))intent='CANCEL';else if(/\b(run|rerun|research|analy[sz]e|investigate)\b/.test(m)){intent='RUN_MODULE';if(/compet/.test(m))target='competitor_intelligence';else if(/customer|user|demand|pain|willing/.test(m))target='customer_demand';else if(/market|industry|econom/.test(m))target='market_economics';else if(/financ|budget|runway|price|break.?even/.test(m))target='financial_readiness';else if(/validat|experiment|test/.test(m))target='validation'}else if(/\bnext\b|what should i do|recommend.*step/.test(m))intent='NEXT_STEP';else if(/phase|status|progress|what was done/.test(m))intent='EXPLAIN_PHASE';else if(/wrong|correct|change my|update my/.test(m))intent='CORRECTION';const runAllowed=intent==='RUN_MODULE'&&target&&x.confirmed_command;const needsConfirmation=intent==='RUN_MODULE'&&target&&!x.confirmed_command;return [{json:{...x,intent,target_module:target,run_allowed:runAllowed,needs_confirmation:needsConfirmation,answer_allowed:!['RUN_MODULE','CANCEL'].includes(intent)||!runAllowed}}];"""),
        if_true("Execute Confirmed Research Command?", 1160, -100, "={{ $json.run_allowed }}"),
        code("Prepare Supervisor Chat Command", 1400, -220, r"""const x=$input.first().json;const p=x.context.project??{};return [{json:{command:'RUN_MODULE',authorization:x.authorization,owner_id:x.authenticated_user_id??null,project_id:x.project_id,run_id:x.run_id,correlation_id:x.correlation_id,idea_text:String(p.idea_text??''),optional_industry:p.optional_industry??null,geography:p.geography??null,requested_modules:[x.target_module],founder_inputs:x.context.run?.original_request?.founder_inputs??{},state:x.context.run??{},message:x.message,test_mode:x.test_mode}}];"""),
        execute_workflow("Ask BP-00 to Run Research", "bp00Supervisor", 1640, -220),
        code("Build Queued Research Chat Response", 1880, -220, r"""const s=$input.first().json;return [{json:{status_code:202,response:{status:s.status==='COMPLETED'?'QUEUED':(s.status??'QUEUED'),intent:'RUN_MODULE',answer:s.message??'The requested research module was routed through the Supervisor.',citations:(s.blueprint?.citations??[]).map(c=>c.evidence_id).slice(0,12),suggested_actions:[],command:{route:s.route,status:s.status},limitations:s.blueprint?.limitations??[],correlation_id:s.correlation_id}}}];"""),
        if_true("Chat Needs Confirmation?", 1400, 20, "={{ $json.needs_confirmation }}"),
        code("Build Research Confirmation", 1640, 20, r"""const x=$input.first().json;return [{json:{status_code:200,response:{status:'NEEDS_CONFIRMATION',intent:'RUN_MODULE',answer:`I can ask the Supervisor to run ${x.target_module.replaceAll('_',' ')} research. This is read-only but will use research/model calls and update this Blueprint. Confirm to continue.`,citations:[],suggested_actions:[{action:'CONFIRM_RUN_MODULE',target_module:x.target_module}],command:{command:'RUN_MODULE',target_module:x.target_module,confirmation_required:true},limitations:[],correlation_id:x.correlation_id}}}];"""),
        code("Prepare Grounded Copilot Answer", 1640, 160, r"""const x=$input.first().json;const allowedEvidence=(x.context.accepted_evidence??[]).slice(0,30);const context={run:x.context.run??{},project:x.context.project??{},sections:x.context.sections??[],accepted_evidence:allowedEvidence,quality_checks:(x.context.quality_checks??[]).slice(0,5),approvals:(x.context.approvals??[]).slice(0,5),errors:(x.context.errors??[]).slice(0,5)};return [{json:{...x,request:{model:'Qwen/Qwen3-30B-A3B-Instruct-2507',temperature:0.1,max_tokens:1200,response_format:{type:'json_object'},messages:[{role:'system',content:'You are Blueprint Research Copilot. Answer only from the supplied project/run context and accepted evidence. Explain what was done, current status, evidence-supported findings, limitations, and next permitted steps. Every factual research statement must cite an evidence ID from the context. If the context does not answer the question, say UNKNOWN and suggest a bounded research module or founder input. Never claim to have run an action, never expose hidden reasoning, and never contact, send, publish, buy, book, pay, or delete. Return JSON with answer, citations array of accepted evidence IDs, suggested_actions array, limitations array.'},{role:'user',content:JSON.stringify({message:x.message,intent:x.intent,context})}]}}}];"""),
        http_nebius("Nebius — Grounded Research Copilot", 1880, 160),
        code("Validate Grounded Chat Answer", 2120, 160, r"""const x=$('Classify Chat Intent Deterministically').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error('CHAT_MODEL_EMPTY');let a;try{a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c}catch{throw new Error('CHAT_MODEL_JSON_PARSE_FAILED')}const allowed=new Set((x.context.accepted_evidence??[]).map(e=>e.id??e.evidence_id));const citations=Array.isArray(a.citations)?a.citations.filter(id=>allowed.has(id)):[];return [{json:{status_code:200,response:{status:'ANSWERED',intent:x.intent,answer:String(a.answer??'UNKNOWN').slice(0,8000),citations,suggested_actions:Array.isArray(a.suggested_actions)?a.suggested_actions.slice(0,6):[],command:null,limitations:Array.isArray(a.limitations)?a.limitations:[],correlation_id:x.correlation_id}}}];"""),
        code("Prepare Chat Exchange Persistence", 2360, 0, r"""const result=$input.first()?.json??{};const v=$('Validate Chat Request and Scope').first().json;let classified=null;try{classified=$('Classify Chat Intent Deterministically').first().json}catch{}const persist_required=!v.test_mode&&!v.scope_denied&&/^Bearer\s+\S+$/i.test(v.authorization)&&v.run_id!=null&&result.response?.answer;return [{json:{result,persist_required,authorization:v.authorization,rpc_body:{p_payload:{project_id:v.project_id,run_id:v.run_id,thread_id:v.thread_id,message:v.message,intent:result.response?.intent??classified?.intent??'AMBIGUOUS',target_module:classified?.target_module??null,response:result.response??{},correlation_id:v.correlation_id}}}}];"""),
        if_true("Persist Authenticated Chat Exchange?", 2600, 0, "={{ $json.persist_required }}"),
        http_supabase_rpc("Persist Chat Exchange Atomically", "append_chat_exchange", 2840, -100),
        code("Return Persisted Chat Response", 3080, -100, r"""const prep=$('Prepare Chat Exchange Persistence').first().json;const p=$input.first()?.json??{};if(p.error||p.persisted!==true)return [{json:{...prep.result,response:{...prep.result.response,limitations:[...(prep.result.response?.limitations??[]),'Chat history persistence failed; the answer is still visible in this response.']}}}];return [{json:{...prep.result,response:{...prep.result.response,thread_id:p.thread_id}}}];"""),
        code("Return Ephemeral Chat Response", 2840, 120, r"""return [{json:$input.first().json.result}];"""),
        respond("Respond Research Copilot", 3320, 0, "={{ JSON.stringify($json.response) }}"),
    ]
    # Add credentials to the two Supabase HTTP nodes after creation.
    for n in nodes:
        if n["name"] in {"Verify Chat Supabase User", "Load Grounded Supervisor Context"}:
            n["credentials"] = {"httpHeaderAuth": {"id": SUPABASE_PUBLIC_ID, "name": "BP Supabase Public"}}
            n["onError"] = "continueRegularOutput"

    c = {}
    connect(c, "POST Blueprint Research Chat", "Validate Chat Request and Scope")
    connect(c, "Run Research Copilot Test", "Create Safe Chat Fixture")
    connect(c, "Create Safe Chat Fixture", "Validate Chat Request and Scope")
    connect(c, "Validate Chat Request and Scope", "Chat Request Allowed?")
    connect(c, "Chat Request Allowed?", "Use Embedded Test Context?", 0)
    connect(c, "Chat Request Allowed?", "Build Chat Denial or Validation Error", 1)
    connect(c, "Build Chat Denial or Validation Error", "Prepare Chat Exchange Persistence")
    connect(c, "Use Embedded Test Context?", "Use Safe Embedded Context", 0)
    connect(c, "Use Embedded Test Context?", "Verify Chat Supabase User", 1)
    connect(c, "Verify Chat Supabase User", "Prepare Supervisor Context Request")
    connect(c, "Prepare Supervisor Context Request", "Load Grounded Supervisor Context")
    connect(c, "Load Grounded Supervisor Context", "Attach Loaded Chat Context")
    connect(c, "Use Safe Embedded Context", "Classify Chat Intent Deterministically")
    connect(c, "Attach Loaded Chat Context", "Classify Chat Intent Deterministically")
    connect(c, "Classify Chat Intent Deterministically", "Execute Confirmed Research Command?")
    connect(c, "Execute Confirmed Research Command?", "Prepare Supervisor Chat Command", 0)
    connect(c, "Prepare Supervisor Chat Command", "Ask BP-00 to Run Research")
    connect(c, "Ask BP-00 to Run Research", "Build Queued Research Chat Response")
    connect(c, "Build Queued Research Chat Response", "Prepare Chat Exchange Persistence")
    connect(c, "Execute Confirmed Research Command?", "Chat Needs Confirmation?", 1)
    connect(c, "Chat Needs Confirmation?", "Build Research Confirmation", 0)
    connect(c, "Build Research Confirmation", "Prepare Chat Exchange Persistence")
    connect(c, "Chat Needs Confirmation?", "Prepare Grounded Copilot Answer", 1)
    connect(c, "Prepare Grounded Copilot Answer", "Nebius — Grounded Research Copilot")
    connect(c, "Nebius — Grounded Research Copilot", "Validate Grounded Chat Answer")
    connect(c, "Validate Grounded Chat Answer", "Prepare Chat Exchange Persistence")
    connect(c, "Prepare Chat Exchange Persistence", "Persist Authenticated Chat Exchange?")
    connect(c, "Persist Authenticated Chat Exchange?", "Persist Chat Exchange Atomically", 0)
    connect(c, "Persist Chat Exchange Atomically", "Return Persisted Chat Response")
    connect(c, "Return Persisted Chat Response", "Respond Research Copilot")
    connect(c, "Persist Authenticated Chat Exchange?", "Return Ephemeral Chat Response", 1)
    connect(c, "Return Ephemeral Chat Response", "Respond Research Copilot")
    return workflow("bpChat01ResearchCopilot", "BP-CHAT-01 Research Copilot", nodes, c, 300)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    built = {
        "BP-QA-01-blueprint-quality.json": build_quality(),
        "BP-00-adaptive-supervisor.json": build_supervisor(),
        "BP-CHAT-01-research-copilot.json": build_chat(),
    }
    for filename, payload in built.items():
        path = OUT / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path} with {len(payload['nodes'])} nodes")


if __name__ == "__main__":
    main()
