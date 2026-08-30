"""Generate the importable n8n Phase 4-5 research-suite workflow.

The generated JSON contains no secret values. It references the credentials already
stored in the local Blueprint Evidence Dev n8n instance by immutable credential ID.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "n8n" / "BP-CORE-45-evidence-blueprint.json"


def uid(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"blueprint-evidence-dev/phase45/{name}"))


def node(name, node_type, version, x, y, parameters, **extra):
    data = {
        "parameters": parameters,
        "id": uid(name),
        "name": name,
        "type": node_type,
        "typeVersion": version,
        "position": [x, y],
    }
    data.update(extra)
    return data


def code(name, x, y, js):
    return node(name, "n8n-nodes-base.code", 2, x, y, {"jsCode": js})


def http(name, x, y, url, body, credential_id, credential_name, timeout=30000):
    return node(
        name,
        "n8n-nodes-base.httpRequest",
        4.5,
        x,
        y,
        {
            "method": "POST",
            "url": url,
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "contentType": "raw",
            "rawContentType": "application/json",
            "body": body,
            "options": {"timeout": timeout},
        },
        credentials={"httpHeaderAuth": {"id": credential_id, "name": credential_name}},
        onError="continueRegularOutput",
    )


def if_true(name, x, y, expression):
    return node(
        name,
        "n8n-nodes-base.if",
        2.2,
        x,
        y,
        {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [{
                    "id": uid(name + " condition"),
                    "leftValue": expression,
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }],
                "combinator": "and",
            },
            "options": {},
        },
    )


def connect(connections, source, target, output=0):
    connections.setdefault(source, {"main": []})
    while len(connections[source]["main"]) <= output:
        connections[source]["main"].append([])
    connections[source]["main"][output].append({"node": target, "type": "main", "index": 0})


NEBIUS_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"
YOU_URL = "https://ydc-index.io/v1/search"
NEBIUS_ID = "ewsT8nomHwfqyWCx"
YOU_ID = "yX3JLZ7MVY7LXlZ4"


nodes = [
    node("Run Phase 4-5 Test", "n8n-nodes-base.manualTrigger", 1, -1800, -180, {}),
    code("Create Safe Test Input", -1580, -180, r"""return [{json:{
  idea_text:'A private evidence workspace that helps an early-stage founder validate an existing product idea before committing a large build budget.',
  optional_industry:'Founder tools', geography:'Global',
  requested_modules:['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation'],
  founder_inputs:{available_budget:5000,monthly_build_budget:1000,hours_per_week:12,target_monthly_price:49,currency:'USD',current_stage:'idea',work_completed:[],constraints:['solo founder']},
  test_mode:true, correlation_id:'bp-phase45-safe-test'
}}];"""),
    node("When Called by Supervisor", "n8n-nodes-base.executeWorkflowTrigger", 1.2, -1800, 100, {"inputSource": "passthrough"}),
    code("Validate and Normalize Research Contract", -1340, 0, r"""const src=$input.first()?.json??{};
const forbidden=['recipient','email_to','message_to','phone_number','payment','publish_target','delete_target'];
const bad=forbidden.filter(k=>src[k]!=null);
const idea=String(src.idea_text??'').trim();
if(bad.length) throw new Error('OUT_OF_SCOPE_ACTION_FIELDS:'+bad.join(','));
if(idea.length<10||idea.length>10000) throw new Error('INVALID_IDEA_TEXT');
const allowed=['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation','launch_distribution','growth_optimization'];
const requested=Array.isArray(src.requested_modules)&&src.requested_modules.length?src.requested_modules.filter(x=>allowed.includes(x)):['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation'];
const fi=src.founder_inputs&&typeof src.founder_inputs==='object'?src.founder_inputs:{};
for(const k of ['available_budget','monthly_build_budget','hours_per_week','target_monthly_price']) if(fi[k]!=null&&(!Number.isFinite(Number(fi[k]))||Number(fi[k])<0)) throw new Error('INVALID_FOUNDER_INPUT:'+k);
return [{json:{schema_version:'bp-research-input-v1',owner_id:src.owner_id??null,project_id:src.project_id??null,run_id:src.run_id??null,correlation_id:String(src.correlation_id??`bp-${Date.now()}`).slice(0,200),idea_text:idea,optional_industry:String(src.optional_industry??'').trim()||null,geography:String(src.geography??'').trim()||null,requested_modules:[...new Set(requested)],founder_inputs:{...fi,currency:fi.currency?String(fi.currency).toUpperCase():null},test_mode:src.test_mode===true}}];"""),
    code("Prepare Idea Framer Agent", -1120, 0, r"""const x=$input.first().json;
