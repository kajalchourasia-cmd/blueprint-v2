"""Standalone Streamlit rendering of the healthcare dashboard reference."""

from __future__ import annotations

import streamlit as st


def render_health_dashboard() -> None:
    """Render the complete healthcare dashboard without Blueprint dependencies."""

    st.set_page_config(
        page_title="Superpower — Sophia Caldwell",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
        <style>
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display:none !important; }
        [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main { background:#020202 !important; }
        .block-container { max-width:none !important; padding:0 !important; }
        iframe { display:block; width:100% !important; border:0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    dashboard_html = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* { box-sizing: border-box; }
:root {
  --canvas: #020202;
  --board: #e9e9e9;
  --ink: #171717;
  --muted: #8c8c8c;
  --line: rgba(20,20,20,.075);
  --acid: #dfff00;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--canvas); }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display:none !important; }
[data-testid="stAppViewContainer"] > .main { background: var(--canvas); }
.block-container { max-width:none !important; padding:18px !important; }
.health-board {
  width:min(1760px, calc(100vw - 36px)); min-height:calc(100vh - 36px); margin:0 auto;
  padding:30px 30px 26px; overflow:hidden; color:var(--ink); background:var(--board);
  border:1px solid rgba(255,255,255,.65); border-radius:34px;
  font-family:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;
  box-shadow:0 45px 110px rgba(0,0,0,.48);
}
.health-board button { font:inherit; }
.topbar { height:54px; display:flex; align-items:center; justify-content:space-between; margin-bottom:17px; }
.brand { font-size:18px; font-weight:700; letter-spacing:-.055em; }
.top-actions { display:flex; gap:8px; }
.round-button {
  width:43px; height:43px; display:grid; place-items:center; border:0; border-radius:50%;
  background:rgba(255,255,255,.72); color:#272727; box-shadow:0 4px 18px rgba(0,0,0,.035);
}
.round-button svg { width:20px; height:20px; fill:none; stroke:currentColor; stroke-width:1.65; }
.dashboard-grid { display:grid; grid-template-columns:285px minmax(0,1fr); gap:34px; }
.side-tabs { display:flex; gap:23px; align-items:end; height:62px; margin-bottom:25px; }
.side-tabs span { font-size:29px; letter-spacing:-.065em; color:#aaa; }
.side-tabs .active { color:#191919; }
.filter-pill {
  height:56px; padding:0 17px; display:flex; align-items:center; justify-content:space-between;
  background:rgba(255,255,255,.75); border-radius:28px; margin-bottom:12px; box-shadow:0 8px 30px rgba(0,0,0,.025);
}
.filter-left { display:flex; gap:12px; align-items:center; font-size:14px; font-weight:550; }
.filter-icon { width:26px; height:26px; display:grid; place-items:center; border:1px solid #b5b5b5; border-radius:7px; color:#777; }
.filter-count { padding:7px 11px; border-radius:17px; background:rgba(255,255,255,.75); color:#888; font-size:11px; }
.filter-x { font-size:18px; color:#666; }
.category-list { border-top:1px solid var(--line); }
.category {
  height:65px; padding:0 10px; display:grid; grid-template-columns:24px 1fr auto; align-items:center; gap:11px;
  border-bottom:1px solid var(--line); color:#333; font-size:14px;
}
.category .ico { width:20px; text-align:center; color:#858585; font-size:17px; }
.membership {
  margin-top:23px; padding:18px; min-height:145px; border-radius:24px; background:rgba(255,255,255,.7);
  position:relative; overflow:hidden;
}
.membership b { display:inline-block; background:var(--acid); border-radius:13px; padding:5px 10px; font-size:10px; }
.membership h4 { font-size:14px; margin:15px 0 4px; }
.membership p { margin:0; color:#9a9a9a; font-size:11px; line-height:1.4; }
.try-button { position:absolute; right:14px; bottom:14px; border:0; border-radius:20px; padding:10px 17px; background:#fff; font-size:11px; }
.content { min-width:0; }
.hero-row { display:grid; grid-template-columns:minmax(0,1fr) 386px; gap:24px; align-items:start; }
.profile-area { min-width:0; }
.profile-title { margin:2px 0 20px; font-size:54px; font-weight:400; letter-spacing:-.075em; line-height:1; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; align-items:end; margin-bottom:26px; }
.stat { position:relative; min-height:58px; display:flex; align-items:center; justify-content:center; gap:9px; }
.dot-number { font-family:"Courier New",monospace; font-size:41px; font-weight:400; letter-spacing:-.12em; }
.stat-label { align-self:flex-start; margin-top:5px; padding:5px 8px; border-radius:12px; background:rgba(255,255,255,.43); color:#7d7d7d; font-size:9px; white-space:nowrap; }
.stat:first-child .stat-label { background:var(--acid); color:#303500; font-weight:700; }
.record-actions { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.action-card { min-height:274px; padding:22px; position:relative; border-radius:30px; overflow:hidden; }
.upload-card { background:rgba(255,255,255,.72); }
.test-card { background:radial-gradient(circle at 52% 50%, #ff1364 0 8%, #ff4f87 20%, #f8a5bb 50%, #efcbd3 78%, #e7d8dc 100%); }
.action-title { display:flex; justify-content:space-between; font-size:14px; line-height:1.08; }
.plus { width:31px; height:31px; display:grid; place-items:center; border-radius:50%; background:rgba(255,255,255,.55); font-size:19px; }
.paper-stack { position:absolute; left:50%; top:48%; width:75px; height:88px; transform:translate(-50%,-50%); }
.paper-stack:before,.paper-stack:after { content:""; position:absolute; inset:0; border-radius:7px; background:#fff; box-shadow:0 12px 24px rgba(0,0,0,.04); }
.paper-stack:before { transform:rotate(-8deg) translate(-10px,2px); opacity:.55; }
.paper-stack:after { background:repeating-linear-gradient(to bottom,#fff 0 12px,#e8e8e8 13px,#fff 14px); }
.record-copy { position:absolute; left:20px; bottom:20px; font-size:12px; }
.record-copy small { color:#aaa; }
.target { position:absolute; left:50%; top:51%; transform:translate(-50%,-50%); width:95px; height:95px; border:1px solid rgba(255,255,255,.42); border-radius:50%; }
.target:before,.target:after { content:""; position:absolute; border:1px solid rgba(255,255,255,.46); border-radius:50%; inset:15px; }
.target:after { inset:34px; background:var(--acid); border:6px solid #ff4c79; box-shadow:0 0 0 1px rgba(255,255,255,.65); }
.target-ripples { position:absolute; left:50%; bottom:30px; transform:translateX(-50%); color:rgba(255,255,255,.7); letter-spacing:-3px; font-size:21px; }
.timeline {
  height:72px; position:relative; display:grid; grid-template-columns:1fr auto 1fr; align-items:center;
  margin:0 0 22px; border-radius:36px; background:rgba(255,255,255,.22); overflow:hidden;
}
.timeline:before { content:""; position:absolute; left:6%; right:6%; top:50%; height:1px; background:rgba(0,0,0,.08); }
.timeline-dots { height:100%; opacity:.62; background-image:radial-gradient(circle,#aaa 1.2px,transparent 1.4px); background-size:31px 13px; background-position:center; }
.timeline-dots.right { opacity:.28; }
.health-improving { z-index:1; min-width:220px; padding:13px 22px; border-radius:28px; background:rgba(255,255,255,.78); box-shadow:0 8px 24px rgba(0,0,0,.035); }
.health-improving b { display:block; font-size:13px; font-weight:500; }
.health-improving small { color:#a5a5a5; font-size:9px; }
.lower-layout { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:24px; }
.score-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.score-card { height:342px; padding:29px; position:relative; border-radius:34px; overflow:hidden; text-align:center; }
.score-green { background:linear-gradient(180deg,#f6b06e 0%,#d8cf65 25%,#4dbc49 53%,#059632 78%,#02842b 100%); }
.score-age { background:radial-gradient(circle at 43% 55%,#ff9912 0 18%,#ff9b27 27%,rgba(240,150,98,.7) 48%,rgba(228,142,154,.75) 68%,#b6cfdb 100%); }
.score-label { color:rgba(255,255,255,.84); font-size:14px; }
.score-number { margin-top:58px; color:rgba(255,255,255,.86); font-family:"Courier New",monospace; font-size:75px; letter-spacing:-.12em; line-height:.8; }
.score-sub { color:rgba(255,255,255,.76); margin-top:15px; font-size:12px; }
.mini-dot-chart { position:absolute; left:16%; right:16%; bottom:30px; height:45px; opacity:.58; background-image:radial-gradient(circle,rgba(255,255,255,.9) 1.5px,transparent 1.8px); background-size:9px 9px; mask-image:linear-gradient(12deg,transparent 0 26%,#000 28% 78%,transparent 80%); }
.age-ruler { position:absolute; left:13%; right:13%; bottom:32px; height:46px; border-bottom:1px solid rgba(255,255,255,.5); background:repeating-linear-gradient(90deg,transparent 0 10px,rgba(255,255,255,.45) 11px 12px,transparent 13px 20px); mask-image:linear-gradient(to bottom,transparent,#000); }
.age-ruler:after { content:""; position:absolute; left:45%; bottom:0; width:3px; height:50px; background:white; border-radius:2px; }
.pending-card { height:342px; padding:27px; position:relative; border-radius:34px; background:rgba(255,255,255,.68); }
.pending-card h3 { margin:0; font-size:15px; font-weight:500; }
.pending-x { position:absolute; right:25px; top:22px; color:#888; }
.days { margin-top:66px; font-size:40px; letter-spacing:-.06em; }
.days small { font-size:11px; color:#999; vertical-align:top; margin-left:4px; }
.result-progress { margin-top:20px; display:flex; align-items:center; gap:10px; }
.result-progress .yellow { width:19px; height:19px; background:var(--acid); border-radius:50%; box-shadow:0 0 13px #dfff00; }
.result-progress .line { width:90px; height:3px; background:linear-gradient(90deg,#ddd,#aaa); border-radius:2px; }
.vial-wrap { position:absolute; right:24px; top:88px; width:112px; height:154px; display:grid; place-items:center; border-radius:54px; background:rgba(255,255,255,.66); }
.vial { width:27px; height:72px; border-radius:5px 5px 12px 12px; background:linear-gradient(90deg,#eee,#fff 45%,#ddd); position:relative; transform:rotate(-3deg); box-shadow:0 9px 14px rgba(0,0,0,.08); }
.vial:before { content:""; position:absolute; left:-2px; right:-2px; top:-10px; height:17px; border-radius:5px; background:linear-gradient(#e9571b,#a92b11); }
.vial:after { content:""; position:absolute; left:4px; right:4px; top:26px; height:20px; background:#df6036; opacity:.75; }
.pending-note { position:absolute; bottom:24px; color:#aaa; font-size:10px; line-height:1.35; }
.section-heading { margin:28px 0 15px; display:flex; justify-content:space-between; align-items:center; }
.section-heading h2 { margin:0; font-size:29px; font-weight:400; letter-spacing:-.055em; }
.section-heading p { margin:4px 0 0; color:#9b9b9b; font-size:11px; }
.see-all { border:0; border-radius:22px; background:rgba(255,255,255,.75); padding:12px 18px; font-size:11px; }
.bottom-sections { display:grid; grid-template-columns:minmax(0,1.02fr) minmax(0,.98fr); gap:28px; }
.cards-row { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
.metric-card,.product-card { min-height:232px; padding:19px; border-radius:27px; background:rgba(255,255,255,.72); overflow:hidden; position:relative; }
.metric-card .metric-name { color:#7d7d7d; font-size:11px; }
.metric-card .metric-value { position:absolute; left:18px; bottom:54px; font-family:"Courier New",monospace; font-size:42px; letter-spacing:-.1em; }
.metric-card .metric-unit { position:absolute; right:16px; bottom:61px; color:#888; font-size:9px; }
.metric-spark { position:absolute; left:15px; right:15px; bottom:17px; height:27px; background:repeating-linear-gradient(90deg,transparent 0 11px,#b2b2b2 12px 13px,transparent 14px 19px); mask-image:linear-gradient(8deg,transparent 0 15%,#000 18% 74%,transparent 78%); opacity:.65; }
.product-card { text-align:center; }
.badge { position:absolute; left:15px; top:14px; background:var(--acid); border-radius:13px; padding:5px 9px; font-size:9px; font-weight:700; }
.orb { width:91px; height:91px; margin:36px auto 8px; border-radius:50%; box-shadow:0 20px 23px rgba(0,0,0,.15); }
.orb.green { background:radial-gradient(circle at 33% 28%,#e3ffcb 0 8%,#83ca6c 24%,#389541 55%,#1c4f2d 100%); }
.orb.blue { background:radial-gradient(circle at 32% 27%,#eefaff 0 10%,#b7ddfb 32%,#75a8e9 59%,#4d68a5 100%); }
.orb.peach { background:radial-gradient(circle at 34% 28%,#ffd5a3 0 10%,#e69555 42%,#a94725 72%,#76321f 100%); }
.product-name { color:#777; font-size:10px; }
.product-price { margin-top:7px; font-size:19px; letter-spacing:-.04em; }
@media (max-width:1180px) {
  .dashboard-grid { grid-template-columns:230px minmax(0,1fr); gap:22px; }
  .hero-row { grid-template-columns:1fr; }
  .record-actions { display:none; }
  .profile-title { font-size:46px; }
  .lower-layout { grid-template-columns:1fr; }
  .pending-card { display:none; }
  .bottom-sections { grid-template-columns:1fr; }
}
@media (max-width:760px) {
  .block-container { padding:0 !important; }
  .health-board { width:100%; min-height:100vh; border-radius:0; padding:20px 14px; }
  .dashboard-grid { display:block; }
  .sidebar { display:none; }
  .profile-title { font-size:39px; }
  .stats { grid-template-columns:repeat(2,1fr); }
  .score-grid { grid-template-columns:1fr; }
  .cards-row { grid-template-columns:1fr 1fr; }
}
</style>
</head>
<body>

<main class="health-board">
  <header class="topbar">
    <div class="brand">superpower</div>
    <div class="top-actions">
      <button class="round-button" aria-label="Cart"><svg viewBox="0 0 24 24"><path d="M3 4h2l2.1 10.1a2 2 0 0 0 2 1.6h7.8a2 2 0 0 0 2-1.6L20 8H7"/><circle cx="10" cy="19" r="1.3"/><circle cx="17" cy="19" r="1.3"/></svg></button>
      <button class="round-button" aria-label="Profile"><svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.2"/><path d="M6.5 19c.5-3.5 2.4-5.3 5.5-5.3s5 1.8 5.5 5.3M5.4 9.5A7 7 0 0 1 7 4.8M18.6 9.5A7 7 0 0 0 17 4.8"/></svg></button>
    </div>
  </header>

  <div class="dashboard-grid">
    <aside class="sidebar">
      <div class="side-tabs"><span class="active">Data</span><span>Records</span></div>
      <div class="filter-pill"><div class="filter-left"><span class="filter-icon">▧</span><span>All Data</span></div><span class="filter-x">×</span></div>
      <div class="category-list">
        <div class="category"><span class="ico">⌁</span><span>Longevity Markers</span><span class="filter-count">85%</span></div>
        <div class="category"><span class="ico">♡</span><span>Heart Health</span><span class="filter-count">72/100</span></div>
        <div class="category"><span class="ico">⌁</span><span>Thyroid Health</span><span></span></div>
        <div class="category"><span class="ico">◌</span><span>Immune Regulation</span><span></span></div>
        <div class="category"><span class="ico">↗</span><span>Hormone Health</span><span class="filter-count">Balanced</span></div>
        <div class="category"><span class="ico">♨</span><span>Metabolic Health</span><span class="filter-count">78/100</span></div>
        <div class="category"><span class="ico">⬡</span><span>Nutrients</span><span></span></div>
        <div class="category"><span class="ico">♧</span><span>Blood</span><span class="filter-count">Normal</span></div>
      </div>
      <div class="membership"><b>Go Pro</b><h4>Free Premium Subscription</h4><p>Unlock deeper health insights and<br>personalized recommendations.</p><button class="try-button">Try it</button></div>
    </aside>

    <section class="content">
      <div class="hero-row">
        <div class="profile-area">
          <h1 class="profile-title">Sophia Caldwell</h1>
          <div class="stats">
            <div class="stat"><span class="dot-number">108</span><span class="stat-label">Total</span></div>
            <div class="stat"><span class="dot-number">80</span><span class="stat-label">Optimal</span></div>
            <div class="stat"><span class="dot-number">21</span><span class="stat-label">In range</span></div>
            <div class="stat"><span class="dot-number">5</span><span class="stat-label">Out of range</span></div>
          </div>
          <div class="timeline"><div class="timeline-dots"></div><div class="health-improving"><b>↗&nbsp; Health Improving</b><small>+12 since last test</small></div><div class="timeline-dots right"></div></div>
        </div>
        <div class="record-actions">
          <div class="action-card upload-card"><div class="action-title"><span>Upload<br>Health Records</span><span class="plus">+</span></div><div class="paper-stack"></div><div class="record-copy">Existing Records<br><small>2 files</small></div></div>
          <div class="action-card test-card"><div class="action-title"><span>Test a New<br>Biomarker</span><span class="plus">+</span></div><div class="target"></div><div class="target-ripples">‹‹‹◎›››</div></div>
        </div>
      </div>

      <div class="lower-layout">
        <div class="score-grid">
          <div class="score-card score-green"><div class="score-label">Biological Score</div><div class="score-number">70</div><div class="score-sub">On Track</div><div class="mini-dot-chart"></div></div>
          <div class="score-card score-age"><div class="score-label">Biological Age</div><div class="score-number">25</div><div class="score-sub">2.3 years younger</div><div class="age-ruler"></div></div>
        </div>
        <div class="pending-card"><span class="pending-x">×</span><h3>Your results are pending</h3><div class="days">7-10<small>Days</small></div><div class="result-progress"><span class="yellow"></span><span class="line"></span></div><div class="vial-wrap"><div class="vial"></div></div><div class="pending-note">You'll hear from us once<br>your lab processing is complete.</div></div>
      </div>

      <div class="bottom-sections">
        <section>
          <div class="section-heading"><div><h2>Biomarkers</h2><p>A snapshot of what's happening inside your body</p></div><button class="see-all">See All</button></div>
          <div class="cards-row">
            <div class="metric-card"><div class="metric-name">♡ &nbsp; LDL Cholesterol</div><div class="metric-value">103</div><div class="metric-unit">mg/dL</div><div class="metric-spark"></div></div>
            <div class="metric-card"><div class="metric-name">⬡ &nbsp; Ferritin</div><div class="metric-value">43</div><div class="metric-unit">ng/mL</div><div class="metric-spark" style="transform:scaleY(.72)"></div></div>
            <div class="metric-card"><div class="metric-name">♡ &nbsp; Apolipoprotein A1</div><div class="metric-value">42</div><div class="metric-unit">mg/dL</div><div class="metric-spark" style="opacity:.4"></div></div>
          </div>
        </section>
        <section>
          <div class="section-heading"><div><h2>Top Supplements for You</h2><p>Support your balance with options picked for you.</p></div><button class="see-all">See All</button></div>
          <div class="cards-row">
            <div class="product-card"><span class="badge">Best Seller</span><div class="orb green"></div><div class="product-name">Comprehensive Greens</div><div class="product-price">$24.30</div></div>
            <div class="product-card"><span class="badge">Best Seller</span><div class="orb blue"></div><div class="product-name">Daily Hydration</div><div class="product-price">$19.90</div></div>
            <div class="product-card"><div class="orb peach"></div><div class="product-name">Omega Balance</div><div class="product-price">$45.00</div></div>
          </div>
        </section>
      </div>
    </section>
  </div>
</main>
</body>
</html>
"""
    # Streamlit's HTML element currently passes multiline content through a
    # Markdown-compatible parser. Compacting prevents four-space-indented
    # descendants from being interpreted as fenced source code.
    st.html("".join(line.strip() for line in dashboard_html.splitlines()))
