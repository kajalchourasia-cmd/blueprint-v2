import html

import streamlit as st
import streamlit.components.v1 as components

from blueprint.auth import render_auth_gate
from blueprint.backend import BackendError, load_recent_blueprints, make_idempotency_key, start_blueprint
from blueprint.schemas import UserProfile
from blueprint.state import reset


st.set_page_config(page_title="Blueprint", page_icon="⌖", layout="wide", initial_sidebar_state="collapsed")
if not render_auth_gate():
    st.stop()
reset()

query_idea = st.query_params.get("idea", "").strip()
if query_idea and st.query_params.get("start") == "1":
    st.session_state.pop("backend_idempotency_key", None)
    st.session_state.pop("generation_error", None)
    st.session_state["idea"] = query_idea
    st.session_state["dialog_answers"] = {"idea": query_idea}
    st.session_state["dialog_question"] = 0
    st.session_state["show_questions"] = True
    st.session_state["generating_blueprint"] = False
    st.query_params.clear()

edit_step = st.query_params.get("edit_step")
if edit_step is not None:
    try:
        st.session_state["dialog_question"] = min(7, max(0, int(edit_step)))
    except (TypeError, ValueError):
        st.session_state["dialog_question"] = 0
    st.session_state.setdefault("dialog_answers", {"idea": st.session_state.get("idea", "")})
    st.session_state["show_questions"] = True
    st.session_state["generating_blueprint"] = False
    st.query_params.clear()


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL@20,400,0&display=swap');
:root{--paper:#efefed;--paper-2:#f8f8f6;--ink:#181a19;--muted:#717571;--line:#d2d4d1;--green:#267c4b;--green-soft:#dceadf;--blue:#c9dff1;--violet:#d9cef4;--peach:#f0d0b1}
[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:radial-gradient(circle at 84% 8%,#fff 0,transparent 30%),linear-gradient(145deg,#f7f7f4 0,#e7e8e5 65%,#dedfdd 100%)}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stSidebarNav"],#MainMenu,footer{display:none!important}
main .block-container{max-width:1500px;padding:0 4vw 90px}
.landing-intro{padding:31px 0 30px;color:var(--ink);border-bottom:1px solid transparent}
.landing-brand{font:500 12px 'DM Mono',monospace;letter-spacing:.13em;text-transform:uppercase;display:flex;align-items:center;gap:10px}.landing-brand:before{content:'';width:9px;height:9px;border-radius:50%;background:#232624;box-shadow:0 0 0 5px rgba(35,38,36,.07)}
.landing-intro h1{max-width:1250px;margin:30px 0 14px;font:500 clamp(46px,5.6vw,82px)/.91 'Space Grotesk',sans-serif;letter-spacing:-.078em}.landing-intro h1 em{display:block;font-style:normal;color:#68706b}
.landing-intro p{max-width:680px;margin:0;color:#626762;font:16px/1.5 'Space Grotesk',sans-serif}
.hero-grid-label{margin:22px 0 10px;color:#7a7f7b;font:10px 'DM Mono',monospace;letter-spacing:.1em;text-transform:uppercase}
.st-key-hero_idea_entry{height:300px;padding:23px 24px 20px;border:1px solid #d2d5d1;border-radius:30px;background:rgba(255,255,255,.86);box-shadow:0 24px 60px rgba(33,38,34,.11),inset 0 1px 0 #fff;display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden}.st-key-hero_idea_entry:before{content:'';position:absolute;right:-55px;top:-70px;width:220px;height:220px;border-radius:50%;background:radial-gradient(circle,rgba(69,139,92,.13),transparent 68%);pointer-events:none}.st-key-hero_idea_entry>*{position:relative;z-index:1}
.hero-note-kicker{color:#747b76;font:8px 'DM Mono',monospace;letter-spacing:.11em}.hero-note-title{margin-top:12px;color:#202421;font:500 24px/1.05 'Space Grotesk',sans-serif;letter-spacing:-.05em}.hero-note-copy{margin-top:6px;color:#777e78;font:11px/1.4 'Space Grotesk',sans-serif}.composer-mode{position:absolute;right:0;top:0;color:#6f7771;font:7px 'DM Mono';letter-spacing:.08em}
.st-key-hero_idea_entry [data-testid="stForm"]{margin-top:auto;border:0!important;padding:0!important}
.st-key-hero_idea_entry [data-testid="stTextArea"]{margin:16px 0 9px;background:transparent!important}.st-key-hero_idea_entry [data-testid="stTextAreaRootElement"],.st-key-hero_idea_entry [data-baseweb="textarea"],.st-key-hero_idea_entry [data-baseweb="textarea"]>div{border:0!important;background:transparent!important;box-shadow:none!important}.st-key-hero_idea_entry [data-testid="stTextArea"] textarea{height:92px!important;min-height:92px!important;padding:13px 15px!important;border:1px solid #edb99d!important;border-radius:16px!important;background:#fff!important;color:#202421!important;box-shadow:none!important;font:14px/1.45 'Space Grotesk',sans-serif!important;resize:none}.st-key-hero_idea_entry [data-testid="stTextArea"] textarea::placeholder{color:#9a9f9b!important}.st-key-hero_idea_entry [data-testid="stTextArea"] textarea:focus{border-color:#df946d!important;box-shadow:none!important;outline:none!important}.st-key-hero_idea_entry [data-testid="InputInstructions"],.st-key-hero_idea_entry [data-testid="stInputInstructions"]{display:none!important}
.st-key-hero_idea_entry [data-testid="stFormSubmitButton"]{display:flex!important;justify-content:flex-start!important}.st-key-hero_idea_entry [data-testid="stFormSubmitButton"] button{flex:0 0 182px!important;width:182px!important;min-width:182px!important;max-width:182px!important;height:40px!important;border:0!important;border-radius:13px!important;background:#d76524!important;color:#fff!important;font:500 8px 'DM Mono',monospace!important;letter-spacing:.055em!important;white-space:nowrap!important;box-shadow:0 9px 20px rgba(139,69,33,.18)!important}.st-key-hero_idea_entry [data-testid="stFormSubmitButton"] button:hover{background:#7b3f24!important;transform:translateY(-1px)}
.bp-section{max-width:1200px;margin:0 auto;padding:90px 0;color:var(--ink)}.bp-rule{border-top:1px solid #b9bcb9;padding-top:13px;color:#747975;font:10px 'DM Mono',monospace;letter-spacing:.09em;text-transform:uppercase}.bp-section h2{max-width:820px;margin:18px 0 38px;font:500 clamp(38px,5.4vw,72px)/.94 'Space Grotesk',sans-serif;letter-spacing:-.07em}.bp-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.bp-card{position:relative;min-height:330px;padding:0 0 22px;border:0;border-top:1px solid #c3c7c3;border-radius:0;background:transparent;display:flex;flex-direction:column;transition:.25s}.bp-card:hover{transform:translateY(-5px)}.bp-card-visual{position:relative;height:180px;margin:18px 0 24px;border-radius:7px;background:#e7e9e4;display:grid;place-items:center;overflow:hidden;transition:.25s}.bp-card-visual:before,.bp-card-visual:after{content:'';position:absolute;transition:.35s}.bp-card-visual:before{width:94px;height:94px;border:1px solid #aeb6ae;border-radius:50%}.bp-card-visual:after{width:140px;border-top:1px solid #2f8051;transform:rotate(-12deg)}.bp-card:hover .bp-card-visual:before{transform:scale(1.12)}.bp-card:hover .bp-card-visual:after{transform:rotate(12deg)}.bp-symbol{position:relative;z-index:2;width:54px;height:54px;display:grid;place-items:center;border-radius:50%;background:#173526;color:#d6f077;font:500 22px 'Space Grotesk';box-shadow:0 12px 28px rgba(24,58,39,.18)}.bp-card:nth-child(2) .bp-card-visual{background:#e4ebef}.bp-card:nth-child(2) .bp-symbol{background:#345f78;color:#e7f5fc}.bp-card:nth-child(3) .bp-card-visual{background:#eee3dc}.bp-card:nth-child(3) .bp-symbol{background:#774c3a;color:#ffe6d8}.bp-card strong{font:500 24px 'Space Grotesk',sans-serif;letter-spacing:-.05em}.bp-card>span{max-width:330px;margin-top:8px;color:#6f746f;font:14px/1.45 'Space Grotesk',sans-serif}.bp-card-index{position:absolute;left:0;top:-22px;color:#7a817b;font:8px 'DM Mono';letter-spacing:.08em}.bp-section.tint{position:relative;max-width:1200px;margin:0 auto;padding:90px 0;border:0;border-radius:0;background:transparent;overflow:visible}.bp-section.tint.method{background:transparent;color:var(--ink)}.bp-section.tint.method .bp-rule{border-color:#b9bcb9;color:#747975}.bp-section.tint:after{display:none}.bp-section.tint.method .bp-card{border-top-color:#34453a}.bp-section.tint.method .bp-card-visual{background:#14281c}.bp-section.tint.method .bp-card-visual:before{border-color:#45614e;box-shadow:inset 0 0 0 22px rgba(217,239,174,.025)}.bp-section.tint.method .bp-card-visual:after{border-color:#b8e15c}.bp-section.tint.method .bp-symbol{background:#d9efae;color:#183b29}.bp-section.tint.method .bp-card:nth-child(2) .bp-symbol{background:#bcdff1;color:#234f66}.bp-section.tint.method .bp-card:nth-child(3) .bp-symbol{background:#f2c5ae;color:#693923}.bp-section.tint.method .bp-card>span{color:#667168}.bp-start{padding:40px;border-radius:30px;background:linear-gradient(130deg,#172d21,#245f3d);color:#f5f6f3;display:flex;align-items:end;justify-content:space-between;gap:25px;box-shadow:0 24px 60px rgba(25,68,43,.16)}.bp-start h2{font-size:52px}.bp-try{display:inline-block;padding:13px 17px;border-radius:17px;background:#fff;color:#202321;text-decoration:none;font:500 10px 'DM Mono',monospace;white-space:nowrap;transition:.22s}.bp-try:hover{background:#d9efae;transform:translateY(-2px)}
.wizard-intro{margin:-8px 0 4px;color:#757c76;font:10px/1.45 'Space Grotesk',sans-serif}.wizard-kicker{color:#1c201d;font:500 17px 'Space Grotesk',sans-serif;letter-spacing:-.025em}.wizard-number{display:block;margin-bottom:6px;color:#7f8680;font:8px 'DM Mono',monospace;letter-spacing:.1em}.wizard-required{margin:6px 0 0;color:#858b86;font:9px 'DM Mono',monospace}.wizard-dots{display:grid;grid-template-columns:repeat(8,1fr);gap:6px;margin:17px 0 22px}.wizard-dots span{height:4px;border-radius:4px;background:#e0e2df}.wizard-dots span.active,.wizard-dots span.done{background:#2f8051}.st-key-wizard_question_head{margin-top:12px}
div[data-baseweb="modal"],[data-testid="stDialog"]{background:rgba(235,237,234,.94)!important;backdrop-filter:blur(38px)!important;-webkit-backdrop-filter:blur(38px)!important}[data-testid="stDialog"]>div{max-width:560px!important;border-radius:28px!important;background:#f7f7f5!important;box-shadow:0 30px 90px rgba(17,20,18,.42)!important}[data-testid="stDialog"] [data-testid="stVerticalBlock"]{gap:8px!important}[data-testid="stDialog"] [data-testid="stTextArea"] textarea,[data-testid="stDialog"] [data-testid="stTextInput"] input,[data-testid="stDialog"] [data-baseweb="select"]>div{border-radius:13px!important;background:#fff!important;border-color:#d2d6d2!important}[data-testid="stDialog"] [data-testid="stTextArea"] textarea{min-height:68px!important;height:68px!important}[data-testid="stDialog"] [data-testid="stPills"] button{min-height:30px!important;padding:5px 10px!important;border-radius:15px!important;border:1px solid #d4d7d3!important;background:#fff!important;color:#555b57!important;font-size:10px!important}[data-testid="stDialog"] [data-testid="stPills"] button[aria-pressed="true"]{border-color:#397e57!important;background:#e2eee5!important;color:#205d3b!important}[data-testid="stDialog"] [data-testid="stRadio"] label{padding:6px 9px;border-radius:12px;background:#fff}[data-testid="stDialog"] [data-testid="stHorizontalBlock"]:last-child{margin-top:13px!important;padding-top:13px;border-top:1px solid #dedfdd}[data-testid="stDialog"] [data-testid="column"]:first-child button{border:0!important;border-radius:14px!important;background:#dceadf!important;color:#246641!important}[data-testid="stDialog"] [data-testid="column"]:first-child button:disabled{background:#eceeeb!important;color:#b3b6b2!important}[data-testid="stDialog"] [data-testid="column"]:nth-child(2) button{border:0!important;background:transparent!important;color:#777d78!important}[data-testid="stDialog"] [data-testid="column"]:last-child button{border:0!important;border-radius:14px!important;background:#202321!important;color:#fff!important}.st-key-wizard_question_head.st-key-wizard_question_head.st-key-wizard_question_head button{height:auto!important;min-height:0!important;padding:1px 0!important;border:0!important;border-radius:0!important;background:transparent!important;color:#69706a!important;text-decoration:underline!important;text-underline-offset:3px;font:8px 'DM Mono',monospace!important;box-shadow:none!important}
.landing-menu{position:fixed;z-index:900;right:24px;top:22px}.landing-menu summary{width:44px;height:44px;display:grid;place-items:center;border:1px solid #d0d3cf;border-radius:50%;background:rgba(255,255,255,.88);box-shadow:0 10px 28px rgba(27,31,28,.12);cursor:pointer;list-style:none}.landing-menu summary::-webkit-details-marker{display:none}.landing-menu summary span{font-family:'Material Symbols Rounded';font-size:20px}.landing-menu nav{position:absolute;right:0;top:53px;width:185px;padding:8px;border:1px solid #d0d3cf;border-radius:20px;background:rgba(255,255,255,.96);box-shadow:0 18px 50px rgba(27,31,28,.16)}.landing-menu a{height:38px;padding:0 10px;display:flex;align-items:center;gap:9px;border-radius:12px;color:#343835;text-decoration:none;font:10px 'Space Grotesk'}.landing-menu a:hover{background:#eef0ed}.landing-menu a span{font-family:'Material Symbols Rounded';font-size:16px;color:#747a75}
.generation{text-align:center;padding:30px 10px 22px}.generation-orbit{width:78px;height:78px;margin:0 auto 22px;position:relative;border:1px solid #c8ccc8;border-radius:50%;animation:spin 2.2s linear infinite}.generation-orbit:before,.generation-orbit:after{content:'';position:absolute;border-radius:50%}.generation-orbit:before{width:15px;height:15px;left:4px;top:13px;background:#2f8051;box-shadow:48px 30px 0 #c8dff0}.generation-orbit:after{width:7px;height:7px;left:34px;top:34px;background:#1d201e;box-shadow:0 0 0 10px rgba(47,128,81,.1)}.generation h3{margin:0;font:500 27px 'Space Grotesk',sans-serif;letter-spacing:-.05em}.generation p{color:#777d78;font-size:12px}.generation-lines{display:grid;gap:7px;margin-top:24px}.generation-lines i{height:4px;border-radius:4px;background:#e1e3e0;overflow:hidden}.generation-lines i:after{content:'';display:block;width:45%;height:100%;background:#2f8051;animation:scan 1.2s ease-in-out infinite}.generation-lines i:nth-child(2):after{animation-delay:.2s}.generation-lines i:nth-child(3):after{animation-delay:.4s}@keyframes spin{to{transform:rotate(360deg)}}@keyframes scan{0%{transform:translateX(-110%)}100%{transform:translateX(240%)}}
  [data-testid="stDialog"]:has(.generation) .wizard-intro,[data-testid="stDialog"]:has(.generation) .wizard-dots,[data-testid="stDialog"]:has(.generation) .st-key-wizard_question_head,[data-testid="stDialog"]:has(.generation) [data-testid="stTextArea"],[data-testid="stDialog"]:has(.generation) [data-testid="stTextInput"],[data-testid="stDialog"]:has(.generation) [data-testid="stSelectbox"],[data-testid="stDialog"]:has(.generation) [data-testid="stMultiSelect"],[data-testid="stDialog"]:has(.generation) [data-testid="stSlider"],[data-testid="stDialog"]:has(.generation) [data-testid="stHorizontalBlock"]{display:none!important}
  [data-testid="stDialog"]>div{height:min(680px,calc(100vh - 96px))!important;min-height:min(680px,calc(100vh - 96px))!important;max-height:min(680px,calc(100vh - 96px))!important;overflow:hidden!important}[data-testid="stDialog"]>div>div{height:100%!important;overflow-y:auto!important;scrollbar-gutter:stable}
@media(max-width:800px){main .block-container{padding:0 18px 70px}.landing-intro h1{margin-top:25px}.bp-cards{grid-template-columns:1fr}.bp-section,.bp-section.tint{padding:64px 0}.bp-card{min-height:0}.bp-start{display:block;padding:27px}.bp-start h2{font-size:40px}.bp-try{margin-top:20px}.st-key-hero_idea_entry{height:auto;min-height:320px}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '''<span id="landing-top"></span><details class="landing-menu"><summary aria-label="Open Blueprint navigation"><span style="font-family:Arial,sans-serif">⌘</span></summary><nav><a href="/"><span style="font-family:Arial,sans-serif">⌂</span>Home</a><a href="/Your_Plan"><span style="font-family:Arial,sans-serif">▦</span>Dashboard</a><a href="/Your_Plan?view=blueprint"><span style="font-family:Arial,sans-serif">⌘</span>Full Blueprint</a><a href="/Inputs"><span style="font-family:Arial,sans-serif">≋</span>User inputs</a><a href="/Data_Library"><span style="font-family:Arial,sans-serif">◫</span>Data library</a><a href="/Case_Study"><span style="font-family:Arial,sans-serif">¶</span>Case study</a></nav></details><section class="landing-intro"><div class="landing-brand">Blueprint</div><h1>Turn the unfinished idea into <em>your next provable move.</em></h1><p>Blueprint turns your context, constraints, and real-world evidence into a roadmap you can execute—without pretending uncertainty is validation.</p></section><span id="idea-field"></span><div class="hero-grid-label">01 / Start here</div>''',
    unsafe_allow_html=True,
)

motion = r"""
<!doctype html><html><head><style>
*{box-sizing:border-box}html,body{margin:0;background:transparent;color:#256d45;overflow:hidden}.shell{height:300px;position:relative;border:1px solid rgba(27,90,54,.28);border-radius:30px;background:linear-gradient(145deg,#e8f0e9,#d8e8dc);font-family:'Courier New',monospace;overflow:hidden;box-shadow:inset 0 1px 0 rgba(255,255,255,.8)}.labels{position:absolute;top:23px;left:7%;right:7%;height:23px;border-top:1px solid rgba(38,109,69,.6);display:flex;justify-content:space-between;align-items:flex-start;font-size:10px;text-transform:uppercase;letter-spacing:.08em}.labels span{margin-top:-7px;padding:0 9px;background:#e4eee6}.labels span:last-child{background:#dce9df}canvas{position:absolute;top:48px;left:0;width:100%;height:206px}.bottom{position:absolute;left:7%;right:7%;bottom:16px;border-top:1px solid rgba(38,109,69,.45);padding-top:8px;display:flex;justify-content:space-between;font-size:8px;letter-spacing:.08em}.bottom .pulse{font-size:13px;line-height:0;animation:pulse 1.8s infinite}@keyframes pulse{50%{opacity:.25}}
</style></head><body><div class="shell"><div class="labels"><span>uncertainty</span><span>evidence</span></div><canvas id="field"></canvas><div class="bottom"><span>UNFINISHED</span><span class="pulse">◉</span><span>NEXT PROOF</span></div></div><script>
const c=document.getElementById('field'),ctx=c.getContext('2d'),DPR=Math.min(devicePixelRatio||1,2);let W,H,t=0;
function size(){W=c.clientWidth;H=c.clientHeight;c.width=W*DPR;c.height=H*DPR;ctx.setTransform(DPR,0,0,DPR,0,0)}function rand(a,b){return a+Math.random()*(b-a)}
let dots=[],columns=[];const laneCount=30,cell=13;function route(x){let q=x/W,knots=[.55,.42,.69,.58,.73,.38,.5,.5],n=knots.length-1,z=Math.max(0,Math.min(.999,q))*n,i=Math.floor(z),f=z-i,s=f*f*(3-2*f);return H*(knots[i]*(1-s)+knots[i+1]*s)}
function seed(){dots=[];columns=[];for(let lane=0;lane<laneCount;lane++){let q=lane/laneCount,count=q<.16?5:q<.36?6:q<.58?4:q<.78?2:0;columns.push(count);for(let j=0;j<count+2;j++){let center=route(18+(W-36)*lane/(laneCount-1));dots.push({lane,y:rand(Math.max(14,center-count*cell),Math.min(H-14,center+count*cell)),min:Math.max(14,center-count*cell),max:Math.min(H-14,center+count*cell),r:rand(3,5.8),speed:rand(.2,.55),direction:Math.random()>.5?1:-1,kind:Math.random()>.88})}}}
function draw(){ctx.clearRect(0,0,W,H);ctx.strokeStyle='rgba(38,109,69,.26)';ctx.lineWidth=1;for(let i=0;i<laneCount;i++){let x=18+(W-36)*i/(laneCount-1);ctx.setLineDash([2,7]);ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()}ctx.setLineDash([]);for(let i=0;i<laneCount;i++){let x=18+(W-36)*i/(laneCount-1),y=route(x),count=columns[i];for(let j=-count;j<=count;j++){let a=Math.max(.035,.15-Math.abs(j)*.014);ctx.fillStyle='rgba(73,139,195,'+a+')';ctx.fillRect(x-8,y+j*cell,16,cell-1)}}dots.forEach(d=>{d.y+=d.speed*d.direction;if(d.y>d.max||d.y<d.min)d.direction*=-1;let x=18+(W-36)*d.lane/(laneCount-1);ctx.beginPath();ctx.arc(x,d.y,d.r,0,Math.PI*2);ctx.fillStyle=d.kind?'#267c4b':'#dbe8de';ctx.fill();ctx.strokeStyle='#267c4b';ctx.stroke()});let raw=(t*.000075)%1,progress=1-Math.pow(1-raw,2.55),currentLane=Math.floor(progress*(laneCount-1)),startLane=Math.max(0,currentLane-15);for(let lane=startLane;lane<=currentLane;lane++){let x=18+(W-36)*lane/(laneCount-1),y=route(x)+Math.sin(lane*2.8)*1.7;ctx.beginPath();ctx.arc(x,y,6.8,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#267c4b';ctx.stroke()}let x=18+(W-36)*progress,y=route(x)+Math.sin(currentLane*2.8)*1.7;ctx.beginPath();ctx.arc(x,y,8.5,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#267c4b';ctx.lineWidth=1.5;ctx.stroke();ctx.lineWidth=1;t+=16;requestAnimationFrame(draw)}size();seed();addEventListener('resize',()=>{size();seed()});draw();
</script></body></html>
"""

left, right = st.columns([1, 1], gap="large", vertical_alignment="top")
with left:
    components.html(motion, height=300, scrolling=False)
with right:
    with st.container(key="hero_idea_entry"):
        st.markdown('<div><div class="hero-note-kicker">START WITH THE UNFINISHED VERSION</div><div class="hero-note-title">What are you trying to make real?</div><div class="hero-note-copy">One rough sentence is enough. Blueprint will ask for the missing context.</div></div>', unsafe_allow_html=True)
        with st.form("hero_idea_form", border=False):
            hero_idea = st.text_area("Your idea", value="", placeholder="Describe your product or business idea…", height=112, label_visibility="collapsed")
            build_blueprint = st.form_submit_button("BUILD MY BLUEPRINT  →", type="primary", use_container_width=True)
        if build_blueprint:
            if hero_idea.strip():
                st.session_state.pop("backend_idempotency_key", None)
                st.session_state.pop("generation_error", None)
                st.session_state["idea"] = hero_idea.strip()
                st.session_state["dialog_answers"] = {"idea": hero_idea.strip()}
                st.session_state["dialog_question"] = 0
                st.session_state["show_questions"] = True
                st.session_state["generating_blueprint"] = False
                st.rerun()
            else:
                st.warning("Enter the idea you want to make real.")

st.markdown(
    """
<section class="bp-section tint"><div class="bp-rule">02 / The promise</div><h2>Do not build the whole thing. Find the next proof.</h2><div class="bp-cards"><div class="bp-card"><div class="bp-card-index">01</div><div class="bp-card-visual"><i class="bp-symbol">◎</i></div><strong>Reality before momentum</strong><span>See the assumptions your idea is quietly asking you to make.</span></div><div class="bp-card"><div class="bp-card-index">02</div><div class="bp-card-visual"><i class="bp-symbol">↗</i></div><strong>Evidence-producing work</strong><span>Turn the next unknown into something you can test outside the screen.</span></div><div class="bp-card"><div class="bp-card-index">03</div><div class="bp-card-visual"><i class="bp-symbol">$</i></div><strong>The cost of continuing</strong><span>Know what the next commitment takes from your money, time, and life.</span></div></div></section>
<section class="bp-section tint method"><div class="bp-rule">03 / The method</div><h2>Every next step should earn the one after it.</h2><div class="bp-cards"><div class="bp-card"><div class="bp-card-index">01</div><div class="bp-card-visual"><i class="bp-symbol">◇</i></div><strong>Name the bet</strong><span>State what must be true before you invest more.</span></div><div class="bp-card"><div class="bp-card-index">02</div><div class="bp-card-visual"><i class="bp-symbol">⌁</i></div><strong>Test in the world</strong><span>Capture behavior, commitments, and contradictions.</span></div><div class="bp-card"><div class="bp-card-index">03</div><div class="bp-card-visual"><i class="bp-symbol">✓</i></div><strong>Decide honestly</strong><span>Continue, change direction, or stop with the evidence in front of you.</span></div></div></section>
<section class="bp-section" id="start"><div class="bp-start"><div><div class="bp-rule" style="border-color:#557765;color:#bad0c0">04 / Begin</div><h2 style="margin-bottom:17px">Bring the unfinished version.</h2><p style="max-width:590px;margin:0;color:#c6d5ca;font:15px/1.5 'Space Grotesk',sans-serif">You do not need a pitch deck or polished answers. The field above is enough to begin.</p></div><a class="bp-try" href="#landing-top">GO TO THE IDEA FIELD ↑</a></div></section>
""",
    unsafe_allow_html=True,
)

if "owned_blueprints" not in st.session_state:
    try:
        st.session_state["owned_blueprints"] = load_recent_blueprints()
        st.session_state["owned_blueprints_error"] = None
    except BackendError as exc:
        st.session_state["owned_blueprints"] = []
        st.session_state["owned_blueprints_error"] = str(exc)

durable_projects = st.session_state.get("owned_blueprints") or []
if durable_projects:
    st.markdown("### Continue your evidence Blueprint")
    durable_labels = {
        f"{project.get('idea_text', 'Untitled')[:90]} · {(project.get('latest_run') or {}).get('status', 'No run').replace('_', ' ').title()}": project
        for project in durable_projects
    }
    selected_label = st.selectbox("Open a saved Blueprint", list(durable_labels), key="durable_blueprint_select", label_visibility="collapsed")
    if st.button("Open saved Blueprint →", key="open_durable_blueprint"):
        saved = durable_labels[selected_label]
        run = saved.get("latest_run") or {}
        if not run.get("id"):
            st.warning("This project has no research run yet. Start it again from the idea field.")
        else:
            stored = saved.get("constraints") or {}
            onboarding = stored.get("onboarding_answers") or {}
            st.session_state["profile"] = UserProfile(
                idea=str(saved.get("idea_text") or ""),
                location=str(saved.get("geography") or ""),
                target_customer=str(stored.get("target_customer") or ""),
                goal=str(stored.get("goal") or "just_explore"),
                success_definition=str(stored.get("success_definition") or ""),
                launch_timeline=str(stored.get("launch_timeline") or "Not sure"),
                current_work=str(stored.get("current_work") or ""),
                constraints=list(stored.get("constraints") or []),
                hours_per_week=int(stored.get("hours_per_week") or 5),
                money_available=int(stored.get("available_budget") or 0),
            )
            st.session_state["dialog_answers"] = onboarding
            st.session_state["backend_project_id"] = str(saved["id"])
            st.session_state["backend_run_id"] = str(run["id"])
            st.session_state["backend_bundle"] = None
            st.session_state["backend_last_refresh_at"] = 0
            st.switch_page("pages/2_🗺️_Your_Plan.py")
elif st.session_state.get("owned_blueprints_error"):
    st.caption("Saved Blueprints could not be loaded right now. You can still start a new one safely.")

if st.session_state.get("projects"):
    st.markdown("### Your Blueprints")
    project_names = list(st.session_state["projects"])
    selected_project = st.selectbox("Open a created Blueprint", project_names, label_visibility="collapsed")
    if st.button("Open selected Blueprint →", key="open_saved_project"):
        saved = st.session_state["projects"][selected_project]
        st.session_state["profile"] = saved["profile"]
        if saved.get("project_id") and saved.get("run_id"):
            st.session_state["backend_project_id"] = saved["project_id"]
            st.session_state["backend_run_id"] = saved["run_id"]
            st.session_state["backend_bundle"] = None
            st.session_state["backend_last_refresh_at"] = 0
        if saved.get("plan"):
            st.session_state["plan"] = saved["plan"]
        st.switch_page("pages/2_🗺️_Your_Plan.py")


def _create_profile(answers: dict) -> UserProfile:
    goal_codes = {
        "Build a profitable business": "small_business", "Replace my current income": "get_job",
        "Create a side income": "side_income", "Turn an idea into a real product": "startup",
        "Build a large company": "startup", "Build a brand / community": "just_explore",
        "Test whether an idea can work": "just_explore", "Create something I eventually want to sell": "startup",
        "Solve a problem I care about": "just_explore", "Build it for the experience / vibes": "just_explore", "Other": "just_explore",
    }
    location = answers.get("location_detail") or answers.get("location", "Not sure")
    customer = ", ".join(answers.get("target_customer", []))
    if answers.get("customer_detail"):
        customer = f"{customer}; {answers['customer_detail']}"
    goal_label = answers.get("goal", "Test whether an idea can work")
    selected_type = answers.get("idea_type", "Not sure")
    idea_types = {selected_type} if isinstance(selected_type, str) else set(selected_type)
    idea_type = "saas" if "App / Software" in idea_types else "service" if "Service" in idea_types else "physical_business" if "Physical store" in idea_types else "other"
    return UserProfile(
        idea=answers.get("idea", ""), idea_type=idea_type, location=location, target_customer=customer,
        background=answers.get("goal_detail", ""), life_context=answers.get("constraints", []),
        goal=goal_codes.get(goal_label, "just_explore"),
        success_definition=(f"{answers.get('success_type')}: {answers.get('success_definition', '')}" if answers.get("success_type") else ""),
        launch_timeline=answers.get("launch_timeline", ""),
        current_work=", ".join(answers.get("prior_work", [])) + (f"; {answers.get('current_work')}" if answers.get("current_work") else ""),
        constraints=answers.get("constraints", []), hours_per_week=answers.get("hours_per_week", 0),
        money_available=answers.get("money_available", 0),
    )


@st.dialog("Help us understand you better", width="small")
def questions_dialog():
    if generation_error := st.session_state.get("generation_error"):
        st.error(generation_error)
        if st.button("Retry safely", key="retry_blueprint_start", use_container_width=True):
            st.session_state["generation_error"] = None
            st.session_state["generating_blueprint"] = True
            st.rerun()
    if st.session_state.get("generating_blueprint"):
        answers = st.session_state["dialog_answers"]
        st.markdown('<div class="generation"><div class="generation-orbit"></div><h3>Starting your evidence Blueprint</h3><p>Saving your founder context, creating the owned research run, and handing it to the Supervisor.</p><div class="generation-lines"><i></i><i></i><i></i></div></div>', unsafe_allow_html=True)
        profile = _create_profile(answers)
        idempotency_key = st.session_state.setdefault("backend_idempotency_key", make_idempotency_key())
        try:
            start_result = start_blueprint(profile, answers, idempotency_key=idempotency_key)
        except BackendError as exc:
            st.session_state["generating_blueprint"] = False
            st.session_state["generation_error"] = str(exc)
            st.error(str(exc))
            st.caption("Your onboarding answers are preserved. Retry uses the same idempotency key and cannot create a duplicate run.")
            return
        st.session_state.update(
            {
                "profile": profile,
                "backend_project_id": start_result["project_id"],
                "backend_run_id": start_result["run_id"],
                "backend_start_result": start_result,
                "backend_bundle": None,
                "backend_last_refresh_at": 0,
                "show_questions": False,
                "generating_blueprint": False,
                "generation_error": None,
                "bp_selected_section": "foundation",
                "bp_auto_selected_run_id": start_result["run_id"],
            }
        )
        st.session_state.setdefault("projects", {})[profile.idea or "Untitled project"] = {
            "profile": profile,
            "project_id": start_result["project_id"],
            "run_id": start_result["run_id"],
        }
        st.switch_page("pages/2_🗺️_Your_Plan.py")
        return

    options = ["Business", "Product", "App / Software", "Service", "Physical store", "Online business", "Community", "Not sure"]
    goals = ["Build a profitable business", "Replace my current income", "Create a side income", "Turn an idea into a real product", "Build a large company", "Build a brand / community", "Test whether an idea can work", "Create something I eventually want to sell", "Solve a problem I care about", "Build it for the experience / vibes", "Other"]
    timelines = ["Within 30 days", "Within 3 months", "Within 6 months", "Within 12 months", "No fixed date", "Not sure"]
    contexts = ["Full-time job", "Caregiving", "School", "Debt or financial pressure", "Health constraint", "Relocation", "Need predictable income", "No major constraint"]
    customer_types = ["Individual consumers", "Families", "Students", "Professionals", "Small businesses", "Large companies", "Creators", "Communities", "Not sure"]
    prior_work = ["Nothing yet", "Read or watched research", "Talked to potential customers", "Built a prototype", "Created a landing page", "Made a sale", "Ran an experiment", "Compared competitors"]
    questions = ["What are you building?", "Who is it for, and where?", "Why are you building it?", "What does success look like?", "How much can you invest?", "How much time can you give?", "What have you already done?", "What are your biggest constraints?"]
    answers = st.session_state.setdefault("dialog_answers", {"idea": st.session_state.get("idea", "")})
    q = st.session_state.setdefault("dialog_question", 0)
    st.markdown("<div class='wizard-intro'>Eight quick questions will make the Blueprint specific to your context.</div>", unsafe_allow_html=True)
    st.markdown("<div class='wizard-dots'>" + "".join(f"<span class='{'active' if i == q else 'done' if i < q else ''}'></span>" for i in range(8)) + "</div>", unsafe_allow_html=True)
    with st.container(key="wizard_question_head"):
        question_col, skip_top = st.columns([4, 1])
        with question_col:
            st.markdown(f"<span class='wizard-number'>QUESTION {q + 1:02d} OF 08</span><div class='wizard-kicker'>{questions[q]}</div><div class='wizard-required'>Optional — answer what you know and refine it later</div>", unsafe_allow_html=True)
        with skip_top:
            if st.button("Skip for now", key=f"skip_top_{q}", use_container_width=True):
                if q < 7:
                    st.session_state["dialog_question"] = q + 1
                    st.rerun()
                else:
                    st.session_state["generating_blueprint"] = True
                    st.rerun()
    if q == 0:
        answers["idea"] = st.text_area("What do you want to build?", value=answers.get("idea", ""), placeholder="Tell us in your own words. It can still be vague.", height=68)
        current_type = answers.get("idea_type", "Not sure")
        if isinstance(current_type, list):
            current_type = current_type[0] if current_type else "Not sure"
        answers["idea_type"] = st.selectbox("What kind of thing is it?", options, index=options.index(current_type) if current_type in options else options.index("Not sure"))
        research_options = ["Customer research", "Competitor research", "Market research"]
        answers["research_selection"] = st.pills(
            "What should Blueprint research first?",
            research_options,
            default=answers.get("research_selection", research_options),
            selection_mode="multi",
            help="All three are selected by default. You can choose only the streams you need.",
        )
    elif q == 1:
        answers["target_customer"] = st.pills("Who do you want to build this for?", customer_types, default=answers.get("target_customer", []), selection_mode="multi")
        answers["customer_detail"] = st.text_input("Anything specific about them?", value=answers.get("customer_detail", ""), placeholder="Optional: e.g. busy professionals who train at home")
        location_options = ["India", "United States", "United Kingdom", "Other country", "Specific city / region", "Online / global", "Not sure"]
        answers["location"] = st.selectbox("Where do you want to build or sell it?", location_options, index=location_options.index(answers.get("location", "Not sure")))
        answers["location_detail"] = st.text_input("City or region", value=answers.get("location_detail", ""), placeholder="Optional: Pune, Austin, or a target country")
    elif q == 2:
        answers["goal"] = st.selectbox("What do you want this to do for you?", goals, index=goals.index(answers.get("goal", goals[6])))
        journey_modes = ["Serious business", "Side project", "Creative experiment", "Just for the vibes"]
        answers["journey_mode"] = st.selectbox("How do you want this journey to feel?", journey_modes, index=journey_modes.index(answers.get("journey_mode", "Serious business")))
        answers["goal_detail"] = st.text_area("Anything else you want this project to give you?", value=answers.get("goal_detail", ""), height=65)
    elif q == 3:
        success_options = ["First paying customers", "Replace my current income", "Reliable side income", "Launch a working product", "Reach a revenue target", "Create measurable impact", "Build an audience or community", "Not sure"]
        answers["success_type"] = st.selectbox("If this works, what would success look like?", success_options, index=success_options.index(answers.get("success_type", "Not sure")))
        answers["success_definition"] = st.text_input("What would make that success concrete?", value=answers.get("success_definition", ""), placeholder="Optional: e.g. 100 weekly active users")
    elif q == 4:
        current_money = int(answers.get("money_available", 5000) or 0)
        current_money = min(200000, max(0, round(current_money / 2500) * 2500))
        answers["money_available"] = st.slider("How much can you invest?", 0, 200000, current_money, step=2500, help="This is the maximum amount available—not what Blueprint recommends spending.")
    elif q == 5:
        answers["hours_per_week"] = st.slider("How much time can you give each week?", 0, 40, answers.get("hours_per_week", 5))
        answers["launch_timeline"] = st.selectbox("When do you want to launch or test it?", timelines, index=timelines.index(answers.get("launch_timeline", "Not sure")))
    elif q == 6:
        answers["prior_work"] = st.pills("What have you already done?", prior_work, default=answers.get("prior_work", []), selection_mode="multi")
        answers["current_work"] = st.text_input("Anything important to add?", value=answers.get("current_work", ""), placeholder="Optional detail")
    else:
        answers["constraints"] = st.pills("What could constrain you?", contexts, default=answers.get("constraints", []), selection_mode="multi")

    back, next_col = st.columns([1, 1.45])
    with back:
        if st.button("← Back", disabled=q == 0, use_container_width=True):
            st.session_state["dialog_question"] = max(0, q - 1)
            st.rerun()
    with next_col:
        label = "Generate my Blueprint →" if q == 7 else "Continue →"
        if st.button(label, type="primary", use_container_width=True):
            if q == 0 and len(str(answers.get("idea", "")).strip()) < 10:
                st.warning("Describe the idea in at least one clear sentence.")
            elif q == 0 and not answers.get("research_selection"):
                st.warning("Select at least one research stream.")
            elif q < 7:
                st.session_state["dialog_question"] = q + 1
                st.rerun()
            else:
                st.session_state["generating_blueprint"] = True
                st.rerun()


if st.session_state.get("show_questions"):
    questions_dialog()
