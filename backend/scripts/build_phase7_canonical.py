from __future__ import annotations

import json
from pathlib import Path

from build_phase6_workflows import (
    code,
    connect,
    execute_workflow,
    http_supabase_rpc,
    if_true,
    node,
    respond,
    sub_trigger,
    webhook,
    workflow,
)
from repair_chat_experience import NODE_CODE as CHAT_NODE_CODE


ROOT = Path(__file__).resolve().parents[1]
N8N = ROOT / "n8n"


def update_code(workflow_file: str, node_name: str, js_code: str) -> None:
    path = N8N / workflow_file
    payload = json.loads(path.read_text(encoding="utf-8"))
    target = next((node for node in payload["nodes"] if node["name"] == node_name), None)
    if target is None:
        raise RuntimeError(f"Missing node {node_name} in {workflow_file}")
    target["parameters"]["jsCode"] = js_code
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_controller() -> dict:
    nodes = [
        sub_trigger("When Called by Authenticated Start", -1500, 0),
        code(
            "Normalize Canonical Supervisor Command",
            -1280,
            0,
            r"""const src=$input.first()?.json??{};const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const authorization=String(src.authorization??'').trim();const aliases={user_research:'customer_demand',customer_research:'customer_demand',customer_demand:'customer_demand',competitor_research:'competitor_intelligence',competitor_intelligence:'competitor_intelligence',market_research:'market_economics',market_economics:'market_economics'};const selected=[...new Set((Array.isArray(src.requested_research)?src.requested_research:[]).map(x=>aliases[String(x).toLowerCase()]).filter(Boolean))];const valid=src.command==='START'&&uuid.test(String(src.project_id??''))&&uuid.test(String(src.run_id??''))&&Number(src.profile_version)>0&&/^Bearer\s+\S+$/i.test(authorization)&&selected.length>0;return [{json:{...src,authorization,requested_research:selected,planning_mode:'DISCOVER',profile_version:Number(src.profile_version??0),controller_cycle:Math.max(0,Math.trunc(Number(src.controller_cycle??0))),claim_limit:1,valid,error_code:valid?null:'INVALID_CANONICAL_START',safe_message:valid?'Authenticated dynamic orchestration accepted.':'The start contract is incomplete, so no autonomous work was dispatched.'}}];""",
        ),
        if_true("Canonical Command Valid?", -1060, 0, "={{ $json.valid }}"),
        code(
            "Prepare Dynamic Run State",
            -840,
            -120,
            r"""const x=$json;return [{json:{...x,rpc_body:{p_run_id:x.run_id}}}];""",
        ),
        http_supabase_rpc("Prepare or Resume Dynamic Run", "prepare_dynamic_run", -620, -120),
        code(
            "Bind Prepared Run State",
            -400,
            -120,
            r"""const base=$('Prepare Dynamic Run State').first().json;const raw=$input.first()?.json??{};const ok=raw.prepared===true&&raw.run&&raw.run.id===base.run_id;return [{json:{...base,prepare_ok:ok,prepared:raw,should_plan:ok&&raw.should_plan===true,can_work:ok&&!raw.terminal&&!raw.waiting_for_human,controller_status:ok?(raw.waiting_for_human?'WAITING_APPROVAL':raw.terminal?raw.run.status:'PLANNING'):'HUMAN_REVIEW',controller_route:ok?(raw.waiting_for_human?'HITL_RESUME':raw.terminal?'COMPLETE':'TASK_PLANNER'):'HUMAN_REVIEW',requires_human:!ok||raw.waiting_for_human===true,terminal:raw.terminal===true,message:ok?'Dynamic run state prepared.':'The supervisor could not prepare durable run state; the run was stopped safely.',provider_response:ok?undefined:raw}}];""",
        ),
        if_true("Run Can Continue?", -180, -120, "={{ $json.can_work }}"),
        if_true("Dynamic Plan Needed?", 40, -220, "={{ $json.should_plan }}"),
        execute_workflow("Execute Dynamic Task Planner", "bpPlan01DynamicTaskPlanner", 260, -300),
        code(
            "Use Existing Durable Plan",
            260,
            -120,
            r"""const x=$json;return [{json:{...x,status:'PLANNED',route:'TASK_SCHEDULER',requires_human:false,terminal:false,message:'Existing durable task graph will be resumed.'}}];""",
        ),
        code(
            "Bind Planner Decision",
            480,
            -220,
            r"""const base=$('Bind Prepared Run State').first().json;const decision=$input.first()?.json??{};const schedulable=decision.route==='TASK_SCHEDULER'&&decision.requires_human!==true;return [{json:{...base,plan_decision:decision,schedulable,controller_status:schedulable?'PLANNED':'HUMAN_REVIEW',controller_route:schedulable?'TASK_SCHEDULER':(decision.route??'HUMAN_REVIEW'),requires_human:!schedulable,message:decision.message??(schedulable?'Task graph ready.':'Task planning stopped safely.')}}];""",
        ),
        if_true("Plan Schedulable?", 700, -220, "={{ $json.schedulable }}"),
        code(
            "Build Scheduler Request",
            920,
            -300,
            r"""const x=$json;return [{json:{authorization:x.authorization,owner_id:x.owner_id,project_id:x.project_id,run_id:x.run_id,profile_version:x.profile_version,idea_text:x.idea_text,profile:x.profile??x.founder_inputs??{},requested_research:x.requested_research,claim_limit:1,controller_cycle:Number(x.controller_cycle??0),correlation_id:x.correlation_id,test_mode:false}}];""",
        ),
        execute_workflow("Execute One Eligible Task", "bpSched01EligibleTaskScheduler", 1140, -300),
        code(
            "Prepare Durable Snapshot Request",
            1360,
            -300,
            r"""const cycle=$json.controller_cycle??$('Build Scheduler Request').first().json.controller_cycle??0;return [{json:{scheduler_result:$json,authorization:$json.authorization??$('Build Scheduler Request').first().json.authorization,run_id:$json.run_id??$('Build Scheduler Request').first().json.run_id,project_id:$json.project_id??$('Build Scheduler Request').first().json.project_id,profile_version:$json.profile_version??$('Build Scheduler Request').first().json.profile_version,idea_text:$('Build Scheduler Request').first().json.idea_text,profile:$('Build Scheduler Request').first().json.profile,requested_research:$('Build Scheduler Request').first().json.requested_research,correlation_id:$json.correlation_id??$('Build Scheduler Request').first().json.correlation_id,controller_cycle:Number(cycle),rpc_body:{p_run_id:$json.run_id??$('Build Scheduler Request').first().json.run_id}}}];""",
        ),
        http_supabase_rpc("Load Durable Orchestration Snapshot", "get_orchestration_run_snapshot", 1580, -300),
        code(
            "Bind Snapshot for Re-evaluation",
            1800,
            -300,
            r"""const base=$('Prepare Durable Snapshot Request').first().json;const snapshot=$input.first()?.json??{};const snapshotOk=snapshot.schema_version==='bp-orchestration-run-snapshot-v1'&&snapshot.run?.id===base.run_id;return [{json:{...base,snapshot:snapshotOk?snapshot:{run:{id:base.run_id},tasks:[],pending_checkpoints:[]},snapshot_ok:snapshotOk,transition_count:Number(base.controller_cycle??0),test_mode:false}}];""",
        ),
        execute_workflow("Re-evaluate Durable State", "bpSupervisorReeval01", 2020, -300),
        code(
            "Attach Bounded Controller Context",
            2240,
            -300,
            r"""const base=$('Bind Snapshot for Re-evaluation').first().json;const decision=$input.first()?.json??{};const cycle=Number(base.controller_cycle??0)+1;const snapshotOk=base.snapshot_ok===true;let route=snapshotOk?(decision.route??'HUMAN_REVIEW'):'HUMAN_REVIEW';let status=snapshotOk?(decision.status??'HUMAN_REVIEW'):'HUMAN_REVIEW';let requiresHuman=!snapshotOk||decision.requires_human===true;let message=snapshotOk?(decision.reason??decision.message??'Supervisor re-evaluated durable state.'):'The durable snapshot could not be loaded; orchestration stopped safely.';if(route==='TASK_SCHEDULER'&&cycle>=12){route='HUMAN_REVIEW';status='HUMAN_REVIEW';requiresHuman=true;message='The bounded controller reached 12 scheduling cycles and stopped for review.';}return [{json:{...base,decision:{...decision,route,status,requires_human:requiresHuman,reason:message},controller_cycle:cycle,continue_loop:route==='TASK_SCHEDULER'&&cycle<12,controller_status:status,controller_route:route,requires_human:requiresHuman,terminal:decision.terminal===true,message}}];""",
        ),
        if_true("Another Eligible Task?", 2460, -300, "={{ $json.continue_loop }}"),
        code(
            "Return Visible Dynamic Supervisor Outcome",
            2680,
            -160,
            r"""const x=$json;return [{json:{schema_version:'bp-canonical-supervisor-result-v1',status:x.controller_status??'HUMAN_REVIEW',route:x.controller_route??'HUMAN_REVIEW',requires_human:x.requires_human===true,terminal:x.terminal===true,message:x.message??x.safe_message??'The supervisor stopped safely.',project_id:x.project_id??null,run_id:x.run_id??null,profile_version:Number(x.profile_version??0)||null,controller_cycles:Number(x.controller_cycle??0),correlation_id:x.correlation_id??null,panel_item:x.decision?.panel_item??{item_type:'HUMAN_REVIEW',severity:'HIGH',blocking:true,title:'Review required',message:x.message??x.safe_message??'The supervisor stopped safely.',allowed_decisions:[],next_route:x.controller_route??'HUMAN_REVIEW'},test_mode:false}}];""",
        ),
        code(
            "Return Invalid Canonical Start",
            -840,
            140,
            r"""const x=$json;return [{json:{schema_version:'bp-canonical-supervisor-result-v1',status:'SAFE_FAILED',route:'SAFE_FAIL',requires_human:true,terminal:true,message:x.safe_message,project_id:x.project_id??null,run_id:x.run_id??null,profile_version:Number(x.profile_version??0)||null,controller_cycles:0,correlation_id:x.correlation_id??null,panel_item:{item_type:'HUMAN_REVIEW',severity:'HIGH',blocking:true,title:'Start stopped safely',message:x.safe_message,allowed_decisions:['RETRY','CANCEL'],next_route:'HUMAN_REVIEW'},test_mode:false}}];""",
        ),
    ]

    connections: dict = {}
    connect(connections, "When Called by Authenticated Start", "Normalize Canonical Supervisor Command")
    connect(connections, "Normalize Canonical Supervisor Command", "Canonical Command Valid?")
    connect(connections, "Canonical Command Valid?", "Prepare Dynamic Run State", 0)
    connect(connections, "Canonical Command Valid?", "Return Invalid Canonical Start", 1)
    connect(connections, "Prepare Dynamic Run State", "Prepare or Resume Dynamic Run")
    connect(connections, "Prepare or Resume Dynamic Run", "Bind Prepared Run State")
    connect(connections, "Bind Prepared Run State", "Run Can Continue?")
    connect(connections, "Run Can Continue?", "Dynamic Plan Needed?", 0)
    connect(connections, "Run Can Continue?", "Return Visible Dynamic Supervisor Outcome", 1)
    connect(connections, "Dynamic Plan Needed?", "Execute Dynamic Task Planner", 0)
    connect(connections, "Dynamic Plan Needed?", "Use Existing Durable Plan", 1)
    connect(connections, "Execute Dynamic Task Planner", "Bind Planner Decision")
    connect(connections, "Use Existing Durable Plan", "Bind Planner Decision")
    connect(connections, "Bind Planner Decision", "Plan Schedulable?")
    connect(connections, "Plan Schedulable?", "Build Scheduler Request", 0)
    connect(connections, "Plan Schedulable?", "Return Visible Dynamic Supervisor Outcome", 1)
    connect(connections, "Build Scheduler Request", "Execute One Eligible Task")
    connect(connections, "Execute One Eligible Task", "Prepare Durable Snapshot Request")
    connect(connections, "Prepare Durable Snapshot Request", "Load Durable Orchestration Snapshot")
    connect(connections, "Load Durable Orchestration Snapshot", "Bind Snapshot for Re-evaluation")
    connect(connections, "Bind Snapshot for Re-evaluation", "Re-evaluate Durable State")
    connect(connections, "Re-evaluate Durable State", "Attach Bounded Controller Context")
    connect(connections, "Attach Bounded Controller Context", "Another Eligible Task?")
    connect(connections, "Another Eligible Task?", "Build Scheduler Request", 0)
    connect(connections, "Another Eligible Task?", "Return Visible Dynamic Supervisor Outcome", 1)
    return workflow("bp00Supervisor", "BP-00 Dynamic Evidence Supervisor", nodes, connections, timeout=900)