const prompt=`Founder idea: ${x.idea_text}\nOptional industry: ${x.optional_industry??'unknown'}\nGeography: ${x.geography??'unknown'}\nFounder starting position: ${JSON.stringify(x.founder_inputs)}\nRequested modules: ${x.requested_modules.join(', ')}`;
return [{json:{...x,request:{model:'Qwen/Qwen3-30B-A3B-Instruct-2507',temperature:0.1,max_tokens:1000,response_format:{type:'json_object'},messages:[{role:'system',content:'You are Blueprint Idea Framer. Normalize only what the founder supplied. Do not invent facts. Return JSON with product_summary, target_customer, problem, desired_outcome, proposed_solution, industry, geography, assumptions (array), missing_questions (array), research_terms (array), and confidence 0..1. Unknown values must be the string UNKNOWN and create a precise missing question.'},{role:'user',content:prompt}]}}}];"""),
    http("Nebius — Idea Framer", -900, 0, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory"),
    code("Parse and Check Idea Frame", -680, 0, r"""const input=$input.first().json; const base=$('Validate and Normalize Research Contract').first().json;
function parse(r){const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'IDEA_FRAME_EMPTY');return typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;}
const f=parse(input); const keys=['product_summary','target_customer','problem','desired_outcome','proposed_solution','industry','geography'];
for(const k of keys) if(typeof f[k]!=='string'||!f[k].trim()) throw new Error('IDEA_FRAME_SCHEMA:'+k);
f.assumptions=Array.isArray(f.assumptions)?f.assumptions.map(String).slice(0,12):[]; f.missing_questions=Array.isArray(f.missing_questions)?f.missing_questions.map(String).slice(0,10):[]; f.research_terms=Array.isArray(f.research_terms)?f.research_terms.map(String).slice(0,12):[]; f.confidence=Math.max(0,Math.min(1,Number(f.confidence)||0));
return [{json:{...base,idea_frame:f,agent_trace:[{agent:'IDEA_FRAME',model:input.model??'Qwen/Qwen3-30B-A3B-Instruct-2507',status:'SUCCEEDED'}]}}];"""),
    code("Research Planner", -460, 0, r"""const x=$input.first().json; const f=x.idea_frame; const geo=f.geography==='UNKNOWN'?'':f.geography;
const cap=s=>String(s).trim().split(/\s+/).slice(0,45).join(' ').slice(0,380).trim();
const target=String(f.target_customer??'').split(/\s+/).slice(0,10).join(' ');
const terms=f.research_terms.slice(0,3).join(' ');
const core=[target,terms].filter(v=>v&&v!=='UNKNOWN').join(' ');
const qs={
 customer:cap(`${core} pain complaints reviews willingness to pay alternatives reddit g2 capterra ${geo}`),
 competitor:cap(`${core} competitors alternatives pricing features customer reviews ${geo}`),
 market:cap(`${core} market size industry report adoption spending statistics ${geo}`)
};
return [{json:{...x,research_plan:{version:'bp-plan-v1',queries:qs,search_budget:4,repair_budget:1,source_target:12,route:['customer_demand','competitor_intelligence','market_economics','evidence_audit']}}}];"""),
    http("You — Customer Demand Search", -240, 0, YOU_URL, "={{ JSON.stringify({ query: $('Research Planner').first().json.research_plan.queries.customer, count: 8 }) }}", YOU_ID, "BP You Search", 20000),
    http("You — Competitor Search", -20, 0, YOU_URL, "={{ JSON.stringify({ query: $('Research Planner').first().json.research_plan.queries.competitor, count: 8 }) }}", YOU_ID, "BP You Search", 20000),
    http("You — Market Search", 200, 0, YOU_URL, "={{ JSON.stringify({ query: $('Research Planner').first().json.research_plan.queries.market, count: 8 }) }}", YOU_ID, "BP You Search", 20000),
    code("Normalize Evidence Cards", 420, 0, r"""const base=$('Research Planner').first().json; const now=new Date().toISOString();
