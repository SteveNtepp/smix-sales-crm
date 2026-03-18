"""
app_sales.py — Smix Sales Assistant (Enterprise Edition V3)
Theme: Midnight Blue & Smix Purple (#5e17eb)
Run: streamlit run app_sales.py
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import altair as alt
import urllib.parse
import re
import os
import requests
from datetime import datetime, date

import database_handler as db

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smix Sales Assistant — Enterprise Edition", 
    page_icon="🎯",
    layout="wide", 
    initial_sidebar_state="expanded",
)

@st.cache_resource
def initialize_app():
    # ── CSS ────────────────────────────────────────────────────────────────
    p = os.path.join(os.path.dirname(__file__), "style.css")
    css_content = ""
    if os.path.exists(p):
        with open(p) as f:
            css_content = f.read()
    
    # ── DATABASE ───────────────────────────────────────────────────────────
    db.init_db()
    return css_content

CSS_CONTENT = initialize_app()
st.markdown(f"<style>{CSS_CONTENT}</style>", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
for k, v in {"authenticated": False, "user": None, "page": "dashboard",
              "selected_lead": None, "show_add_lead": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CONSTANTS ──────────────────────────────────────────────────────────────────
STATUSES = ["Nouveau","Contacté","Qualifié","Relance","Paiement en attente","Inscrit/Soldé","Perdu"]
STATUS_EMOJI = {"Nouveau":"🆕","Contacté":"📞","Qualifié":"✅","Relance":"🔄",
                "Paiement en attente":"💳","Inscrit/Soldé":"🏆","Perdu":"❌"}
PROFILE_TYPES = ["Entrepreneur","Freelance","Salarié","Étudiant","Autre"]
URGENCY_TYPES = ["Immédiate","Cette semaine","Ce mois","Pas pressé"]
SCRIPT_CATEGORIES = ["Closing","Suivi","Relance","Bienvenue","Personnalisé"]

# ── HELPERS ────────────────────────────────────────────────────────────────────

def wa_link(phone: str, message: str) -> str:
    """Build WhatsApp URL — API WhatsApp avoids wa.me encoding issues with emojis."""
    clean = re.sub(r"[\s\-\(\)\+]", "", phone)
    encoded = urllib.parse.quote(message, safe='', encoding='utf-8')
    return f"https://api.whatsapp.com/send?phone={clean}&text={encoded}"


def get_absolute_url(path: str) -> str:
    """Convert relative path to absolute URL using base_url config."""
    if not path or path.startswith("http"):
        return path
    base_url = db.get_config().get("base_url", "").strip("/")
    if base_url:
        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path
        return f"{base_url}{path}"
    return path


def save_uploaded_file(uploaded_file):
    """Save file to Cloud Storage (Catbox) and return the public URL."""
    if uploaded_file is not None:
        try:
            # We use Catbox.moe for permanent, public cloud storage
            # This ensures links work perfectly on WhatsApp Cloud
            url = "https://catbox.moe/user/api.php"
            files = {'fileToUpload': (uploaded_file.name, uploaded_file.getvalue())}
            data = {'reqtype': 'fileupload'}
            
            with st.spinner("Hébergement du fichier en cours..."):
                response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                public_url = response.text.strip()
                return public_url
            else:
                st.error(f"Erreur d'hébergement (Catbox) : {response.status_code}")
                return None
        except Exception as e:
            st.error(f"Erreur de connexion cloud : {e}")
            return None
    return None


def extract_yt_id(url: str) -> str:
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else ""


def embed_youtube(url: str, height: int = 370):
    vid = extract_yt_id(url)
    if not vid:
        st.warning(f"URL invalide : {url}")
        return
    components.html(f"""
        <iframe width="100%" height="{height}"
            src="https://www.youtube.com/embed/{vid}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen style="border-radius:10px;display:block;">
        </iframe>
    """, height=height + 12)


def purple_chart(df: pd.DataFrame, x_col: str, y_col: str, x_type: str = "N") -> alt.Chart:
    """Altair bar chart with horizontal x-axis labels, purple fill, transparent bg."""
    return (
        alt.Chart(df)
        .mark_bar(color="#5e17eb", cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{x_col}:{x_type}", sort=None,
                    axis=alt.Axis(labelAngle=0, labelColor="#8892AA",
                                  titleColor="#8892AA", labelFontSize=11,
                                  gridColor="#1C2242", labelLimit=120)),
            y=alt.Y(f"{y_col}:Q",
                    axis=alt.Axis(labelColor="#8892AA", titleColor="#8892AA",
                                  gridColor="#1C2242")),
            tooltip=[x_col, y_col],
        )
        .properties(background="transparent", padding={"top": 5, "bottom": 5})
        .configure_view(strokeWidth=0)
    )


def inject_vars(tpl: str, name: str, goal: str, amount: str, program: str, start_date: str) -> str:
    return (tpl
            .replace("[Prénom]",   name or "")
            .replace("{{name}}",   name or "")
            .replace("{{goal}}",   goal or "votre objectif")
            .replace("{{amount}}", amount)
            .replace("{{program}}", program)
            .replace("{{start_date}}", start_date))


def render_score_bar(score: int, temp: str):
    color = {"🔥 Chaud":"#FF6B35","⚡ Tiède":"#F59E0B","❄️ Froid":"#60A5FA"}.get(temp,"#888")
    st.markdown(f"""
    <div class="score-gauge">
      <strong style="color:{color};font-size:1.1rem;">{score}/10</strong>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:{score*10}%;background:{color};"></div>
      </div>
      <span style="color:{color};">{temp}</span>
    </div>""", unsafe_allow_html=True)


def topbar(user: dict):
    badge = ('<span class="smix-badge-admin">⚙️ Admin</span>'
             if user["role"] == "admin"
             else '<span class="smix-badge-sales">📊 Sales</span>')
    st.markdown(f"""
    <div class="smix-topbar">
      <span class="smix-logo">🎯 Smix Sales Assistant</span>
      <div style="display:flex;align-items:center;gap:10px;">
        <span style="color:var(--text-muted);font-size:.85rem;">
          Bonjour, <strong style="color:var(--text);">{user['full_name']}</strong></span>
        {badge}
      </div>
    </div>""", unsafe_allow_html=True)


def fu_label(date_str: str):
    """Return (label_text, is_today, is_overdue)."""
    if not date_str:
        return "—", False, False
    try:
        d = date.fromisoformat(str(date_str))
        today = date.today()
        if d == today:   return f"📅 Aujourd'hui ({d.strftime('%d/%m')})", True, False
        elif d < today:  return f"⚠️ Retard {(today-d).days}j ({d.strftime('%d/%m')})", False, True
        else:            return f"🗓️ Dans {(d-today).days}j ({d.strftime('%d/%m/%Y')})", False, False
    except ValueError:
        return date_str, False, False


# ── LOGIN ──────────────────────────────────────────────────────────────────────

def page_login():
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("""
        <div style="text-align:center;padding:40px 0 24px;">
          <div style="font-size:3.5rem;">🎯</div>
          <div style="font-size:2rem;font-weight:800;
                background:linear-gradient(90deg,#5e17eb,#9B59FF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            Smix Sales Assistant
          </div>
          <p style="color:var(--text-muted);font-size:.88rem;margin-top:6px;">
            Enterprise Edition V3 — Smix Academy</p>
        </div>""", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("👤 Identifiant", placeholder="ex: steve")
            password = st.text_input("🔒 Mot de passe", type="password")
            ok = st.form_submit_button("🚀 Se connecter", use_container_width=True)
        if ok:
            user = db.authenticate(username.strip(), password.strip())
            if user:
                st.session_state.update({"authenticated": True, "user": user, "page": "dashboard"})
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects ou compte inactif.")


# ── SIDEBAR ────────────────────────────────────────────────────────────────────

def render_sidebar(user: dict):
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:10px 0 18px;">
          <div style="font-size:1.7rem;font-weight:800;
                background:linear-gradient(90deg,#5e17eb,#9B59FF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            🎯 Smix</div>
          <div style="font-size:.7rem;color:var(--text-muted);">Sales Assistant</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("**🗺️ Navigation**")
        st.markdown("---")
        nav = [("dashboard","📊","Dashboard"),("leads","👥","Mes Leads"),
               ("bulk","🚀","Envoi Groupé"),
               ("analytics","📈","Analytique"),
               ("resources","📚","Ressources")]
        if user["role"] == "admin":
            nav.append(("cockpit","⚙️","Cockpit Admin"))

        for pid, icon, label in nav:
            if st.button(f"{icon}  {label}", key=f"nav_{pid}", use_container_width=True):
                st.session_state.page = pid
                st.session_state.selected_lead = None
                st.rerun()

        st.markdown("---")
        cfg = db.get_config()
        st.markdown(f"""
        <div style="background:var(--surface2);border-radius:8px;padding:12px;border:1px solid var(--border);">
          <div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Programme actif</div>
          <div style="font-size:.82rem;font-weight:600;">{cfg.get('program_name','—')}</div>
          <div style="font-size:.75rem;color:var(--purple-light);margin-top:4px;">📅 {cfg.get('start_date','—')}</div>
          <div style="font-size:.75rem;color:var(--text-muted);">💰 {cfg.get('price_promo','—')} (Promo)</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🚪 Déconnexion", use_container_width=True):
            for k in ["authenticated","user","page","selected_lead"]: del st.session_state[k]
            st.rerun()


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

def page_dashboard(user: dict):
    topbar(user)
    is_admin = user["role"] == "admin"
    assigned = None if is_admin else user["username"]
    df  = db.get_leads(assigned_to=assigned)
    cfg = db.get_config()

    tops = db.get_weekly_kpis()
    names = {"alinne":"Alinne","manuella":"Manuella","steve":"Steve"}
    tc = st.columns(3)
    if tops["closer"]:
        with tc[0]:
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">🏆</div>
              <div class="top-closer-text">
                <strong>Top Closer : {names.get(tops["closer"]["agent"], tops["closer"]["agent"].title())} 🔥</strong>
                <span>{int(tops["closer"]["val"]*100)}% conv. sur 7j</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if tops["contacts"]:
        with tc[1]:
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">📞</div>
              <div class="top-closer-text">
                <strong>Top Prospection : {names.get(tops["contacts"]["agent"], tops["contacts"]["agent"].title())}</strong>
                <span>{int(tops["contacts"]["val"])} leads contactés</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if tops["commission"]:
        with tc[2]:
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">💰</div>
              <div class="top-closer-text">
                <strong>Top Commission : {names.get(tops["commission"]["agent"], tops["commission"]["agent"].title())}</strong>
                <span>{int(tops["commission"]["val"]):,} FCFA gagnés</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if not is_admin and any(t and t["agent"] == user["username"] for t in tops.values()):
        st.balloons()

    total   = len(df)
    closed  = len(df[df.status == "Inscrit/Soldé"]) if not df.empty else 0
    hot     = len(df[df.temperature == "🔥 Chaud"])  if not df.empty else 0
    comm    = db.get_agent_commission(user["username"]) if not is_admin else \
              (db.get_team_stats()["commission"].sum() if not db.get_team_stats().empty else 0)
    rate    = round(closed / total * 100, 1) if total > 0 else 0.0

    cols = st.columns(5)
    for col, val, lbl, ico in [
        (cols[0], str(total),        "Total Leads",         "👥"),
        (cols[1], str(closed),       "Inscrits/Soldés",     "🏆"),
        (cols[2], str(hot),          "Leads Chauds 🔥",     "🌡️"),
        (cols[3], f"{rate}%",        "Taux de Conversion",  "📈"),
        (cols[4], f"{int(comm):,}",  "Commission (FCFA)",   "💚"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-icon">{ico}</div>
              <div class="metric-value">{val}</div>
              <div class="metric-label">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-header"><span class="accent">▶</span> Pipeline Funnel</div>',
                    unsafe_allow_html=True)
        funnel = db.get_funnel_stats(assigned_to=assigned)
        if not funnel.empty:
            fd = dict(zip(funnel["status"], funnel["count"]))
            for s in STATUSES:
                st.markdown(f"""
                <div class="funnel-step">
                  <span class="funnel-label">{STATUS_EMOJI.get(s,'')} {s}</span>
                  <span class="funnel-count">{fd.get(s,0)}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Aucun lead pour le moment.")

    with c2:
        st.markdown('<div class="section-header"><span class="accent">▶</span> 📅 Planning Relances</div>',
                    unsafe_allow_html=True)
        fu_df = db.get_upcoming_followups(assigned_to=assigned)
        if fu_df.empty:
            st.info("Aucune relance planifiée. Définissez des dates sur les fiches leads.")
        else:
            tc = {"🔥 Chaud":"#FF6B35","⚡ Tiède":"#F59E0B","❄️ Froid":"#60A5FA"}
            for _, r in fu_df.iterrows():
                lbl, is_today, is_over = fu_label(r.get("follow_up_date",""))
                extra = " relance-today" if is_today else " relance-overdue" if is_over else ""
                ag = f" · {r.get('assigned_to','')}" if is_admin else ""
                st.markdown(f"""
                <div class="relance-card{extra}">
                  <div class="relance-date">{lbl}</div>
                  <div class="relance-name">{r.get('name','—')}</div>
                  <div class="relance-meta">
                    <span style="color:{tc.get(r.get('temperature',''),'#888')};">{r.get('temperature','—')}</span>
                    &nbsp;· {STATUS_EMOJI.get(r.get('status',''),'')}&nbsp;{r.get('status','—')}{ag}
                  </div>
                </div>""", unsafe_allow_html=True)

    if not df.empty:
        st.markdown('<div class="section-header" style="margin-top:1rem;"><span class="accent">▶</span> Derniers Leads</div>',
                    unsafe_allow_html=True)
        disp = df[["name","phone","status","temperature","score","follow_up_date","created_at"]].head(10).copy()
        disp.columns = ["Nom","Téléphone","Statut","Température","Score","Prochaine Relance","Créé le"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ── LEADS ─────────────────────────────────────────────────────────────────────

def page_leads(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">▶</span> Gestion des Leads</div>',
                unsafe_allow_html=True)
    is_admin = user["role"] == "admin"
    assigned = None if is_admin else user["username"]

    cs, cst, ct, ca = st.columns([3,2,2,1])
    with cs:  search  = st.text_input("🔍", placeholder="Nom ou téléphone...", label_visibility="collapsed")
    with cst: sflt    = st.selectbox("Statut", ["Tous"]+STATUSES, label_visibility="collapsed")
    with ct:  tflt    = st.selectbox("Temp.", ["Toutes","🔥 Chaud","⚡ Tiède","❄️ Froid"], label_visibility="collapsed")
    with ca:
        if st.button("➕", use_container_width=True, type="primary"):
            st.session_state.show_add_lead = not st.session_state.get("show_add_lead", False)

    df = db.get_leads(assigned_to=assigned)
    if not df.empty:
        if search: df = df[df.name.str.contains(search,case=False,na=False)|df.phone.str.contains(search,case=False,na=False)]
        if sflt != "Tous":    df = df[df.status == sflt]
        if tflt != "Toutes":  df = df[df.temperature == tflt]

    if st.session_state.get("show_add_lead"):
        _add_lead_form(user, is_admin)

    if st.session_state.selected_lead:
        _lead_detail(st.session_state.selected_lead, user)
        if st.button("← Retour"): st.session_state.selected_lead = None; st.rerun()
        return

    if df.empty:
        st.info("📭 Aucun lead."); return

    tc = {"🔥 Chaud":"#FF6B35","⚡ Tiède":"#F59E0B","❄️ Froid":"#60A5FA"}
    for _, row in df.iterrows():
        lbl, _, _ = fu_label(str(row.get("follow_up_date","") or ""))
        cl, cb = st.columns([5,1])
        with cl:
            st.markdown(f"""
            <div class="lead-card">
              <div class="lead-name">{row.get('name','—')}</div>
              <div class="lead-meta">📞 {row.get('phone','—')} &nbsp;|&nbsp; 🎯 {row.get('goal','—') or '—'}</div>
              <div class="lead-meta" style="margin-top:5px;">
                {STATUS_EMOJI.get(row.get('status',''),'')}&nbsp;<strong>{row.get('status','—')}</strong>
                &nbsp;|&nbsp;<span style="color:{tc.get(row.get('temperature',''),'#888')};">{row.get('temperature','—')}</span>
                &nbsp;|&nbsp;Score: <strong>{row.get('score',0)}/10</strong>
                &nbsp;|&nbsp;{lbl}
                {(" &nbsp;|&nbsp; 👤 "+str(row.get('assigned_to',''))) if is_admin else ""}
              </div>
            </div>""", unsafe_allow_html=True)
        with cb:
            if st.button("👁️ Voir", key=f"v_{row['id']}"):
                st.session_state.selected_lead = int(row["id"]); st.rerun()


def _add_lead_form(user: dict, is_admin: bool):
    with st.expander("➕ Nouveau Lead", expanded=True):
        with st.form("add_lead_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name  = st.text_input("👤 Nom *",       placeholder="Kofi Mensah")
                phone = st.text_input("📞 Téléphone *",  placeholder="+225 07 XX XX XX")
                email = st.text_input("📧 Email",        placeholder="kofi@gmail.com")
                goal  = st.text_input("🎯 Objectif",     placeholder="Générer des clients en ligne")
            with c2:
                ptype = st.selectbox("👤 Profil",   PROFILE_TYPES)
                urg   = st.selectbox("⏰ Urgence",  URGENCY_TYPES)
                bconf = st.checkbox("✅ Budget confirmé")
                avail = st.checkbox("📅 Disponible")
                fast  = st.checkbox("⚡ Réponse rapide")
            m1,m2,m3 = st.columns(3)
            with m1: camp = st.text_input("📡 Campagne")
            with m2: adst = st.text_input("Ad Set")
            with m3: crea = st.text_input("Créatif")
            c3, c4 = st.columns(2)
            with c3:
                if is_admin:
                    agents = db.get_sales_agents()
                    lbls = [f"{fn} ({un})" for un,fn in agents]
                    idx = st.selectbox("Assigner à", range(len(lbls)), format_func=lambda i: lbls[i])
                    ato = agents[idx][0]
                else:
                    ato = user["username"]
            with c4:
                fu_date = st.date_input("📅 Prochaine relance", value=None, min_value=date.today(), format="DD/MM/YYYY")
            notes = st.text_area("📝 Notes")
            sub = st.form_submit_button("💾 Enregistrer", use_container_width=True, type="primary")
        if sub:
            if not name or not phone: st.error("Nom et téléphone obligatoires.")
            else:
                lid = db.add_lead({"name":name,"phone":phone,"email":email,"assigned_to":ato,
                    "status":"Nouveau","goal":goal,"profile_type":ptype,"urgency":urg,
                    "budget_confirmed":int(bconf),"available":int(avail),"fast_response":int(fast),
                    "campaign":camp,"adset":adst,"creative":crea,"notes":notes,
                    "last_contact":str(date.today()),
                    "follow_up_date":str(fu_date) if fu_date else "","follow_up_day":0})
                db.log_activity(user["username"], lid, "CREATED", f"Lead {name}")
                st.success(f"✅ Lead **{name}** ajouté !"); st.session_state.show_add_lead = False; st.rerun()


def _lead_detail(lead_id: int, user: dict):
    lead = db.get_lead(lead_id)
    if not lead: st.error("Lead introuvable."); return
    cfg = db.get_config(); scripts = db.get_scripts(); templates = db.get_script_templates()
    st.markdown(f"### 👤 {lead['name']} — Fiche Lead")
    t1,t2,t3,t4 = st.tabs(["📋 Profil & Scoring","💬 Scripts WhatsApp","📚 Templates","✏️ Modifier"])

    with t1:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Contact**")
            st.markdown(f"📞 `{lead.get('phone','—')}`")
            st.markdown(f"📧 {lead.get('email') or '—'}")
            st.markdown(f"🎯 **{lead.get('goal') or '—'}**")
            st.markdown(f"👤 {lead.get('profile_type') or '—'}  |  ⏰ {lead.get('urgency') or '—'}")
            lbl,_,_ = fu_label(str(lead.get("follow_up_date","") or ""))
            st.markdown(f"📅 Relance : **{lbl}**")
        with c2:
            st.markdown("**Score Intelligence Lead**")
            render_score_bar(lead.get("score",0), lead.get("temperature","❄️ Froid"))
            st.markdown("")
            for lbl, ok in [("👤 Profil Entrepreneur/Freelance", lead.get("profile_type") in ("Entrepreneur","Freelance")),
                            ("⏰ Urgence Immédiate", lead.get("urgency")=="Immédiate"),
                            ("💰 Budget Confirmé", bool(lead.get("budget_confirmed"))),
                            ("📅 Disponible", bool(lead.get("available"))),
                            ("⚡ Réponse Rapide", bool(lead.get("fast_response")))]:
                pts = "<span style='color:var(--green);'>+2</span>" if ok else "<span style='color:var(--text-muted);'>+0</span>"
                st.markdown(f"{'✅' if ok else '❌'} {lbl} — {pts}", unsafe_allow_html=True)
        if lead.get("status") == "Inscrit/Soldé":
            amt = float(lead.get("amount_paid") or 0)
            st.markdown(f"""<div class="commission-badge" style="margin-top:12px;">
              <div class="commission-label">💚 Commission générée</div>
              <div class="commission-amount">{int(amt*0.10):,} FCFA</div>
            </div>""", unsafe_allow_html=True)

    with t2:
        days_tabs = st.tabs(["🟡 J+1","🔵 J+3","🔴 J+5","⚫ J+7"])
        for dtab, day in zip(days_tabs, ["J1","J3","J5","J7"]):
            with dtab:
                sd = scripts.get(day, {})
                filled = inject_vars(sd.get("content",""), lead.get("name",""),
                                     lead.get("goal",""), cfg.get("price_promo","75 000 FCFA"),
                                     cfg.get("program_name","Community Manager Augmenté"),
                                     cfg.get("start_date","18 Avril 2026"))
                st.markdown(f"**{sd.get('title','')}**")
                
                att = sd.get("attachment_url", "")
                final_filled = filled
                if att:
                    abs_url = get_absolute_url(att)
                    st.markdown(f"📎 **Pièce jointe :** [Ouvrir le fichier]({abs_url})")
                    final_filled += f"\n\n📎 Pièce jointe : {abs_url}"
                
                st.markdown(f'<div class="script-card">{final_filled}</div>', unsafe_allow_html=True)
                link = wa_link(lead.get("phone",""), final_filled)
                st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="margin-top:12px;display:inline-flex;">📲 Envoyer via WhatsApp (message complet)</a>',
                            unsafe_allow_html=True)
                st.text_area("📋 Copier :", value=final_filled, height=200,
                             key=f"cp_{day}_{lead_id}", label_visibility="collapsed")
                if st.button(f"✅ Marquer comme envoyé ({day})", key=f"log_dt_{day}_{lead_id}"):
                    if lead['status'] == 'Nouveau':
                        db.update_lead(lead['id'], {**lead, 'status': 'Contacté'})
                    db.log_activity(user["username"], lead['id'], "WHATSAPP_SENT", f"Détail: Script {day}")
                    st.success("Activité enregistrée !"); st.rerun()

    with t3:
        if templates.empty:
            st.info("Aucun modèle. L'admin peut en créer depuis le Cockpit Admin.")
        else:
            for cat in templates["category"].unique():
                st.markdown(f"**— {cat} —**")
                for _, tr in templates[templates["category"]==cat].iterrows():
                    with st.expander(f"📄 {tr['name']}"):
                        ft = inject_vars(tr["content"], lead.get("name",""), lead.get("goal",""),
                                        cfg.get("price_promo","75 000 FCFA"),
                                        cfg.get("program_name",""), cfg.get("start_date",""))
                        
                        att = tr.get("attachment_url", "")
                        final_ft = ft
                        if att:
                            abs_url = get_absolute_url(att)
                            st.markdown(f"📎 **Pièce jointe associée :** [Ouvrir]({abs_url})")
                            final_ft += f"\n\n📎 Pièce jointe : {abs_url}"
                            
                        st.markdown(f'<div class="script-card">{final_ft}</div>', unsafe_allow_html=True)
                        link = wa_link(lead.get("phone",""), final_ft)
                        st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="margin-top:10px;display:inline-flex;">📲 WhatsApp</a>',
                                    unsafe_allow_html=True)
                        tid = tr["id"]
                        st.text_area("📋", value=final_ft, height=120, key=f"t_{tid}_{lead_id}", label_visibility="collapsed")
                        if st.button(f"✅ Marquer comme envoyé", key=f"log_tpl_{tid}_{lead_id}"):
                            if lead['status'] == 'Nouveau':
                                db.update_lead(lead['id'], {**lead, 'status': 'Contacté'})
                            db.log_activity(user["username"], lead['id'], "WHATSAPP_SENT", f"Détail: Tpl {tr['name']}")
                            st.success("Activité enregistrée !"); st.rerun()

    with t4:
        with st.form(f"edit_{lead_id}"):
            c1,c2 = st.columns(2)
            with c1:
                name   = st.text_input("👤 Nom",       value=lead.get("name",""))
                phone  = st.text_input("📞 Téléphone", value=lead.get("phone",""))
                email  = st.text_input("📧 Email",     value=lead.get("email","") or "")
                goal   = st.text_input("🎯 Objectif",  value=lead.get("goal","") or "")
                sidx   = STATUSES.index(lead["status"]) if lead.get("status") in STATUSES else 0
                status = st.selectbox("📌 Statut", STATUSES, index=sidx)
                amount = st.number_input("💰 Montant payé (FCFA)", value=float(lead.get("amount_paid") or 0), step=5000.0)
            with c2:
                pidx  = PROFILE_TYPES.index(lead["profile_type"]) if lead.get("profile_type") in PROFILE_TYPES else 0
                ptype = st.selectbox("👤 Profil",  PROFILE_TYPES, index=pidx)
                uidx  = URGENCY_TYPES.index(lead["urgency"]) if lead.get("urgency") in URGENCY_TYPES else 0
                urg   = st.selectbox("⏰ Urgence", URGENCY_TYPES, index=uidx)
                bconf = st.checkbox("✅ Budget confirmé", value=bool(lead.get("budget_confirmed")))
                avail = st.checkbox("📅 Disponible",      value=bool(lead.get("available")))
                fast  = st.checkbox("⚡ Réponse rapide",  value=bool(lead.get("fast_response")))
                efd   = None
                if lead.get("follow_up_date"):
                    try: efd = date.fromisoformat(str(lead["follow_up_date"]))
                    except: pass
                fu_date = st.date_input("📅 Prochaine relance", value=efd, min_value=date.today(), format="DD/MM/YYYY")
            m1,m2,m3 = st.columns(3)
            with m1: camp = st.text_input("Campagne", value=lead.get("campaign","") or "")
            with m2: adst = st.text_input("Ad Set",   value=lead.get("adset","") or "")
            with m3: crea = st.text_input("Créatif",  value=lead.get("creative","") or "")
            if user["role"] == "admin":
                agents = db.get_sales_agents(); lbls = [f"{fn} ({un})" for un,fn in agents]
                cur = lead.get("assigned_to",""); cidx = next((i for i,(un,_) in enumerate(agents) if un==cur),0)
                aidx = st.selectbox("Assigner à", range(len(lbls)), index=cidx, format_func=lambda i: lbls[i])
                ato  = agents[aidx][0]
            else:
                ato = lead["assigned_to"]
            notes = st.text_area("📝 Notes", value=lead.get("notes","") or "")
            save  = st.form_submit_button("💾 Sauvegarder", use_container_width=True, type="primary")
        if save:
            db.update_lead(lead_id, {"name":name,"phone":phone,"email":email,"assigned_to":ato,
                "status":status,"goal":goal,"profile_type":ptype,"urgency":urg,
                "budget_confirmed":int(bconf),"available":int(avail),"fast_response":int(fast),
                "amount_paid":amount,"campaign":camp,"adset":adst,"creative":crea,
                "notes":notes,"last_contact":str(date.today()),
                "follow_up_date":str(fu_date) if fu_date else ""})
            db.log_activity(user["username"], lead_id, "UPDATED", f"Statut → {status}")
            st.success("✅ Mis à jour !"); st.rerun()
        if user["role"] == "admin":
            st.markdown("---")
            if st.button("🗑️ Supprimer ce lead"):
                db.delete_lead(lead_id); db.log_activity(user["username"], lead_id, "DELETED", "")
                st.session_state.selected_lead = None; st.rerun()




# ── BULK MESSAGING ────────────────────────────────────────────────────────────

def page_bulk_messaging(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">🚀</span> Envoi Groupé (Diffusion)</div>',
                unsafe_allow_html=True)
    
    is_admin = user["role"] == "admin"
    leads_df = db.get_leads(assigned_to=None if is_admin else user["username"])
    
    if leads_df.empty:
        st.info("Aucun lead disponible pour l'envoi groupé.")
        return

    # Filters
    st.markdown("#### 1. Filtrer les leads")
    c1, c2 = st.columns(2)
    with c1:
        f_status = st.multiselect("Statut", STATUSES, default=["Nouveau", "Relance"])
    with c2:
        f_temp = st.multiselect("Température", ["🔥 Chaud", "⚡ Tiède", "❄️ Froid"], default=["🔥 Chaud", "⚡ Tiède"])
    
    filtered_df = leads_df.copy()
    if f_status:
        filtered_df = filtered_df[filtered_df["status"].isin(f_status)]
    if f_temp:
        filtered_df = filtered_df[filtered_df["temperature"].isin(f_temp)]
        
    st.info(f"💡 **{len(filtered_df)}** leads correspondent à vos filtres.")
    
    if filtered_df.empty:
        st.warning("Aucun lead ne correspond aux filtres sélectionnés.")
        return

    # Template selection
    st.markdown("---")
    st.markdown("#### 2. Configurer le message")
    
    scripts = db.get_scripts()
    tpls = db.get_script_templates()
    
    all_templates = {}
    for day in ["J1", "J3", "J5", "J7"]:
        s = scripts.get(day)
        if s: all_templates[f"📜 {s['title']}"] = {"content": s["content"], "attachment": s.get("attachment_url", "")}
            
    for _, t in tpls.iterrows():
        all_templates[f"📚 {t['category']} : {t['name']}"] = {"content": t["content"], "attachment": t.get("attachment_url", "")}
        
    sel_tpl_name = st.selectbox("Modèle à utiliser", list(all_templates.keys()))
    sel_tpl_data = all_templates[sel_tpl_name]
    sel_tpl_content = sel_tpl_data["content"]
    att = sel_tpl_data["attachment"]
    
    cfg = db.get_config()

    st.markdown("---")
    st.markdown("#### 3. Exécution")
    
    # NEW: Stabilization of the list
    if "bulk_leads_ids" not in st.session_state:
        st.session_state.bulk_leads_ids = []
    if "bulk_idx" not in st.session_state:
        st.session_state.bulk_idx = 0

    # Detect mismatch between filters and loaded list
    current_filter_ids = filtered_df["id"].tolist()
    mismatch = st.session_state.bulk_leads_ids != current_filter_ids
    
    if mismatch and st.session_state.bulk_leads_ids:
        st.warning(f"⚠️ Vos filtres ont changé ({len(current_filter_ids)} leads) mais la campagne actuelle contient encore {len(st.session_state.bulk_leads_ids)} leads.")

    if not st.session_state.bulk_leads_ids or st.button("🔄 Charger / Réinitialiser la liste", type="primary" if mismatch else "secondary"):
        st.session_state.bulk_leads_ids = current_filter_ids
        st.session_state.bulk_idx = 0
        st.rerun()

    total_leads = len(st.session_state.bulk_leads_ids)
    
    if st.session_state.bulk_idx < total_leads:
        current_id = st.session_state.bulk_leads_ids[st.session_state.bulk_idx]
        # Get fresh lead data for this ID
        lead_data = db.get_lead(current_id)
        
        if not lead_data:
            st.session_state.bulk_idx += 1
            st.rerun()

        # Prepare message
        # In Bulk Messaging, we now have 'att' from the selection above
        
        filled = inject_vars(sel_tpl_content, str(lead_data["name"]), str(lead_data["goal"]),
                             cfg.get("price_promo", "75 000 FCFA"), cfg.get("program_name", ""),
                             cfg.get("start_date", "18 Avril 2026"))
        
        final_filled = filled
        if att:
            abs_url = get_absolute_url(att)
            final_filled += f"\n\n📎 Pièce jointe : {abs_url}"
            
        # Display lead info and script
        st.markdown(f"""
        <div style="background:var(--surface2); padding: 20px; border-radius: 12px; border: 1px solid var(--purple); margin-bottom: 10px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--purple-light);">
                Lead {st.session_state.bulk_idx + 1} / {total_leads} : {lead_data['name']}
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
                📞 {lead_data['phone']} | Statut: {lead_data['status']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if att:
            st.info("📎 **Pièce jointe incluse**")
            
        final_filled_html = final_filled.replace("\n", "<br>")
        st.markdown(f'<div class="script-card">{final_filled_html}</div>', unsafe_allow_html=True)
        
        link = wa_link(str(lead_data["phone"]), final_filled)
        
        # Action Buttons
        st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="width: 100%; justify-content: center; text-align: center; margin-bottom: 10px;">📲 1. Ouvrir WhatsApp & Envoyer</a>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 2. Confirmer & Suivant", use_container_width=True, type="primary"):
                # Mark as contacted and Log
                if lead_data['status'] == 'Nouveau':
                    db.update_lead(current_id, {**lead_data, 'status': 'Contacté'})
                db.log_activity(user["username"], current_id, "WHATSAPP_SENT", f"Bulk: {sel_tpl_name}")
                st.session_state.bulk_idx += 1
                st.rerun()
        
        with c2:
            if st.button("⏭️ Sauter / Plus tard", use_container_width=True):
                st.session_state.bulk_idx += 1
                st.rerun()
                
        st.caption("Instructions : Cliquez sur le bouton vert pour envoyer. Une fois envoyé sur WhatsApp, cliquez sur 'Confirmer & Suivant' pour valider vos points. Si vous ne voulez pas contacter ce lead maintenant, cliquez sur 'Sauter'.")
    else:
        st.success(f"🎉 Campagne terminée ! {total_leads} prospects ont été passés en revue.")
        if st.button("Recommencer une nouvelle campagne"):
            st.session_state.bulk_leads_ids = []
            st.session_state.bulk_idx = 0
            st.rerun()


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

def page_analytics(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">▶</span> Analytique & Performance</div>',
                unsafe_allow_html=True)
    is_admin = user["role"] == "admin"

    # ── Commission badge — correctly scoped per role
    if is_admin:
        stats = db.get_team_stats()
        total_comm = float(stats["commission"].sum()) if not stats.empty else 0.0
        comm_label = "💚 Commission Totale Équipe"
        df = db.get_leads()
    else:
        total_comm = db.get_agent_commission(user["username"])
        comm_label = f"💚 Ma Commission — {user['full_name']}"
        df = db.get_leads(assigned_to=user["username"])

    st.markdown(f"""
    <div class="commission-badge" style="margin-bottom:1.5rem;">
      <div class="commission-label">{comm_label}</div>
      <div class="commission-amount">{int(total_comm):,} FCFA</div>
    </div>""", unsafe_allow_html=True)

    if is_admin:
        tops = db.get_weekly_kpis()
        names = {"alinne":"Alinne","manuella":"Manuella","steve":"Steve"}
        tc = st.columns(3)
        if tops["closer"]:
            with tc[0]:
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">🏆</div>
                  <div class="top-closer-text">
                    <strong>Top Closer : {names.get(tops["closer"]["agent"], tops["closer"]["agent"].title())} 🔥</strong>
                    <span>{int(tops["closer"]["val"]*100)}% conv. sur 7j</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        if tops["contacts"]:
            with tc[1]:
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">📞</div>
                  <div class="top-closer-text">
                    <strong>Top Prospection : {names.get(tops["contacts"]["agent"], tops["contacts"]["agent"].title())}</strong>
                    <span>{int(tops["contacts"]["val"])} leads contactés</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        if tops["commission"]:
            with tc[2]:
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">💰</div>
                  <div class="top-closer-text">
                    <strong>Top Commission : {names.get(tops["commission"]["agent"], tops["commission"]["agent"].title())}</strong>
                    <span>{int(tops["commission"]["val"]):,} FCFA gagnés</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        st.info("Aucune donnée disponible."); return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📊 Répartition Funnel**")
        funnel = db.get_funnel_stats(assigned_to=None if is_admin else user["username"])
        if not funnel.empty:
            st.altair_chart(purple_chart(funnel, "status", "count"), use_container_width=True)

    with c2:
        st.markdown("**🌡️ Température des Leads**")
        temp_df = df.groupby("temperature").size().reset_index(name="count")
        if not temp_df.empty:
            st.altair_chart(purple_chart(temp_df, "temperature", "count"), use_container_width=True)

    if is_admin:
        st.markdown("---")
        st.markdown("**📡 ROAS par Créatif Meta Ads**")
        roas = db.get_roas_by_creative()
        if not roas.empty:
            st.dataframe(roas, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun tracking créatif disponible.")

        st.markdown("---")
        st.markdown("**👥 Performance par Agent**")
        if not stats.empty:
            disp = stats.rename(columns={"agent":"Agent","total_leads":"Leads","closed":"Inscrits",
                                          "lost":"Perdus","revenue":"CA (FCFA)",
                                          "commission":"Commission (FCFA)","conversion_rate":"% Conv."})
            st.dataframe(disp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**🎯 Distribution des Scores**")
    score_df = df.groupby("score").size().reset_index(name="count")
    score_df["score"] = score_df["score"].astype(str)
    if not score_df.empty:
        st.altair_chart(purple_chart(score_df, "score", "count", "O"), use_container_width=True)

    if is_admin:
        st.markdown("---")
        st.markdown("**📋 Journal d'Activité**")
        log_df = db.get_recent_activity()
        if not log_df.empty:
            st.dataframe(log_df, use_container_width=True, hide_index=True)


# ── RESOURCES PAGE ────────────────────────────────────────────────────────────

def page_resources(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">▶</span> 📚 Kit Commercial & Formations</div>',
                unsafe_allow_html=True)

    sections = db.get_kit_sections()
    videos   = db.get_videos()

    # Build dynamic tabs: sections + videos tab
    tab_labels = [f"{s['icon']} {s['title']}" for s in sections] + ["🎬 Formations Vidéo"]
    tabs = st.tabs(tab_labels)

    # Kit content sections — use st.markdown() for native table/heading rendering
    for tab, section in zip(tabs[:-1], sections):
        with tab:
            st.markdown(section["content"])
            with st.expander("📋 Afficher en texte brut (copier)"):
                st.text_area("", value=section["content"], height=250,
                             key=f"raw_{section['section_key']}", label_visibility="collapsed")

    # Videos tab
    with tabs[-1]:
        st.markdown("**Regardez les formations directement dans l'outil — sans quitter l'application.**")
        if not videos:
            st.info("Aucune vidéo disponible. L'admin peut en ajouter depuis le Cockpit Admin.")
        else:
            # 2-column grid for videos
            for i in range(0, len(videos), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(videos):
                        v = videos[i + j]
                        with col:
                            st.markdown(f"""
                            <div style="background:var(--surface2);border:1px solid var(--border);
                                        border-radius:10px;padding:14px;margin-bottom:12px;">
                              <div style="font-weight:700;color:var(--text);margin-bottom:4px;">
                                🎬 {v['title']}</div>
                              <div style="font-size:.78rem;color:var(--text-muted);margin-bottom:10px;">
                                {v['description']}</div>
                            </div>""", unsafe_allow_html=True)
                            embed_youtube(v["youtube_url"])


# ── COCKPIT ADMIN ─────────────────────────────────────────────────────────────

def page_cockpit_admin(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">▶</span> Cockpit Admin</div>',
                unsafe_allow_html=True)
    if user["role"] != "admin":
        st.error("🔒 Accès réservé."); return

    t1,t2,t3,t4,t5,t6,t7 = st.tabs([
        "⚙️ Offre","✏️ Scripts J1-J7","📚 Modèles Scripts",
        "📖 Ressources Kit","🎬 Vidéos","👥 Agents","📊 Leaderboard & Export"
    ])
    cfg = db.get_config()

    # ── Config
    with t1:
        with st.form("cfg"):
            pn  = st.text_input("📚 Programme",    value=cfg.get("program_name",""))
            sd  = st.text_input("📅 Démarrage",    value=cfg.get("start_date",""))
            pp  = st.text_input("💰 Prix Promo",   value=cfg.get("price_promo",""))
            ps  = st.text_input("💰 Prix Std",     value=cfg.get("price_standard",""))
            cr  = st.text_input("📊 Commission %", value=cfg.get("commission_rate","10"))
            sav = st.form_submit_button("💾 Sauvegarder", type="primary", use_container_width=True)
        if sav:
            for k,v in [("program_name",pn),("start_date",sd),("price_promo",pp),
                        ("price_standard",ps),("commission_rate",cr)]: db.update_config(k,v)
            st.success("✅ Configuration mise à jour !"); st.rerun()

    # ── Scripts J1-J7
    with t2:
        sc = db.get_scripts()
        for day in ["J1","J3","J5","J7"]:
            d = sc.get(day,{})
            with st.expander(f"**{day}** — {d.get('title','')}"):
                with st.form(f"sc_{day}", clear_on_submit=False):
                    nt = st.text_input("Titre",    value=d.get("title",""), key=f"t_{day}")
                    nc = st.text_area("Contenu",   value=d.get("content",""), height=250, key=f"c_{day}", 
                                      help="💡 WhatsApp : *Gras*, _Italique_, ~Barré~, ```Code```")
                    
                    # File uploader directly in the form
                    up_s = st.file_uploader("Changer la pièce jointe", type=["pdf","jpg","jpeg","png","mp3","mp4"], key=f"fup_{day}")
                    
                    # We still keep the text input in case they want to use an external link
                    na = st.text_input("Ou Lien externe", value=d.get("attachment_url",""), key=f"a_{day}")
                    
                    sv = st.form_submit_button(f"💾 Sauvegarder {day}", use_container_width=True)
                
                if sv:
                    final_url = na
                    if up_s:
                        path_s = save_uploaded_file(up_s)
                        if path_s: final_url = path_s
                    
                    db.update_script(day, nt, nc, final_url)
                    db.update_script(day, nt, nc, final_url)
                    st.success(f"✅ {day} sauvegardé !")
                    st.rerun()

    # ── Script templates
    with t3:
        with st.expander("➕ Ajouter un modèle", expanded=False):
            with st.form("add_tpl_new", clear_on_submit=True):
                tn  = st.text_input("Nom")
                tc_ = st.selectbox("Catégorie", SCRIPT_CATEGORIES)
                tco = st.text_area("Contenu", height=200, help="💡 WhatsApp : *Gras*, _Italique_, ~Barré~")
                up_new = st.file_uploader("Pièce jointe (Optionnel)", type=["pdf","jpg","jpeg","png","mp3","mp4"])
                tau = st.text_input("Ou Lien externe (Optionnel)")
                atb = st.form_submit_button("💾 Ajouter", type="primary", use_container_width=True)
            
            if atb:
                final_url = tau
                if up_new:
                    path_new = save_uploaded_file(up_new)
                    if path_new: final_url = path_new
                
                if tn and tco:
                    db.add_script_template(tn, tc_, tco, user["username"], final_url)
                    st.success("✅ Modèle ajouté !")
                    st.rerun()
                else:
                    st.error("Nom et contenu requis.")
        tpls = db.get_script_templates()
        if tpls.empty:
            st.info("Aucun modèle.")
        else:
            for _,tr in tpls.iterrows():
                with st.expander(f"📄 {tr['name']} — {tr['category']}"):
                    ca,cb = st.columns([3,1])
                    with ca:
                        with st.form(f"etpl_form_{tr['id']}"):
                            en = st.text_input("Nom",      value=tr["name"],     key=f"en_{tr['id']}")
                            ec = st.selectbox("Catégorie", SCRIPT_CATEGORIES,
                                             index=SCRIPT_CATEGORIES.index(tr["category"]) if tr["category"] in SCRIPT_CATEGORIES else 0,
                                             key=f"ec_{tr['id']}")
                            eco= st.text_area("Contenu",   value=tr["content"],  height=180, key=f"eco_{tr['id']}")
                            
                            up_e = st.file_uploader("Changer la pièce jointe", type=["pdf","jpg","jpeg","png","mp3","mp4"], key=f"up_e_{tr['id']}")
                            eau= st.text_input("Lien actuel/externe", value=tr.get("attachment_url",""), key=f"eau_{tr['id']}")
                            
                            sv = st.form_submit_button("💾 Modifier", use_container_width=True)
                        
                        if sv:
                            final_url = eau
                            if up_e:
                                path_e = save_uploaded_file(up_e)
                                if path_e: final_url = path_e
                            
                            db.update_script_template(int(tr["id"]), en, ec, eco, final_url)
                            db.update_script_template(int(tr["id"]), en, ec, eco, final_url)
                            st.success("✅ Modèle sauvegardé !")
                            st.rerun()
                    with cb:
                        st.markdown(f"*Par {tr.get('created_by','—')}*")
                        if st.button("🗑️ Supprimer", key=f"dt_{tr['id']}"):
                            db.delete_script_template(int(tr["id"])); st.rerun()

    # ── Kit sections editor
    with t4:
        st.markdown("Modifiez le contenu de chaque section du kit commercial.")
        sections = db.get_kit_sections()
        for sec in sections:
            with st.expander(f"{sec['icon']} {sec['title']}"):
                with st.form(f"kit_{sec['section_key']}"):
                    icon_  = st.text_input("Icône emoji", value=sec["icon"], key=f"ki_{sec['section_key']}")
                    title_ = st.text_input("Titre",       value=sec["title"], key=f"kt_{sec['section_key']}")
                    cont_  = st.text_area("Contenu (Markdown)",   value=sec["content"],
                                         height=350, key=f"kc_{sec['section_key']}")
                    sv_    = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
                if sv_:
                    db.update_kit_section(sec["section_key"], title_, icon_, cont_)
                    st.success("✅ Section mise à jour !"); st.rerun()

    # ── Videos manager
    with t5:
        st.markdown("**Gestion des vidéos de formation**")
        with st.expander("➕ Ajouter une vidéo", expanded=False):
            with st.form("add_vid", clear_on_submit=True):
                vt  = st.text_input("Titre")
                vd  = st.text_input("Description")
                vu  = st.text_input("URL YouTube (youtu.be/...)")
                vo  = st.number_input("Ordre", value=0, step=1)
                avb = st.form_submit_button("💾 Ajouter", type="primary", use_container_width=True)
            if avb:
                if vt and vu:
                    db.add_video(vt,vd,vu,int(vo),user["username"]); st.success("✅ Vidéo ajoutée !"); st.rerun()
                else: st.error("Titre et URL requis.")
        vids = db.get_videos()
        if not vids: st.info("Aucune vidéo.")
        else:
            for v in vids:
                with st.expander(f"🎬 {v['title']}"):
                    embed_youtube(v["youtube_url"], height=250)
                    ca,cb = st.columns([3,1])
                    with ca:
                        with st.form(f"ev_{v['id']}"):
                            evt = st.text_input("Titre",       value=v["title"],       key=f"vt_{v['id']}")
                            evd = st.text_input("Description", value=v["description"], key=f"vd_{v['id']}")
                            evu = st.text_input("URL",         value=v["youtube_url"], key=f"vu_{v['id']}")
                            evo = st.number_input("Ordre",     value=int(v["order_idx"]), step=1, key=f"vo_{v['id']}")
                            svv = st.form_submit_button("💾 Modifier", use_container_width=True)
                        if svv: db.update_video(int(v['id']),evt,evd,evu,int(evo)); st.success("✅"); st.rerun()
                    with cb:
                        if st.button("🗑️ Supprimer", key=f"dv_{v['id']}"):
                            db.delete_video(int(v["id"])); st.rerun()

    # ── Agents
    with t6:
        users_df = db.get_all_users()
        if not users_df.empty:
            st.dataframe(users_df.rename(columns={"id":"ID","username":"Login",
                "full_name":"Nom","role":"Rôle","active":"Actif","created_at":"Créé le"}),
                use_container_width=True, hide_index=True)
        st.markdown("---")
        ca, cb = st.columns(2)
        with ca:
            st.markdown("**➕ Créer un agent**")
            with st.form("new_user", clear_on_submit=True):
                fn = st.text_input("Nom complet",  placeholder="Paul Dupont")
                un = st.text_input("Identifiant",  placeholder="paul")
                pw = st.text_input("Mot de passe", type="password")
                rl = st.selectbox("Rôle", ["sales","admin"])
                cr2= st.form_submit_button("✅ Créer", type="primary", use_container_width=True)
            if cr2:
                if fn and un and pw:
                    ok = db.create_user(un,pw,rl,fn)
                    st.success(f"✅ Agent **{fn}** créé !") if ok else st.error(f"❌ Login `{un}` déjà utilisé.")
                    if ok: st.rerun()
                else: st.error("Tous les champs sont requis.")
        with cb:
            st.markdown("**🔒 Réinitialiser mot de passe**")
            if not users_df.empty:
                with st.form("pwd_reset", clear_on_submit=True):
                    uid_map = {f"{r['full_name']} ({r['username']})": r["id"] for _,r in users_df.iterrows()}
                    sel_u   = st.selectbox("Agent", list(uid_map.keys()))
                    npw     = st.text_input("Nouveau MDP", type="password")
                    rb      = st.form_submit_button("🔑 Réinitialiser", use_container_width=True)
                if rb:
                    if npw: db.reset_user_password(uid_map[sel_u],npw); st.success("✅ MDP réinitialisé !")
                    else: st.error("MDP vide.")
        st.markdown("---")
        st.markdown("**🔄 Activer / Désactiver**")
        if not users_df.empty:
            for _,row in users_df.iterrows():
                cn,cb2 = st.columns([3,1])
                with cn: st.markdown(f"{'🟢' if row['active'] else '🔴'} **{row['full_name']}** (`{row['username']}`) — {row['role']}")
                with cb2:
                    lbl = "Désactiver" if row["active"] else "Activer"
                    if st.button(lbl, key=f"tog_{row['id']}"): db.update_user_status(int(row["id"]),not bool(row["active"])); st.rerun()

    # ── Leaderboard & Export
    with t7:
        st.markdown("**🏆 Leaderboard**")
        stats = db.get_team_stats()
        tops = db.get_weekly_kpis()
        top_c = tops["closer"]["agent"] if tops["closer"] else ""
        if stats.empty:
            st.info("Aucune donnée.")
        else:
            stats = stats.sort_values("conversion_rate",ascending=False).reset_index(drop=True)
            for i,row in stats.iterrows():
                rank = ["🥇","🥈","🥉"][i] if i < 3 else f"#{i+1}"
                is_t = row["agent"] == top_c
                st.markdown(f"""
                <div class="leaderboard-row" style="{'border-color:var(--purple);' if is_t else ''}">
                  <div class="leaderboard-rank">{rank}</div>
                  <div class="leaderboard-name">{row['agent'].title()}{'&nbsp;🔥' if is_t else ''}</div>
                  <div class="leaderboard-stat">
                    <div style="color:var(--purple-light);font-weight:700;">{int(row.get('conversion_rate',0))}% conv.</div>
                    <div style="color:var(--green);">{int(row.get('commission',0)):,} FCFA commission</div>
                    <div>{int(row.get('closed',0))} / {int(row.get('total_leads',0))} leads</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**📤 Export Excel**")
        all_df = db.get_leads()
        st.write(f"**{len(all_df)} leads** dans la base.")
        if not all_df.empty:
            xlsx = db.export_leads_excel()
            st.download_button("⬇️ Télécharger Excel",data=xlsx,
                file_name=f"smix_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary", use_container_width=True)


# ── ROUTER ────────────────────────────────────────────────────────────────────

def main():
    if not st.session_state.authenticated:
        page_login(); return
    user = st.session_state.user
    render_sidebar(user)
    page = st.session_state.page
    if page == "dashboard":   page_dashboard(user)
    elif page == "leads":     page_leads(user)
    elif page == "bulk":      page_bulk_messaging(user)
    elif page == "analytics": page_analytics(user)
    elif page == "resources": page_resources(user)
    elif page == "cockpit" and user["role"] == "admin": page_cockpit_admin(user)
    else: page_dashboard(user)

if __name__ == "__main__":
    main()