def build_rerun_api() -> dict:
    verify_user = node(
        "Verify Rerun Supabase User",
        "n8n-nodes-base.httpRequest",
        -620,
        -100,
        {
            "url": "https://gudsbrmphrokpnzmrlqd.supabase.co/auth/v1/user",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Authorization", "value": "={{ $json.authorization }}"}]},
            "options": {"timeout": 15000},
        },
        4.5,
    )
    verify_user["credentials"] = {"httpHeaderAuth": {"id": "fguxqwSfKfj2xfo9", "name": "BP Supabase Public"}}
    verify_user["onError"] = "continueRegularOutput"

    nodes = [
        webhook("POST Blueprint Research Rerun", "blueprint/rerun", -1280, 0),
        code(
            "Validate Rerun Request",
            -1060,
            0,
            r"""const raw=$input.first()?.json??{};let b=raw.body??raw;if(typeof b==='string'){try{b=JSON.parse(b)}catch{b={}}}const headers=Object.fromEntries(Object.entries(raw.headers??{}).map(([k,v])=>[String(k).toLowerCase(),v]));const authorization=String(headers.authorization??'').trim();const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const command=String(b.command??'').toUpperCase();const target=String(b.target_module??'').toLowerCase();const modules=['customer_demand','competitor_intelligence','market_economics'];const errors=[];if(!/^Bearer\s+\S+$/i.test(authorization))errors.push('AUTHORIZATION_REQUIRED');if(!['PREVIEW','APPROVE','CANCEL'].includes(command))errors.push('COMMAND_INVALID');if(command==='PREVIEW'&&(!uuid.test(String(b.project_id??''))||!uuid.test(String(b.source_run_id??''))||!modules.includes(target)))errors.push('PREVIEW_SCOPE_INVALID');if(command!=='PREVIEW'&&(!uuid.test(String(b.rerun_request_id??''))||!Number.isInteger(Number(b.expected_source_state_version))))errors.push('RESOLUTION_SCOPE_INVALID');const statusCode=errors.includes('AUTHORIZATION_REQUIRED')?401:400;return [{json:{valid:errors.length===0,errors,status_code:statusCode,authorization,command,project_id:b.project_id??null,source_run_id:b.source_run_id??null,target_module:target,rerun_request_id:b.rerun_request_id??null,expected_source_state_version:Number(b.expected_source_state_version??0),idempotency_key:String(b.idempotency_key??`rerun-${Date.now()}`).slice(0,200),correlation_id:String(b.correlation_id??`bp-rerun-${Date.now()}`).slice(0,200)}}];""",
        ),
        if_true("Rerun Request Valid?", -840, 0, "={{ $json.valid }}"),
        verify_user,
        if_true("Rerun User Authenticated?", -400, -100, "={{ /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test($json.id ?? '') }}"),
        if_true("Preview Requested?", -180, -180, "={{ $('Validate Rerun Request').item.json.command === 'PREVIEW' }}"),
        code(
            "Prepare Research Rerun Preview",
            40,
            -280,
            r"""const x=$('Validate Rerun Request').first().json;return [{json:{...x,rpc_body:{p_project_id:x.project_id,p_source_run_id:x.source_run_id,p_target_module:x.target_module,p_idempotency_key:x.idempotency_key}}}];""",
        ),
        http_supabase_rpc("Create Durable Rerun Preview", "preview_research_rerun", 260, -280),
        code(
            "Build Rerun Preview Response",
            480,
            -280,
            r"""const p=$json??{};const req=$('Prepare Research Rerun Preview').first().json;const rr=p.rerun_request??{};const cp=p.checkpoint??{};const ok=Boolean(rr.id&&cp.id);return [{json:{status_code:ok?200:500,response:ok?{ok:true,status:'NEEDS_CONFIRMATION',command:'PREVIEW',rerun_request_id:rr.id,checkpoint_id:cp.id,target_module:req.target_module,expected_source_state_version:Number(rr.impact?.source_state_version??cp.state_version??0),impact:rr.impact,available_decisions:cp.available_decisions??['APPROVE','CANCEL'],correlation_id:req.correlation_id}:{ok:false,error_code:'RERUN_PREVIEW_FAILED',message:'Blueprint could not create a durable rerun preview. Nothing was rerun.',correlation_id:req.correlation_id}}}];""",
        ),
        respond("Respond Rerun Preview", 700, -280, "={{ JSON.stringify($json.response) }}"),
        code(
            "Prepare Rerun Resolution",
            40,
            -80,
            r"""const x=$('Validate Rerun Request').first().json;return [{json:{...x,rpc_body:{p_rerun_request_id:x.rerun_request_id,p_decision:x.command,p_expected_source_state_version:x.expected_source_state_version}}}];""",
        ),
        http_supabase_rpc("Resolve Approved Research Rerun", "resolve_profile_rerun", 260, -80),
        code(
            "Classify Rerun Resolution",
            480,
            -80,
            r"""const req=$('Prepare Rerun Resolution').first().json;const p=$json??{};const approved=p.decision==='APPROVE'&&p.target_run?.id&&p.rerun_request?.target_profile_version;const cancelled=p.decision==='CANCEL';const requested=Array.isArray(p.profile?.requested_research)?p.profile.requested_research:[];return [{json:{...req,resolution:p,approved:Boolean(approved),cancelled,dispatch_required:Boolean(approved),project_id:p.target_run?.project_id??p.rerun_request?.project_id??null,run_id:p.target_run?.id??null,profile_version:Number(p.rerun_request?.target_profile_version??0),profile:p.profile??{},requested_research:requested,response:approved?{ok:true,status:'QUEUED',command:'APPROVE',project_id:p.target_run.project_id,run_id:p.target_run.id,profile_version:Number(p.rerun_request.target_profile_version),message:'The approved research rerun was queued through the dynamic Supervisor.',poll_after_ms:2000,correlation_id:req.correlation_id}:cancelled?{ok:true,status:'CANCELLED',command:'CANCEL',message:'The rerun was cancelled; no new research run was created.',correlation_id:req.correlation_id}:{ok:false,status:'SAFE_FAILED',error_code:'RERUN_RESOLUTION_FAILED',message:'The rerun decision could not be resolved safely.',correlation_id:req.correlation_id}}}];""",
        ),
        if_true("Approved Rerun Needs Dispatch?", 700, -80, "={{ $json.dispatch_required }}"),
        code(
            "Prepare Approved Rerun Dispatch",
            920,
            -160,
            r"""const x=$json;return [{json:{command:'START',authorization:x.authorization,project_id:x.project_id,run_id:x.run_id,profile_version:x.profile_version,idea_text:String(x.profile.idea_text??''),optional_industry:x.profile.optional_industry??null,geography:x.profile.geography??null,requested_research:x.requested_research,planning_mode:'DISCOVER',founder_inputs:x.profile.constraints??{},profile:x.profile,controller_cycle:0,correlation_id:x.correlation_id,test_mode:false}}];""",
        ),
        execute_workflow("Dispatch Approved Rerun to BP-00", "bp00Supervisor", 1140, -160),
        respond("Respond Rerun Resolution", 920, 20, "={{ JSON.stringify($json.response) }}"),
        respond(
            "Respond Invalid Rerun Request",
            -620,
            140,
            "={{ JSON.stringify({ok:false,error_code:$json.status_code===401?'UNAUTHENTICATED':'INVALID_RERUN_REQUEST',message:$json.status_code===401?'Please sign in before requesting a rerun.':'Check the rerun scope and try again.',correlation_id:$json.correlation_id}) }}",
        ),
        respond(
            "Respond Invalid Rerun Session",
            -180,
            60,
            "={{ JSON.stringify({ok:false,error_code:'UNAUTHENTICATED',message:'Your session is invalid or expired. Please sign in again.',correlation_id:$('Validate Rerun Request').item.json.correlation_id}) }}",
            "={{ 401 }}",
        ),
    ]
    connections: dict = {}
    connect(connections, "POST Blueprint Research Rerun", "Validate Rerun Request")
    connect(connections, "Validate Rerun Request", "Rerun Request Valid?")
    connect(connections, "Rerun Request Valid?", "Verify Rerun Supabase User", 0)
    connect(connections, "Rerun Request Valid?", "Respond Invalid Rerun Request", 1)
    connect(connections, "Verify Rerun Supabase User", "Rerun User Authenticated?")
    connect(connections, "Rerun User Authenticated?", "Preview Requested?", 0)
    connect(connections, "Rerun User Authenticated?", "Respond Invalid Rerun Session", 1)
    connect(connections, "Preview Requested?", "Prepare Research Rerun Preview", 0)
    connect(connections, "Preview Requested?", "Prepare Rerun Resolution", 1)
    connect(connections, "Prepare Research Rerun Preview", "Create Durable Rerun Preview")
    connect(connections, "Create Durable Rerun Preview", "Build Rerun Preview Response")
    connect(connections, "Build Rerun Preview Response", "Respond Rerun Preview")
    connect(connections, "Prepare Rerun Resolution", "Resolve Approved Research Rerun")
    connect(connections, "Resolve Approved Research Rerun", "Classify Rerun Resolution")
    connect(connections, "Classify Rerun Resolution", "Approved Rerun Needs Dispatch?")
    connect(connections, "Approved Rerun Needs Dispatch?", "Prepare Approved Rerun Dispatch", 0)
    connect(connections, "Approved Rerun Needs Dispatch?", "Respond Rerun Resolution", 1)
    connect(connections, "Prepare Approved Rerun Dispatch", "Dispatch Approved Rerun to BP-00")
    connect(connections, "Prepare Approved Rerun Dispatch", "Respond Rerun Resolution")
    return workflow("bpApi02ResearchRerun", "BP-API-02 Research Rerun", nodes, connections, timeout=120)