function h(s){let v=2166136261;for(const c of s){v^=c.charCodeAt(0);v=Math.imul(v,16777619)}return (v>>>0).toString(16).padStart(8,'0')}
function domain(u){try{return new URL(u).hostname.replace(/^www\./,'')}catch{return 'unknown.invalid'}}
function type(d){if(/\.gov\b/.test(d))return'GOVERNMENT';if(/\.edu\b|doi\.org|arxiv/.test(d))return'ACADEMIC';if(/reddit|quora|forum/.test(d))return'COMMUNITY';if(/g2|capterra|trustpilot|producthunt/.test(d))return'REVIEW';if(/techcrunch|reuters|forbes|news/.test(d))return'NEWS';return'OTHER'}
function candidates(obj){const out=[];const seen=new Set();function walk(v,d=0){if(d>5||v==null)return;if(Array.isArray(v)){for(const z of v)walk(z,d+1);return}if(typeof v!=='object')return;const u=v.url??v.link??v.source_url; if(typeof u==='string'&&u.startsWith('https://')&&!seen.has(u)){seen.add(u);out.push(v)}for(const z of Object.values(v))if(typeof z==='object')walk(z,d+1)}walk(obj);return out}
const specs=[['customer_demand','You — Customer Demand Search',base.research_plan.queries.customer],['competitor_intelligence','You — Competitor Search',base.research_plan.queries.competitor],['market_economics','You — Market Search',base.research_plan.queries.market]];
const cards=[]; const provider_failures=[];
for(const [stream,name,q] of specs){const raw=$(name).first().json??{};if(raw.error){provider_failures.push({stream,provider:'YOU',error_class:'PROVIDER'});continue}for(const r of candidates(raw).slice(0,8)){const u=r.url??r.link??r.source_url;const d=domain(u);const title=String(r.title??r.name??'Untitled source').slice(0,1000);const snippetText=Array.isArray(r.snippets)?r.snippets.slice(0,2).join(' '):'';const ex=String(snippetText||r.snippet||r.excerpt||r.description||r.text||'').trim().slice(0,4000);if(!ex)continue;cards.push({evidence_id:`ev-${h(stream+'|'+u+'|'+ex)}`,stream,claim:ex,source_url:u,source_title:title,source_domain:d,source_type:type(d),provider:'YOU',query:q,excerpt:ex,retrieved_at:now,limitations:['Search-result excerpt; suitable for directional research only until its source page is verified. Never treat it as payment, market-size, or other high-stakes proof.'],auditor_verdict:'PENDING'})}}
const unique=[...new Map(cards.map(c=>[c.source_url+'|'+c.claim,c])).values()];
return [{json:{...base,evidence_cards:unique,provider_failures,coverage:{customer_demand:unique.filter(c=>c.stream==='customer_demand').length,competitor_intelligence:unique.filter(c=>c.stream==='competitor_intelligence').length,market_economics:unique.filter(c=>c.stream==='market_economics').length,total:unique.length},agent_trace:[...base.agent_trace,{agent:'RESEARCH_PLANNER',status:'SUCCEEDED'},{agent:'PROVIDER_GATEWAY',provider:'YOU',status:provider_failures.length?'PARTIAL':'SUCCEEDED',tool_calls:3}]}}];"""),
]


def analysis_prepare(name, stream, role, x, y, previous_node):
    js = f"""const x=$input.first().json; const cards=x.evidence_cards.filter(c=>c.stream==='{stream}');
const payload={{idea_frame:x.idea_frame,evidence:cards.map(c=>({{id:c.evidence_id,title:c.source_title,url:c.source_url,excerpt:c.excerpt,limitations:c.limitations}}))}};
return [{{json:{{...x,request:{{model:'Qwen/Qwen3-235B-A22B-Instruct-2507',temperature:0.1,max_tokens:1400,response_format:{{type:'json_object'}},messages:[{{role:'system',content:'You are the {role} specialist inside Blueprint. Use only supplied evidence. Never use model memory as evidence. Distinguish observed signals, reasonable inferences, assumptions, contradictions, and unknowns. Every factual claim must cite evidence_ids. Return JSON with summary, observed_signals (array of objects with claim and evidence_ids), assumptions (array), risks (array), contradictions (array), unknowns (array), and recommended_next_tests (array).'}},{{role:'user',content:JSON.stringify(payload)}}]}}}}}}];"""
    nodes.append(code(name, x, y, js))
    nodes.append(http(previous_node, x + 220, y, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory"))


analysis_prepare("Prepare Customer Evidence Agent", "customer_demand", "Customer Demand", 640, 0, "Nebius — Customer Evidence")
nodes.append(code("Parse Customer Evidence", 1080, 0, r"""const x=$('Normalize Evidence Cards').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'CUSTOMER_AGENT_EMPTY');const a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;return [{json:{...x,analyses:{customer_demand:a},agent_trace:[...x.agent_trace,{agent:'CUSTOMER_DEMAND',model:r.model,status:'SUCCEEDED'}]}}];"""))
analysis_prepare("Prepare Competitor Intelligence Agent", "competitor_intelligence", "Competitor Intelligence", 1300, 0, "Nebius — Competitor Intelligence")
nodes.append(code("Parse Competitor Intelligence", 1740, 0, r"""const x=$('Parse Customer Evidence').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'COMPETITOR_AGENT_EMPTY');const a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;return [{json:{...x,analyses:{...x.analyses,competitor_intelligence:a},agent_trace:[...x.agent_trace,{agent:'COMPETITOR_INTELLIGENCE',model:r.model,status:'SUCCEEDED'}]}}];"""))
analysis_prepare("Prepare Market Economics Agent", "market_economics", "Market and Economics", 1960, 0, "Nebius — Market Economics")
nodes.append(code("Parse Market Economics", 2400, 0, r"""const x=$('Parse Competitor Intelligence').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'MARKET_AGENT_EMPTY');const a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;return [{json:{...x,analyses:{...x.analyses,market_economics:a},agent_trace:[...x.agent_trace,{agent:'MARKET_ECONOMICS',model:r.model,status:'SUCCEEDED'}]}}];"""))
nodes.extend([
    code("Deterministic Financial Scenario Agent", 2620, 0, r"""const x=$input.first().json;const f=x.founder_inputs??{};const n=v=>v==null?null:Number(v);const budget=n(f.available_budget),monthly=n(f.monthly_build_budget),price=n(f.target_monthly_price);const currency=f.currency??null;
const questions=[];if(budget==null)questions.push('What total amount can you afford to risk before receiving payment evidence?');if(monthly==null)questions.push('What monthly build-and-validation spend can you sustain?');if(price==null)questions.push('What price or price range do you want to test with real buyers?');if(!currency)questions.push('Which currency should the financial plan use?');
const evidenceBudget=budget==null?null:Math.round(budget*0.2*100)/100;const reserve=budget==null?null:Math.round(budget*0.5*100)/100;const buildCap=budget==null?null:Math.round(budget*0.3*100)/100;
const scenarios=['lean','base','stretch'].map((name,i)=>{const factor=[0.6,1,1.4][i];const monthlySpend=monthly==null?null:Math.round(monthly*factor*100)/100;const runway=budget==null||!monthlySpend?null:Math.floor(budget/monthlySpend*10)/10;const customers=price==null||!monthlySpend?null:Math.ceil(monthlySpend/price);return{name,monthly_spend:monthlySpend,runway_months:runway,customers_to_cover_monthly_spend:customers,assumption:`${name} scenario uses ${factor}x the founder's stated monthly build budget.`}});
const plan={calculation_version:'bp-finance-v1',currency,founder_inputs:{available_budget:budget,monthly_build_budget:monthly,hours_per_week:n(f.hours_per_week),target_monthly_price:price},staged_capital:{validation_budget:evidenceBudget,build_budget_cap:buildCap,reserve},scenarios,spend_gates:[{gate:'problem evidence',unlock:'Run low-cost interviews and demand tests',required_signal:'Repeated pain plus current workaround'},{gate:'payment evidence',unlock:'Increase build spend',required_signal:'Deposit, preorder, paid pilot, or signed LOI with budget owner'},{gate:'retention evidence',unlock:'Scale distribution spend',required_signal:'Repeat usage or renewal behavior'}],open_questions:questions,limitations:['These are deterministic scenarios from founder inputs, not a forecast.','Market-search excerpts do not justify revenue projections.']};
return [{json:{...x,financial_plan:plan,agent_trace:[...x.agent_trace,{agent:'FINANCIAL_SCENARIO',model:'DETERMINISTIC',status:questions.length?'PARTIAL':'SUCCEEDED'}]}}];"""),
    code("Prepare Validation and Distribution Agent", 2840, 0, r"""const x=$input.first().json;const payload={idea_frame:x.idea_frame,founder_inputs:x.founder_inputs,customer_analysis:x.analyses.customer_demand,competitor_analysis:x.analyses.competitor_intelligence,market_analysis:x.analyses.market_economics,evidence:x.evidence_cards};return [{json:{...x,request:{model:'Qwen/Qwen3-235B-A22B-Instruct-2507',temperature:0.1,max_tokens:1800,response_format:{type:'json_object'},messages:[{role:'system',content:'You are the Validation and Distribution specialist. Using only supplied evidence, design how this founder can find the first reachable users and test demand before scaling. Return JSON with first_user_definition, reachable_channels (array with channel, why_reachable, evidence_ids), experiment_ladder (array with hypothesis, smallest_test, success_threshold, failure_threshold, duration_days, cost_cap, human_approval_required), launch_sequence (array), growth_hypotheses (array), open_questions (array), risks (array), and assumptions (array). Never send messages, publish, buy ads, recruit people, or claim willingness to pay without binding payment evidence. All external actions are proposals requiring founder approval.'},{role:'user',content:JSON.stringify(payload)}]}}}];"""),
    http("Nebius — Validation and Distribution", 3060, 0, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory"),
    code("Parse Validation and Distribution", 3280, 0, r"""const x=$('Deterministic Financial Scenario Agent').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'VALIDATION_AGENT_EMPTY');const a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;for(const e of (a.experiment_ladder??[]))e.human_approval_required=true;return [{json:{...x,analyses:{...x.analyses,validation_distribution:a},agent_trace:[...x.agent_trace,{agent:'EXPERIMENT_DESIGNER',model:r.model,status:'SUCCEEDED'}]}}];"""),
    code("Prepare Independent Evidence Auditor", 3500, 0, r"""const x=$input.first().json;const evidence=x.evidence_cards.map(({auditor_verdict,...e})=>e);const payload={idea_frame:x.idea_frame,evidence,analyses:x.analyses,coverage:x.coverage,provider_failures:x.provider_failures};return [{json:{...x,request:{model:'openai/gpt-oss-120b',reasoning_effort:'low',temperature:0,max_tokens:1400,response_format:{type:'json_object'},messages:[{role:'system',content:'You are the silent independent Evidence Auditor. You assign the first audit verdict; do not interpret the absence of a prior verdict as failure. Do not add research or rewrite the answer. Grade each evidence ID by whether its URL, title, and excerpt support a specific analyst claim. A relevant search excerpt may be accepted with limitation for directional findings such as named alternatives, reported pain, workflows, or experiment ideas. It must NOT prove exact market size, revenue, willingness to pay, purchase intent, or other high-stakes numeric claims unless the excerpt is from an appropriate primary source and directly states it. Unsupported analyst claims remain assumptions; that alone does not block a PARTIAL evidence-led blueprint. Set can_synthesize true when at least three relevant IDs are accepted and each requested research stream has usable directional coverage; use human_review only for a genuine contradiction, unsafe request, or decision needing human authority. Return JSON: verdict PASS|REPAIR|HUMAN_REVIEW|FAIL, can_synthesize boolean, repair_needed boolean, human_review boolean, coverage_scores object (0..1 per stream), accepted_ids array, rejected_ids array, contradictions array, reasons array, weakest_stream, and repair_query. Never accept a claim merely because it sounds plausible.'},{role:'user',content:JSON.stringify(payload)}]}}}];"""),
    http("Nebius — Independent Evidence Audit", 3720, 0, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory"),
    code("Parse Audit and Decide Route", 3940, 0, r"""const x=$('Parse Validation and Distribution').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'AUDITOR_EMPTY');let a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;a.accepted_ids=Array.isArray(a.accepted_ids)?a.accepted_ids.filter(id=>x.evidence_cards.some(e=>e.evidence_id===id)):[];a.rejected_ids=Array.isArray(a.rejected_ids)?a.rejected_ids:[];a.reasons=Array.isArray(a.reasons)?a.reasons.map(String):[];const weak=Object.entries(x.coverage).filter(([k])=>k!=='total').sort((p,q)=>p[1]-q[1])[0]?.[0]??'customer_demand';const deterministicRepair=x.coverage.total<6||Object.values(x.coverage).slice(0,3).some(v=>v<1);const repair_needed=!a.human_review&&(deterministicRepair||a.repair_needed===true||a.verdict==='REPAIR');const can_synthesize=!repair_needed&&!a.human_review&&a.can_synthesize===true&&a.accepted_ids.length>=3;const repair_query=String(a.repair_query??`${x.idea_frame.target_customer} ${x.idea_frame.problem} ${weak} primary source statistics pricing`).slice(0,2000);return [{json:{...x,audit:{...a,weakest_stream:a.weakest_stream??weak,repair_query},repair_needed,can_synthesize,human_review:a.human_review===true,repair_applied:false,agent_trace:[...x.agent_trace,{agent:'EVIDENCE_AUDITOR',model:r.model,status:repair_needed?'RETRYING':(can_synthesize?'SUCCEEDED':'PARTIAL')}]}}];"""),
    if_true("One Bounded Research Repair?", 4160, 0, "={{ $json.repair_needed }}"),
    code("Prepare Repair Query", 3720, -120, r"""const x=$input.first().json;const raw=x.audit.repair_query||`${x.idea_frame.target_customer} ${x.idea_frame.problem} primary source evidence`;const repair_query=String(raw).trim().split(/\s+/).slice(0,45).join(' ').slice(0,380).trim();return [{json:{...x,repair_query}}];"""),
    http("You — One Repair Search", 3940, -120, YOU_URL, "={{ JSON.stringify({ query: $json.repair_query, count: 8 }) }}", YOU_ID, "BP You Search", 20000),
    code("Merge Repair Evidence", 4160, -120, r"""const x=$('Prepare Repair Query').first().json;const raw=$input.first().json;const now=new Date().toISOString();let arr=[];function walk(v,d=0){if(d>5||v==null)return;if(Array.isArray(v)){for(const z of v)walk(z,d+1);return}if(typeof v!=='object')return;const u=v.url??v.link??v.source_url;if(typeof u==='string'&&u.startsWith('https://'))arr.push(v);for(const z of Object.values(v))if(typeof z==='object')walk(z,d+1)}if(!raw.error)walk(raw);const existing=new Set(x.evidence_cards.map(e=>e.source_url));const cards=[];for(const r of arr){const u=r.url??r.link??r.source_url;if(existing.has(u))continue;const snippetText=Array.isArray(r.snippets)?r.snippets.slice(0,2).join(' '):'';const ex=String(snippetText||r.snippet||r.excerpt||r.description||r.text||'').trim();if(!ex)continue;let d='unknown.invalid';try{d=new URL(u).hostname.replace(/^www\./,'')}catch{};const id=`ev-repair-${cards.length}-${Date.now().toString(36)}`;cards.push({evidence_id:id,stream:'repair',claim:ex.slice(0,4000),source_url:u,source_title:String(r.title??r.name??'Repair source').slice(0,1000),source_domain:d,source_type:/\.gov\b/.test(d)?'GOVERNMENT':(/\.edu\b|doi/.test(d)?'ACADEMIC':'OTHER'),provider:'YOU',query:x.repair_query,excerpt:ex.slice(0,4000),retrieved_at:now,limitations:['Bounded repair search excerpt; directional use only until source-page verification.'],auditor_verdict:'PENDING'});existing.add(u);if(cards.length>=8)break}return [{json:{...x,evidence_cards:[...x.evidence_cards,...cards],coverage:{...x.coverage,total:x.evidence_cards.length+cards.length,repair:cards.length},repair_applied:true,repair_needed:false,agent_trace:[...x.agent_trace,{agent:'PROVIDER_GATEWAY',provider:'YOU',status:raw.error?'FAILED':'SUCCEEDED',tool_calls:1,reason:'BOUNDED_REPAIR'}]}}];"""),
    code("Prepare Re-Audit", 4380, -120, r"""const x=$input.first().json;const evidence=x.evidence_cards.map(({auditor_verdict,...e})=>e);return [{json:{...x,request:{model:'openai/gpt-oss-120b',reasoning_effort:'low',temperature:0,max_tokens:1200,response_format:{type:'json_object'},messages:[{role:'system',content:'You are performing the final independent evidence re-audit after the single allowed repair. Assign verdicts yourself. A relevant search excerpt may support directional claims with a limitation, but cannot prove exact market size, revenue, willingness to pay, or purchase intent. Unsupported claims remain UNKNOWN and must not enter the blueprint as facts. Set can_synthesize true when at least three IDs are relevant and the requested streams have enough directional coverage for an explicitly PARTIAL blueprint. Use human_review only for genuine contradiction, unsafe scope, or human authority—not merely because further real-world validation is recommended. Return JSON with verdict PASS|HUMAN_REVIEW|FAIL, can_synthesize boolean, human_review boolean, accepted_ids array, rejected_ids array, contradictions array, reasons array, coverage_scores object. Do not request another repair.'},{role:'user',content:JSON.stringify({idea_frame:x.idea_frame,evidence,analyses:x.analyses})}]}}}];"""),
    http("Nebius — Final Re-Audit", 4600, -120, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory"),
    code("Parse Final Re-Audit", 4820, -120, r"""const x=$('Merge Repair Evidence').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'REAUDIT_EMPTY');const a=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;const accepted=Array.isArray(a.accepted_ids)?a.accepted_ids.filter(id=>x.evidence_cards.some(e=>e.evidence_id===id)):[];const can=a.can_synthesize===true&&a.human_review!==true&&accepted.length>=3;return [{json:{...x,audit:{...a,accepted_ids:accepted},can_synthesize:can,human_review:a.human_review===true,repair_needed:false,agent_trace:[...x.agent_trace,{agent:'EVIDENCE_AUDITOR',model:r.model,status:can?'SUCCEEDED':(a.human_review?'PARTIAL':'FAILED'),reason:'FINAL_REAUDIT'}]}}];"""),
    code("Use First Audit Without Repair", 3720, 120, r"""const x=$input.first().json;return [{json:{...x,repair_applied:false}}];"""),
    code("Finalize Audited State", 5040, 0, r"""const x=$input.first().json;const accepted=new Set(x.audit.accepted_ids??[]);const cards=x.evidence_cards.map(e=>({...e,auditor_verdict:accepted.has(e.evidence_id)?'ACCEPT':((x.audit.rejected_ids??[]).includes(e.evidence_id)?'REJECT':'ACCEPT_WITH_LIMITATION')}));return [{json:{...x,evidence_cards:cards,accepted_evidence:cards.filter(e=>accepted.has(e.evidence_id)),can_synthesize:x.can_synthesize===true&&accepted.size>=3}}];"""),
    if_true("Evidence Gate Passed?", 5260, 0, "={{ $json.can_synthesize }}"),
    code("Prepare Blueprint Synthesis Agent", 5480, -120, r"""const x=$input.first().json;const payload={idea_frame:x.idea_frame,founder_inputs:x.founder_inputs,requested_modules:x.requested_modules,analyses:x.analyses,financial_plan:x.financial_plan,audit:x.audit,evidence:x.accepted_evidence};return [{json:{...x,request:{model:'Qwen/Qwen3-235B-A22B-Instruct-2507',temperature:0.1,max_tokens:3000,response_format:{type:'json_object'},messages:[{role:'system',content:'You are the Blueprint Synthesis Agent. Produce an actionable founder blueprint using only audited evidence and deterministic calculations supplied. Unknowns stay explicit. Return JSON with status COMPLETED|PARTIAL, executive_decision, dashboard {completion_percent,open_assumptions,positive_signals,open_risks}, sections array where every section has section_key,status,completion_percent,summary,open_questions,evidence_ids, plus next_route VALIDATION|FOUNDER_INPUT|HUMAN_REVIEW|COMPLETE and limitations array. Include requested sections and mark unrequested/dependent future sections honestly. Never invent market size, customer willingness to pay, competitor features, or financial projections.'},{role:'user',content:JSON.stringify(payload)}]}}}];"""),
    http("Nebius — Blueprint Synthesis", 5700, -120, NEBIUS_URL, "={{ JSON.stringify($json.request) }}", NEBIUS_ID, "BP Nebius Token Factory", 45000),
    code("Parse Complete Blueprint", 5920, -120, r"""const x=$('Finalize Audited State').first().json;const r=$input.first().json;const c=r.choices?.[0]?.message?.content;if(!c)throw new Error(r.error?.message??'SYNTHESIS_EMPTY');const b=typeof c==='string'?JSON.parse(c.replace(/^```json\s*|\s*```$/g,'')):c;const sectionKeys=['foundation','customer_demand','competitor_intelligence','market_economics','operating_model','financial_readiness','validation','launch_distribution','growth_optimization','final_blueprint'];const sections=Array.isArray(b.sections)?b.sections.filter(s=>sectionKeys.includes(s.section_key)).map(s=>({section_key:s.section_key,status:s.status??'PARTIAL',completion_percent:Math.max(0,Math.min(100,Math.round(Number(s.completion_percent)||0))),summary:s.summary??{},open_questions:Array.isArray(s.open_questions)?s.open_questions.map(String):[],evidence_ids:Array.isArray(s.evidence_ids)?s.evidence_ids.filter(id=>x.accepted_evidence.some(e=>e.evidence_id===id)):[]})):[];return [{json:{schema_version:'bp-blueprint-v1',status:b.status==='COMPLETED'?'COMPLETED':'PARTIAL',product_idea:x.idea_frame.product_summary,starting_position:{idea_text:x.idea_text,industry:x.optional_industry,geography:x.geography,founder_inputs:x.founder_inputs,idea_frame:x.idea_frame},dashboard:b.dashboard??{completion_percent:0,open_assumptions:x.idea_frame.assumptions.length,positive_signals:0,open_risks:0},executive_decision:b.executive_decision??{},sections,financial_plan:x.financial_plan,citations:x.accepted_evidence,next_route:['VALIDATION','FOUNDER_INPUT','HUMAN_REVIEW','COMPLETE'].includes(b.next_route)?b.next_route:'VALIDATION',limitations:[...(Array.isArray(b.limitations)?b.limitations:[]),...(x.provider_failures.length?['One or more research providers returned a partial failure.']:[])],audit:x.audit,agent_trace:[...x.agent_trace,{agent:'BLUEPRINT_SYNTHESIS',model:r.model,status:'SUCCEEDED'}],persistence_envelope:{owner_id:x.owner_id,project_id:x.project_id,run_id:x.run_id,correlation_id:x.correlation_id}}}];"""),
    code("Build Safe Partial Blueprint", 5480, 120, r"""const x=$input.first().json;const qs=[...(x.idea_frame.missing_questions??[]),...(x.financial_plan.open_questions??[])];const sections=['foundation','customer_demand','competitor_intelligence','market_economics','financial_readiness','validation','launch_distribution','growth_optimization'].map(k=>({section_key:k,status:x.requested_modules.includes(k)?(x.human_review?'HUMAN_REVIEW':'PARTIAL'):'NOT_REQUESTED',completion_percent:k==='foundation'?60:0,summary:k==='foundation'?x.idea_frame:{message:'Evidence gate did not support a complete section.'},open_questions:qs,evidence_ids:[]}));return [{json:{schema_version:'bp-blueprint-v1',status:x.human_review?'HUMAN_REVIEW':'PARTIAL',product_idea:x.idea_frame.product_summary,starting_position:{idea_text:x.idea_text,industry:x.optional_industry,geography:x.geography,founder_inputs:x.founder_inputs,idea_frame:x.idea_frame},dashboard:{completion_percent:10,open_assumptions:x.idea_frame.assumptions.length,positive_signals:0,open_risks:(x.audit.contradictions??[]).length+1},executive_decision:{decision:'INSUFFICIENT_EVIDENCE',reason:'The evidence gate did not support a trustworthy complete blueprint.'},sections,financial_plan:x.financial_plan,citations:x.evidence_cards.filter(e=>e.auditor_verdict==='ACCEPT'),next_route:x.human_review?'HUMAN_REVIEW':'FOUNDER_INPUT',limitations:x.audit.reasons??['Insufficient audited evidence.'],audit:x.audit,agent_trace:x.agent_trace,persistence_envelope:{owner_id:x.owner_id,project_id:x.project_id,run_id:x.run_id,correlation_id:x.correlation_id}}}];"""),
])


connections = {}
connect(connections, "Run Phase 4-5 Test", "Create Safe Test Input")
connect(connections, "Create Safe Test Input", "Validate and Normalize Research Contract")
connect(connections, "When Called by Supervisor", "Validate and Normalize Research Contract")
chain = [
    "Validate and Normalize Research Contract", "Prepare Idea Framer Agent", "Nebius — Idea Framer", "Parse and Check Idea Frame",
    "Research Planner", "You — Customer Demand Search", "You — Competitor Search", "You — Market Search", "Normalize Evidence Cards",
    "Prepare Customer Evidence Agent", "Nebius — Customer Evidence", "Parse Customer Evidence",
    "Prepare Competitor Intelligence Agent", "Nebius — Competitor Intelligence", "Parse Competitor Intelligence",
    "Prepare Market Economics Agent", "Nebius — Market Economics", "Parse Market Economics",
    "Deterministic Financial Scenario Agent", "Prepare Validation and Distribution Agent", "Nebius — Validation and Distribution", "Parse Validation and Distribution",
    "Prepare Independent Evidence Auditor", "Nebius — Independent Evidence Audit", "Parse Audit and Decide Route",
    "One Bounded Research Repair?",
]
for a, b in zip(chain, chain[1:]):
    connect(connections, a, b)
connect(connections, "One Bounded Research Repair?", "Prepare Repair Query", 0)
connect(connections, "Prepare Repair Query", "You — One Repair Search")
connect(connections, "You — One Repair Search", "Merge Repair Evidence")
connect(connections, "Merge Repair Evidence", "Prepare Re-Audit")
connect(connections, "Prepare Re-Audit", "Nebius — Final Re-Audit")
connect(connections, "Nebius — Final Re-Audit", "Parse Final Re-Audit")
connect(connections, "Parse Final Re-Audit", "Finalize Audited State")
connect(connections, "One Bounded Research Repair?", "Use First Audit Without Repair", 1)
connect(connections, "Use First Audit Without Repair", "Finalize Audited State")
connect(connections, "Finalize Audited State", "Evidence Gate Passed?")
connect(connections, "Evidence Gate Passed?", "Prepare Blueprint Synthesis Agent", 0)
connect(connections, "Prepare Blueprint Synthesis Agent", "Nebius — Blueprint Synthesis")
connect(connections, "Nebius — Blueprint Synthesis", "Parse Complete Blueprint")
connect(connections, "Evidence Gate Passed?", "Build Safe Partial Blueprint", 1)

workflow = {
    "id": "bpCore45Evidence01",
    "name": "BP-CORE-45 Evidence Blueprint",
    "nodes": nodes,
    "connections": connections,
    "pinData": {},
    "active": False,
    "settings": {"executionOrder": "v1", "timezone": "Asia/Calcutta", "errorWorkflow": "bp90ErrorAudit01", "saveExecutionProgress": True},
    "versionId": uid("workflow-version"),
    "meta": {"templateCredsSetupCompleted": True},
    "tags": [],
}

OUT.write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {OUT} with {len(nodes)} nodes")