def main() -> None:
    # Preserve the public API while dispatching the typed dynamic contract.
    update_code(
        "BP-API-01-start-run.json",
        "Classify Start Result",
        r"""const raw=$input.first()?.json??{};const correlationId=$('Prepare Authenticated Start').first().json.correlation_id;const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const allowed=['NEW','FRAMING','NEEDS_INPUT','PLANNING','RESEARCHING','AUDITING','WAITING_APPROVAL','SYNTHESIZING','COMPLETED','PARTIAL','HUMAN_REVIEW','SAFE_FAILED','CANCELLED'];const ok=uuid.test(raw.project_id??'')&&uuid.test(raw.run_id??'')&&allowed.includes(String(raw.status??''))&&Number(raw.profile_version)>0;if(ok){return [{json:{ok:true,status_code:202,response:{ok:true,correlation_id:correlationId,project_id:raw.project_id,run_id:raw.run_id,status:raw.status,state_version:Number(raw.state_version??0),profile_version:Number(raw.profile_version),original_blueprint_version:Number(raw.original_blueprint_version??1),duplicate:Boolean(raw.duplicate),created_at:raw.created_at,poll_after_ms:2000}}}];}const technical=String(raw.error?.message??raw.message??raw.code??'UNKNOWN').toUpperCase();const conflict=technical.includes('CONFLICT')||technical.includes('409');return [{json:{ok:false,status_code:conflict?409:500,response:{ok:false,error_code:conflict?'CONFLICT':'START_FAILED',message:conflict?'This request conflicts with an existing start operation.':'Blueprint could not initialize its durable founder profile and original blueprint safely.',correlation_id:correlationId}}}];""",
    )
    update_code(
        "BP-API-01-start-run.json",
        "Prepare Supervisor Start Dispatch",
        r"""const x=$input.first().json;const p=$('Prepare Authenticated Start').first().json;const r=p.rpc_body;const selected=r.p_original_request?.requested_research??r.p_constraints?.requested_research??[];if(!selected.length)throw new Error('REQUESTED_RESEARCH_MISSING');return [{json:{command:'START',authorization:p.authorization,owner_id:p.authenticated_user_id,project_id:x.response.project_id,run_id:x.response.run_id,profile_version:x.response.profile_version,correlation_id:p.correlation_id,idea_text:r.p_idea_text,optional_industry:r.p_optional_industry,geography:r.p_geography,requested_research:selected,planning_mode:'DISCOVER',founder_inputs:r.p_constraints??{},profile:{idea_text:r.p_idea_text,optional_industry:r.p_optional_industry,geography:r.p_geography,constraints:r.p_constraints??{},requested_research:selected,goal:r.p_constraints?.goal??null},state:{transition_count:0,search_cycle_count:0,tool_call_count:0,revision_count:0},controller_cycle:0,test_mode:false}}];""",
    )

    # Carry controller state through the scheduler subworkflow.
    update_code(
        "BP-SCHED-01-eligible-task-scheduler.json",
        "Normalize Scheduler Request",
        r"""const src=$input.first()?.json??{};const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;const allowed=['foundation','customer_demand','competitor_intelligence','market_economics','evidence_audit','research_verdict','final_blueprint'];const authorization=String(src.authorization??'');const runId=src.run_id??null;const testMode=src.test_mode===true;const canClaim=!testMode&&uuid.test(String(runId??''))&&/^Bearer\s+\S+$/i.test(authorization);return [{json:{schema_version:'bp-scheduler-request-v1',authorization,owner_id:src.owner_id??null,project_id:src.project_id??null,run_id:runId,profile_version:Number(src.profile_version??0),idea_text:String(src.idea_text??src.profile?.idea_text??''),profile:src.profile??{},requested_research:Array.isArray(src.requested_research)?src.requested_research:[],provided_tasks:Array.isArray(src.tasks)?src.tasks:[],allowed_modules:allowed,claim_limit:Math.max(1,Math.min(3,Math.trunc(Number(src.claim_limit??3)))),controller_cycle:Math.max(0,Math.trunc(Number(src.controller_cycle??0))),can_claim:canClaim,test_mode:testMode,correlation_id:String(src.correlation_id??`bp-scheduler-${Date.now()}`).slice(0,200)}}];""",
    )
    update_code(
        "BP-SCHED-01-eligible-task-scheduler.json",
        "Return Persisted Scheduler Cycle",
        r"""const prep=$('Prepare Typed Task Observation').item.json;const req=$('Normalize Scheduler Request').first().json;const p=$json??{};const ok=p.recorded===true;return {json:{schema_version:'bp-scheduler-cycle-result-v1',status:ok?'OBSERVED':'HUMAN_REVIEW',route:ok?'SUPERVISOR_REEVALUATE':'HUMAN_REVIEW',requires_human:!ok,terminal:false,worker:prep.worker,observation_persistence:ok?p:{recorded:false,reason:'OBSERVATION_PERSISTENCE_FAILED',provider_response:p},authorization:req.authorization,owner_id:req.owner_id,project_id:req.project_id,run_id:req.run_id,profile_version:req.profile_version,requested_research:req.requested_research,controller_cycle:req.controller_cycle,correlation_id:prep.worker.correlation_id,test_mode:false}};""",
    )
    update_code(
        "BP-SCHED-01-eligible-task-scheduler.json",
        "Return Safe Scheduler Cycle",
        r"""const x=$json;const req=$('Normalize Scheduler Request').first().json;return {json:{schema_version:'bp-scheduler-cycle-result-v1',status:'OBSERVED',route:'SUPERVISOR_REEVALUATE',requires_human:false,terminal:false,worker:x.worker,observation_persistence:{recorded:false,reason:'TEST_MODE'},authorization:req.authorization,owner_id:req.owner_id,project_id:req.project_id,run_id:req.run_id,profile_version:req.profile_version,requested_research:req.requested_research,controller_cycle:req.controller_cycle,correlation_id:x.worker.correlation_id,test_mode:true}};""",
    )

    # The Research Blueprint must be synthesized before the Stage 1 checkpoint blocks later stages.
    update_code(
        "BP-SUPERVISOR-REEVAL-01.json",
        "Choose Next Route from Durable State",
        r"""const src=$json??{};const s=src.snapshot??src;const tasks=Array.isArray(s.tasks)?s.tasks:[];const checkpoints=Array.isArray(s.pending_checkpoints)?s.pending_checkpoints:[];const n=Math.max(0,Math.trunc(Number(src.transition_count??0)));const finalReady=tasks.some(t=>(t.module_key==='final_blueprint'||t.task_key==='s1_research_blueprint')&&t.status==='READY');let status='WAITING',route='WAIT_FOR_ELIGIBLE_TASK',requiresHuman=false,reason='No eligible task is ready yet.',allowed=[];if(n>=20){status='HUMAN_REVIEW';route='HUMAN_REVIEW';requiresHuman=true;reason='The bounded supervisor reached its transition limit.';allowed=['RETRY','PAUSE_OR_REVISE','CANCEL'];}else if(finalReady){status='DISPATCH';route='TASK_SCHEDULER';reason='The Research Blueprint must be synthesized before the stage gate pauses later work.';}else if(checkpoints.length){status='HUMAN_REVIEW';route='HITL_RESUME';requiresHuman=true;reason='A durable founder checkpoint must be resolved before the graph can continue.';allowed=checkpoints[0].available_decisions??[];}else if(tasks.some(t=>t.status==='NEEDS_INPUT')){status='NEEDS_INPUT';route='FOUNDER_INPUT';requiresHuman=true;reason='The workflow needs specific founder input.';allowed=['MORE_INFORMATION','CANCEL'];}else if(tasks.some(t=>t.status==='HUMAN_REVIEW'||t.status==='SAFE_FAILED')){status='HUMAN_REVIEW';route='HUMAN_REVIEW';requiresHuman=true;reason=tasks.some(t=>t.observation_verdict==='CONTRADICTORY')?'Contradictory evidence needs a founder decision.':'A task exhausted its safe autonomous path.';allowed=tasks.some(t=>t.observation_verdict==='CONTRADICTORY')?['MORE_INFORMATION','OVERRIDE','PAUSE_OR_REVISE']:['RETRY','REQUEST_CHANGES','CANCEL'];}else if(tasks.some(t=>t.status==='READY')){status='DISPATCH';route='TASK_SCHEDULER';reason='At least one dependency-satisfied task is ready.';}else if(tasks.some(t=>t.status==='RUNNING')){status='WAITING';route='WAIT_FOR_OBSERVATION';reason='A claimed task is still running.';}else if(tasks.length&&tasks.every(t=>['COMPLETED','REUSED','NOT_APPLICABLE'].includes(t.status))&&tasks.some(t=>t.module_key==='final_blueprint'||t.task_key==='s1_research_blueprint')){status=checkpoints.length?'HUMAN_REVIEW':'STAGE_COMPLETE';route=checkpoints.length?'HITL_RESUME':'COMPLETE';requiresHuman=checkpoints.length>0;reason=checkpoints.length?'The Research Blueprint is ready; the founder must now choose whether to continue, validate, revise, or pause.':'The immutable Research Blueprint is complete.';allowed=checkpoints[0]?.available_decisions??[];}else if(tasks.some(t=>t.status==='PARTIAL')){status='PARTIAL_COMPLETE';route='HUMAN_REVIEW';requiresHuman=true;reason='A partial result is preserved; the founder can retry or continue with limitations.';allowed=['RETRY','CONTINUE_ANYWAY','PAUSE_OR_REVISE'];}const panel={item_type:requiresHuman?(route==='FOUNDER_INPUT'?'NEEDS_INPUT':'HUMAN_REVIEW'):'SUPERVISOR_STATUS',severity:requiresHuman?'HIGH':'INFO',blocking:requiresHuman,title:{FOUNDER_INPUT:'Founder input required',HITL_RESUME:'Your verdict decision is required',HUMAN_REVIEW:'Review required',TASK_SCHEDULER:'Research can continue',COMPLETE:'Stage 1 complete'}[route]??'Waiting safely',message:reason,allowed_decisions:allowed,next_route:route};return {json:{schema_version:'bp-supervisor-decision-v1',scenario:src.scenario??null,status,route,requires_human:requiresHuman,reason,allowed_decisions:allowed,transition_count:n+1,terminal:route==='COMPLETE',panel_item:panel,correlation_id:src.correlation_id??null,test_mode:src.test_mode===true}};""",
    )

    for node_name, js_code in CHAT_NODE_CODE.items():
        update_code("BP-CHAT-01-research-copilot.json", node_name, js_code)

    (N8N / "BP-00-adaptive-supervisor.json").write_text(
        json.dumps(build_controller(), indent=2) + "\n", encoding="utf-8"
    )
    (N8N / "BP-API-02-research-rerun.json").write_text(
        json.dumps(build_rerun_api(), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
