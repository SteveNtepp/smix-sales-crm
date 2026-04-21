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
import invoice_generator as ig
from translations import t

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smix Sales Assistant — Enterprise Edition", 
    page_icon="🎯",
    layout="wide", 
    initial_sidebar_state="expanded",
)

@st.cache_resource
def initialize_db():
    db.init_db()

def load_css():
    p = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(p):
        with open(p, "r") as f:
            return f.read()
    return ""

# ── INIT & BRANDING ────────────────────────────────────────────────────────────
initialize_db()
CSS_CONTENT = load_css()
st.markdown(f"<style>{CSS_CONTENT}</style>", unsafe_allow_html=True)

# ── SESSION STATE ──────────────────────────────────────────────────────────────
for k, v in {"authenticated": False, "user": None, "page": "dashboard",
              "selected_lead": None, "show_add_lead": False, "lang": "fr"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── CONSTANTS (INTERNAL DB VALUES & KEYS) ──────────────────────────────────────
STATUSES = ["Nouveau","Contacté","Qualifié","Relance","Paiement en attente","Inscrit/Soldé","Perdu"]
STATUS_KEYS = {
    "Nouveau": "status_new", "Contacté": "status_contacted", "Qualifié": "status_qualified",
    "Relance": "status_followup", "Paiement en attente": "status_pending",
    "Inscrit/Soldé": "status_closed", "Perdu": "status_lost"
}
STATUS_EMOJI = {"Nouveau":"🆕","Contacté":"📞","Qualifié":"✅","Relance":"🔄",
                "Paiement en attente":"💳","Inscrit/Soldé":"🏆","Perdu":"❌"}

TEMP_KEYS = {
    "🔥 Chaud": "temp_hot", "⚡ Tiède": "temp_warm", "❄️ Froid": "temp_cold"
}

PROFILE_TYPES = ["Entrepreneur","Freelance","Salarié","Étudiant","Autre"]

PROFILE_KEYS = {
    "Entrepreneur": "profile_entrepreneur", "Freelance": "profile_freelance",
    "Salarié": "profile_employee", "Étudiant": "profile_student", "Autre": "profile_other"
}

URGENCY_TYPES = ["Immédiate","Cette semaine","Ce mois","Pas pressé"]
URGENCY_KEYS = {
    "Immédiate": "urgency_immediate", "Cette semaine": "urgency_this_week",
    "Ce mois": "urgency_this_month", "Pas pressé": "urgency_not_hurried"
}

SCRIPT_CATEGORIES = ["Closing","Suivi","Relance","Bienvenue","Personnalisé"]
SCRIPT_CAT_KEYS = {
    "Closing": "cat_closing", "Suivi": "cat_followup_s", "Relance": "cat_relance",
    "Bienvenue": "cat_welcome", "Personnalisé": "cat_custom"
}


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
            url = "https://catbox.moe/user/api.php"
            files = {'fileToUpload': (uploaded_file.name, uploaded_file.getvalue())}
            data = {'reqtype': 'fileupload'}
            with st.spinner(t("upload_spinner")):
                response = requests.post(url, data=data, files=files)
            if response.status_code == 200:
                public_url = response.text.strip()
                return public_url
            else:
                st.error(t("upload_err_catbox").format(response.status_code))
                return None
        except Exception as e:
            st.error(t("upload_err_conn").format(e))
            return None
    return None


def extract_yt_id(url: str) -> str:
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else ""


def embed_youtube(url: str, height: int = 370):
    vid = extract_yt_id(url)
    if not vid:
        st.warning(t("url_invalid").format(url))
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


def inject_vars(tpl: str, lead_name: str, lead_goal: str, amount: str, program: str, start_date: str) -> str:
    return (tpl
            .replace("[Prénom]",   lead_name or "")
            .replace("{{name}}",   lead_name or "")
            .replace("{{goal}}",   lead_goal or "votre objectif")
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
    notifs = db.get_notifications(user["username"], only_unread=True)
    badge = (f'<span class="smix-badge-admin">{t("badge_admin")}</span>'
             if user["role"] == "admin"
             else f'<span class="smix-badge-sales">{t("badge_sales")}</span>')
    notif_count_html = ""
    if notifs:
        notif_count_html = f'<div class="notif-badge">{len(notifs)}</div>'
    st.markdown(f"""
    <div class="smix-topbar">
      <div style="display:flex;align-items:center;">
        <span class="smix-logo">🎯 Smix Sales Assistant</span>
      </div>
      <div style="display:flex;align-items:center;gap:20px;">
        <div class="smix-notif-icon">🔔 {notif_count_html}</div>
        <span style="color:var(--text-muted);font-size:.85rem;">
          {t('greeting')} <strong style="color:var(--text);">{user['full_name']}</strong></span>
        {badge}
      </div>
    </div>""", unsafe_allow_html=True)
    if notifs:
        with st.expander(t("notif_new")):
            for n in notifs:
                c1, c2 = st.columns([4, 1])
                with c1: st.info(n["message"])
                with c2:
                    if st.button(t("notif_validate"), key=f"nr_{n['id']}"):
                        db.mark_notification_as_read(n["id"])
                        st.rerun()


def fu_label(date_str: str):
    """Return (label_text, is_today, is_overdue)."""
    if not date_str:
        return "—", False, False
    try:
        d = date.fromisoformat(str(date_str))
        today = date.today()
        if d == today:
            return t("fu_today").format(d.strftime('%d/%m')), True, False
        elif d < today:
            return t("fu_overdue").format((today-d).days, d.strftime('%d/%m')), False, True
        else:
            return t("fu_future").format((d-today).days, d.strftime('%d/%m/%Y')), False, False
    except ValueError:
        return date_str, False, False


# ── LOGIN ──────────────────────────────────────────────────────────────────────

def page_login():
    # Language toggle at top-right
    c_sp, c_lang = st.columns([10, 1])
    with c_lang:
        if st.button(t("lang_toggle_label"), key="lang_login"):
            st.session_state.lang = "en" if st.session_state.lang == "fr" else "fr"
            st.rerun()

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown(f"""
        <div style="text-align:center;padding:40px 0 24px;">
          <div style="font-size:3.5rem;">🎯</div>
          <div style="font-size:2rem;font-weight:800;
                background:linear-gradient(90deg,#5e17eb,#9B59FF);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            {t('app_title')}
          </div>
          <p style="color:var(--text-muted);font-size:.88rem;margin-top:6px;">
            {t('app_subtitle')}</p>
        </div>""", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input(t("login_username"), placeholder="ex: steve")
            password = st.text_input(t("login_password"), type="password")
            ok = st.form_submit_button(t("login_btn"), use_container_width=True)
        if ok:
            user = db.authenticate(username.strip(), password.strip())
            if user:
                st.session_state.update({"authenticated": True, "user": user, "page": "dashboard"})
                st.rerun()
            else:
                st.error(t("login_error"))


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

        # Language toggle
        if st.button(t("lang_toggle_label"), key="lang_sidebar", use_container_width=True):
            st.session_state.lang = "en" if st.session_state.lang == "fr" else "fr"
            st.rerun()
        st.markdown("---")

        nav = [("dashboard", t("nav_dashboard")),

               ("leads",     t("nav_leads")),
               ("bulk",      t("nav_bulk")),
               ("analytics", t("nav_analytics")),
               ("resources", t("nav_resources"))]
        if user["role"] == "admin":
            nav.append(("cockpit", t("nav_cockpit")))

        for pid, label in nav:
            if st.button(label, key=f"nav_{pid}", use_container_width=True):
                st.session_state.page = pid
                st.session_state.selected_lead = None
                st.rerun()

        st.markdown("---")

        # Active offer: prefer first active offer, fall back to config


        # Active offer: prefer first active offer, fall back to config
        offers = db.get_offers()
        active_offers = [o for o in offers if o.get("is_active")]
        if active_offers:
            ao = active_offers[0]
            prog_name   = ao.get("program_name", "—")
            start_date  = ao.get("start_date", "—")
            price_promo = ao.get("price_promo", "—")
        else:
            cfg = db.get_config()
            prog_name   = cfg.get("program_name", "—")
            start_date  = cfg.get("start_date", "—")
            price_promo = cfg.get("price_promo", "—")
        st.markdown(f"""
        <div style="background:var(--surface2);border-radius:8px;padding:12px;border:1px solid var(--border);">
          <div style="font-size:.7rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">{t('sidebar_active_prog')}</div>
          <div style="font-size:.82rem;font-weight:600;">{prog_name}</div>
          <div style="font-size:.75rem;color:var(--purple-light);margin-top:4px;">{t('sidebar_start')} {start_date}</div>
          <div style="font-size:.75rem;color:var(--text-muted);">{t('sidebar_promo')} {price_promo} {t('sidebar_promo_label')}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        if st.button(t("sidebar_logout"), use_container_width=True):
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
    # Agent names can be kept as is or mapped if needed, but they are from DB typically
    tc = st.columns(3)
    if tops["closer"]:
        with tc[0]:
            agent_name = tops["closer"]["agent"].title()
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">🏆</div>
              <div class="top-closer-text">
                <strong>{t('dash_top_closer')} : {agent_name} 🔥</strong>
                <span>{int(tops["closer"]["val"]*100)}% {t('dash_conv_rate')}</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if tops["contacts"]:
        with tc[1]:
            agent_name = tops["contacts"]["agent"].title()
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">📞</div>
              <div class="top-closer-text">
                <strong>{t('dash_top_prospe')} : {agent_name}</strong>
                <span>{int(tops["contacts"]["val"])} {t('dash_leads_contacted')}</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if tops["commission"]:
        with tc[2]:
            agent_name = tops["commission"]["agent"].title()
            st.markdown(f"""
            <div class="top-closer-banner">
              <div class="top-closer-icon">💰</div>
              <div class="top-closer-text">
                <strong>{t('dash_top_comm')} : {agent_name}</strong>
                <span>{int(tops["commission"]["val"]):,} {t('dash_fcfa_earned')}</span>
              </div>
            </div>""", unsafe_allow_html=True)
    if not is_admin and any(t_ and t_["agent"] == user["username"] for t_ in tops.values()):
        st.balloons()

    total   = len(df)
    closed  = len(df[df.status == "Inscrit/Soldé"]) if not df.empty else 0
    hot     = len(df[df.temperature == "🔥 Chaud"])  if not df.empty else 0
    comm    = db.get_agent_commission(user["username"]) if not is_admin else \
              (db.get_team_stats()["commission"].sum() if not db.get_team_stats().empty else 0)
    rate    = round(closed / total * 100, 1) if total > 0 else 0.0

    cols = st.columns(5)
    for col, val, lbl, ico in [
        (cols[0], str(total),        t("kpi_total_leads"),   "👥"),
        (cols[1], str(closed),       t("kpi_closed"),        "🏆"),
        (cols[2], str(hot),          t("kpi_hot"),           "🌡️"),
        (cols[3], f"{rate}%",        t("kpi_rate"),          "📈"),
        (cols[4], f"{int(comm):,}",  t("kpi_commission"),    "💚"),
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
        st.markdown(f'<div class="section-header"><span class="accent">▶</span> {t("dash_funnel")}</div>',
                    unsafe_allow_html=True)
        funnel = db.get_funnel_stats(assigned_to=assigned)
        if not funnel.empty:
            fd = dict(zip(funnel["status"], funnel["count"]))
            for s_val in STATUSES:
                st.markdown(f"""
                <div class="funnel-step">
                  <span class="funnel-label">{STATUS_EMOJI.get(s_val,'')} {t(STATUS_KEYS.get(s_val,s_val))}</span>
                  <span class="funnel-count">{fd.get(s_val,0)}</span>
                </div>""", unsafe_allow_html=True)

        else:
            st.info(t("dash_no_leads"))

    with c2:
        st.markdown(f'<div class="section-header"><span class="accent">▶</span> {t("dash_planning")}</div>',
                    unsafe_allow_html=True)
        fu_df = db.get_upcoming_followups(assigned_to=assigned)
        if fu_df.empty:
            st.info(t("dash_no_followup"))
        else:
            tc_map = {"🔥 Chaud":"#FF6B35","⚡ Tiède":"#F59E0B","❄️ Froid":"#60A5FA"}
            for _, r in fu_df.iterrows():
                lbl, is_today, is_over = fu_label(r.get("follow_up_date",""))
                extra = " relance-today" if is_today else " relance-overdue" if is_over else ""
                ag = f" · {r.get('assigned_to','')}" if is_admin else ""
                st.markdown(f"""
                <div class="relance-card{extra}">
                  <div class="relance-date">{lbl}</div>
                  <div class="relance-name">{r.get('name','—')}</div>
                  <div class="relance-meta">
                    <span style="color:{tc_map.get(r.get('temperature',''),'#888')};">{t(TEMP_KEYS.get(r.get('temperature',''), r.get('temperature','—')))}</span>
                    &nbsp;· {STATUS_EMOJI.get(r.get('status',''),'')}&nbsp;{t(STATUS_KEYS.get(r.get('status',''), r.get('status','—')))}{ag}
                  </div>
                </div>""", unsafe_allow_html=True)


    if not df.empty:
        st.markdown(f'<div class="section-header" style="margin-top:1rem;"><span class="accent">▶</span> {t("dash_latest_leads")}</div>',
                    unsafe_allow_html=True)
        disp = df[["name","phone","status","temperature","score","follow_up_date","created_at"]].head(10).copy()
        disp.columns = [t("col_name"), t("col_phone"), t("col_status"), t("col_temp"), t("col_score"), t("col_followup"), t("col_created")]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ── LEADS ─────────────────────────────────────────────────────────────────────

def page_leads(user: dict):
    topbar(user)
    st.markdown('<div class="section-header"><span class="accent">▶</span> Gestion des Leads</div>',
                unsafe_allow_html=True)
    is_admin = user["role"] == "admin"
    assigned = None if is_admin else user["username"]

    cs, cst, ct, ca = st.columns([3,2,2,1])
    with cs:  search  = st.text_input("🔍", placeholder=t("leads_search"), label_visibility="collapsed")
    with cst: sflt    = st.selectbox(t("leads_filter_status"), ["Tous"]+STATUSES, label_visibility="collapsed",
                                     format_func=lambda x: t("leads_filter_all_status") if x=="Tous" else f"{STATUS_EMOJI.get(x,'')} {t(STATUS_KEYS.get(x,x))}")
    with ct:  tflt    = st.selectbox(t("leads_filter_temp"), ["Toutes","🔥 Chaud","⚡ Tiède","❄️ Froid"], label_visibility="collapsed",
                                     format_func=lambda x: t("temp_all") if x=="Toutes" else x)
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
                {STATUS_EMOJI.get(row.get('status',''),'')}&nbsp;<strong>{t(STATUS_KEYS.get(row.get('status',''), row.get('status','—')))}</strong>
                &nbsp;|&nbsp;<span style="color:{tc.get(row.get('temperature',''),'#888')};">{t(TEMP_KEYS.get(row.get('temperature',''), row.get('temperature','—')))}</span>
                &nbsp;|&nbsp;{t('col_score')}: <strong>{row.get('score',0)}/10</strong>
                &nbsp;|&nbsp;{lbl}
                {(" &nbsp;|&nbsp; 👤 "+str(row.get('assigned_to',''))) if is_admin else ""}
              </div>
            </div>""", unsafe_allow_html=True)

        with cb:
            if st.button("👁️ Voir", key=f"v_{row['id']}"):
                st.session_state.selected_lead = int(row["id"]); st.rerun()


def _add_lead_form(user: dict, is_admin: bool):
    with st.expander(t("add_lead_title"), expanded=True):
        # Load offers for selectbox
        all_offers = db.get_offers()
        offer_labels = [t("field_offer_none")] + [f"{o['program_name']} ({o.get('price_promo','')})" for o in all_offers]
        offer_ids    = [None] + [o["id"] for o in all_offers]
        with st.form("add_lead_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name  = st.text_input(t("field_name"),  placeholder="Kofi Mensah")
                phone = st.text_input(t("field_phone"), placeholder="+225 07 XX XX XX")
                email = st.text_input(t("field_email"), placeholder="kofi@gmail.com")
                goal  = st.text_input(t("field_goal"),  placeholder="Générer des clients en ligne")
            with c2:
                ptype = st.selectbox(t("field_profile"),  PROFILE_TYPES, format_func=lambda x: t(PROFILE_KEYS.get(x,x)))
                urg   = st.selectbox(t("field_urgency"),   URGENCY_TYPES, format_func=lambda x: t(URGENCY_KEYS.get(x,x)))
                bconf = st.checkbox(t("field_budget"))
                avail = st.checkbox(t("field_available"))
                fast  = st.checkbox(t("field_fast"))

            m1,m2,m3 = st.columns(3)
            with m1: camp = st.text_input(t("field_campaign"))
            with m2: adst = st.text_input(t("field_adset"))
            with m3: crea = st.text_input(t("field_creative"))
            # Offer selectbox
            offer_idx = st.selectbox(t("field_offer"), range(len(offer_labels)), format_func=lambda i: offer_labels[i])
            c3, c4 = st.columns(2)
            with c3:
                if is_admin:
                    agents = db.get_sales_agents()
                    lbls = [f"{fn} ({un})" for un,fn in agents]
                    idx = st.selectbox(t("field_assign"), range(len(lbls)), format_func=lambda i: lbls[i])
                    ato = agents[idx][0]
                else:
                    ato = user["username"]
            with c4:
                fu_date = st.date_input(t("field_followup_date"), value=None, min_value=date.today(), format="DD/MM/YYYY")
            notes = st.text_area(t("field_notes"))
            sub = st.form_submit_button(t("btn_save"), use_container_width=True, type="primary")
        if sub:
            if not name or not phone:
                st.error(t("err_name_phone"))
            else:
                selected_offer_id = offer_ids[offer_idx]
                lid = db.add_lead({"name":name,"phone":phone,"email":email,"assigned_to":ato,
                    "status":"Nouveau","goal":goal,"profile_type":ptype,"urgency":urg,
                    "budget_confirmed":int(bconf),"available":int(avail),"fast_response":int(fast),
                    "campaign":camp,"adset":adst,"creative":crea,"notes":notes,
                    "last_contact":str(date.today()),
                    "follow_up_date":str(fu_date) if fu_date else "","offer_id": selected_offer_id})
                db.log_activity(user["username"], lid, "CREATED", f"Lead {name}")
                st.success(t("success_lead_added").format(f"**{name}**"))
                st.session_state.show_add_lead = False; st.rerun()


def _lead_detail(lead_id: int, user: dict):
    lead = db.get_lead(lead_id)
    if not lead: st.error(t("err_lead_not_found")); return
    cfg = db.get_config(); scripts = db.get_scripts(); templates = db.get_script_templates()

    # Get offer info for variable injection
    off_data = None
    if lead.get("offer_id"):
        off_data = db.get_offer(lead["offer_id"])
    
    # Fallback to global config if no offer or missing fields
    prog_name = off_data.get("program_name") if off_data else cfg.get("program_name", "")
    p_promo   = off_data.get("price_promo") if off_data else cfg.get("price_promo", "")
    s_date    = off_data.get("start_date") if off_data else cfg.get("start_date", "")

    st.markdown(f"### 👤 {lead['name']} — {t('detail_title')}")
    t1,t2,t3,t4,t5 = st.tabs([
        t("detail_tab_profile"), t("detail_tab_scripts"), 
        t("detail_tab_templates"), t("detail_tab_edit"), t("detail_tab_docs")
    ])

    with t1:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown(t("detail_contact"))
            st.markdown(f"📞 `{lead.get('phone','—')}`")
            st.markdown(f"📧 {lead.get('email') or '—'}")
            st.markdown(f"🎯 **{lead.get('goal') or '—'}**")
            st.markdown(f"👤 {lead.get('profile_type') or '—'}  |  ⏰ {lead.get('urgency') or '—'}")
            lbl,_,_ = fu_label(str(lead.get("follow_up_date","") or ""))
            st.markdown(f"{t('detail_relance')} **{lbl}**")
            if lead.get("offer_id") and off_data:
                st.markdown(f"{t('detail_offer_label')} **{off_data['program_name']}** ({off_data.get('price_promo','')})")
            else:
                st.markdown(f"{t('detail_offer_label')} {t('detail_no_offer')}")
        with c2:
            st.markdown(t("detail_score"))
            render_score_bar(lead.get("score",0), t(TEMP_KEYS.get(lead.get("temperature",""), lead.get("temperature","❄️ Froid"))))
            st.markdown("")

            for clbl, ok in [("👤 Profil Entrepreneur/Freelance", lead.get("profile_type") in ("Entrepreneur","Freelance")),
                             ("⏰ Urgence Immédiate", lead.get("urgency")=="Immédiate"),
                             ("💰 Budget Confirmé", bool(lead.get("budget_confirmed"))),
                             ("📅 Disponible", bool(lead.get("available"))),
                             ("⚡ Réponse Rapide", bool(lead.get("fast_response")))]:
                pts = "<span style='color:var(--green);'>+2</span>" if ok else "<span style='color:var(--text-muted);'>+0</span>"
                st.markdown(f"{'✅' if ok else '❌'} {clbl} — {pts}", unsafe_allow_html=True)
        
        if lead.get("status") == "Inscrit/Soldé":
            amt = float(lead.get("amount_paid") or 0)
            comm_rate = float(off_data.get("commission_rate", 10)) if off_data else float(cfg.get("commission_rate", 10))
            comm_val = int(amt * comm_rate / 100)
            st.markdown(f"""<div class="commission-badge" style="margin-top:12px;">
              <div class="commission-label">{t('detail_commission_gen')}</div>
              <div class="commission-amount">{comm_val:,} FCFA</div>
            </div>""", unsafe_allow_html=True)

    with t2:
        days_tabs = st.tabs(["🟡 J+1","🔵 J+3","🔴 J+5","⚫ J+7"])
        for dtab, day in zip(days_tabs, ["J1","J3","J5","J7"]):
            with dtab:
                sd = scripts.get(day, {})
                filled = inject_vars(sd.get("content",""), lead.get("name",""),
                                     lead.get("goal",""), p_promo, prog_name, s_date)
                st.markdown(f"**{sd.get('title','')}**")
                
                att = sd.get("attachment_url", "")
                final_filled = filled
                if att:
                    abs_url = get_absolute_url(att)
                    st.markdown(f"📎 **{t('script_attachment')} :** [Ouvrir le fichier]({abs_url})")
                    final_filled += f"\n\n📎 {t('script_attachment')} : {abs_url}"
                
                st.markdown(f'<div class="script-card">{final_filled}</div>', unsafe_allow_html=True)
                link = wa_link(lead.get("phone",""), final_filled)
                st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="margin-top:12px;display:inline-flex;">📲 {t("btn_send_wa_full")}</a>',
                            unsafe_allow_html=True)
                st.text_area(t("label_copy"), value=final_filled, height=200,
                             key=f"cp_{day}_{lead_id}", label_visibility="collapsed")
                if st.button(f"✅ {t('btn_mark_sent').format(day)}", key=f"log_dt_{day}_{lead_id}"):
                    if lead['status'] == 'Nouveau':
                        db.update_lead(lead['id'], {**lead, 'status': 'Contacté'})
                    db.log_activity(user["username"], lead['id'], "WHATSAPP_SENT", f"Détail: Script {day}")
                    st.success(t("success_activity_logged")); st.rerun()

    with t3:
        if templates.empty:
            st.info(t("err_no_templates"))
        else:
            for cat in templates["category"].unique():
                st.markdown(f"**— {cat} —**")
                for _, tr in templates[templates["category"]==cat].iterrows():
                    with st.expander(f"📄 {tr['name']}"):
                        ft = inject_vars(tr["content"], lead.get("name",""), lead.get("goal",""),
                                        p_promo, prog_name, s_date)
                        
                        att = tr.get("attachment_url", "")
                        final_ft = ft
                        if att:
                            abs_url = get_absolute_url(att)
                            st.markdown(f"📎 **{t('script_attachment_associated')} :** [Ouvrir]({abs_url})")
                            final_ft += f"\n\n📎 {t('script_attachment')} : {abs_url}"
                            
                        st.markdown(f'<div class="script-card">{final_ft}</div>', unsafe_allow_html=True)
                        link = wa_link(lead.get("phone",""), final_ft)
                        st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="margin-top:10px;display:inline-flex;">📲 {t("btn_wa")}</a>',
                                    unsafe_allow_html=True)
                        tid = tr["id"]
                        st.text_area("📋", value=final_ft, height=120, key=f"t_{tid}_{lead_id}", label_visibility="collapsed")
                        if st.button(f"✅ {t('detail_btn_validate')}", key=f"log_tpl_{tid}_{lead_id}"):
                            if lead['status'] == 'Nouveau':
                                db.update_lead(lead['id'], {**lead, 'status': 'Contacté'})
                            db.log_activity(user["username"], lead['id'], "WHATSAPP_SENT", f"Détail: Tpl {tr['name']}")
                            st.success(t("success_activity_logged")); st.rerun()

    with t4:
        all_offers_e = db.get_offers()
        offer_labels_e = [t("field_offer_none")] + [f"{o['program_name']} ({o.get('price_promo','')})" for o in all_offers_e]
        offer_ids_e    = [None] + [o["id"] for o in all_offers_e]
        cur_offer_id = lead.get("offer_id")
        cur_offer_idx = next((i for i,oid in enumerate(offer_ids_e) if oid == cur_offer_id), 0)
        with st.form(f"edit_{lead_id}"):
            c1,c2 = st.columns(2)
            with c1:
                e_name   = st.text_input(t("field_name").replace(" *",""),  value=lead.get("name",""))
                e_phone  = st.text_input(t("field_phone").replace(" *",""), value=lead.get("phone",""))
                e_email  = st.text_input(t("field_email"),  value=lead.get("email","") or "")
                e_goal   = st.text_input(t("field_goal"),   value=lead.get("goal","") or "")
                sidx   = STATUSES.index(lead["status"]) if lead.get("status") in STATUSES else 0
                e_status = st.selectbox(t("detail_status_lbl"), STATUSES, index=sidx, 
                                        format_func=lambda x: f"{STATUS_EMOJI.get(x,'')} {t(STATUS_KEYS.get(x,x))}")
                e_amount = st.number_input(t("detail_amount"), value=float(lead.get("amount_paid") or 0), step=5000.0)
            with c2:
                pidx  = PROFILE_TYPES.index(lead["profile_type"]) if lead.get("profile_type") in PROFILE_TYPES else 0
                e_ptype = st.selectbox(t("field_profile"),  PROFILE_TYPES, index=pidx, format_func=lambda x: t(PROFILE_KEYS.get(x,x)))
                uidx  = URGENCY_TYPES.index(lead["urgency"]) if lead.get("urgency") in URGENCY_TYPES else 0
                e_urg   = st.selectbox(t("field_urgency"), URGENCY_TYPES, index=uidx, format_func=lambda x: t(URGENCY_KEYS.get(x,x)))

                e_bconf = st.checkbox(t("field_budget"),    value=bool(lead.get("budget_confirmed")))
                e_avail = st.checkbox(t("field_available"), value=bool(lead.get("available")))
                e_fast  = st.checkbox(t("field_fast"),      value=bool(lead.get("fast_response")))
                efd = date.today()
                if lead.get("follow_up_date"):
                    try:
                        parsed_date = date.fromisoformat(str(lead["follow_up_date"]))
                        if parsed_date >= date.today(): efd = parsed_date
                    except: pass
                e_fu_date = st.date_input(t("field_followup_date"), value=efd, min_value=date.today(), format="DD/MM/YYYY")
            e_offer_idx = st.selectbox(t("field_offer"), range(len(offer_labels_e)), index=cur_offer_idx, format_func=lambda i: offer_labels_e[i])
            m1,m2,m3 = st.columns(3)
            with m1: e_camp = st.text_input(t("field_campaign"), value=lead.get("campaign","") or "")
            with m2: e_adst = st.text_input(t("field_adset"),    value=lead.get("adset","") or "")
            with m3: e_crea = st.text_input(t("field_creative"), value=lead.get("creative","") or "")
            if user["role"] == "admin":
                agents = db.get_sales_agents(); albls = [f"{fn} ({un})" for un,fn in agents]
                acur = lead.get("assigned_to",""); acidx = next((i for i,(un,_) in enumerate(agents) if un==acur),0)
                e_aidx = st.selectbox(t("field_assign"), range(len(albls)), index=acidx, format_func=lambda i: albls[i])
                e_ato  = agents[e_aidx][0]
            else:
                e_ato = lead["assigned_to"]
            e_notes = st.text_area(t("field_notes"), value=lead.get("notes","") or "")
            e_save  = st.form_submit_button(t("btn_update"), use_container_width=True, type="primary")
        if e_save:
            e_offer_id = offer_ids_e[e_offer_idx]
            db.update_lead(lead_id, {"name":e_name,"phone":e_phone,"email":e_email,"assigned_to":e_ato,
                "status":e_status,"goal":e_goal,"profile_type":e_ptype,"urgency":e_urg,
                "budget_confirmed":int(e_bconf),"available":int(e_avail),"fast_response":int(e_fast),
                "amount_paid":e_amount,"campaign":e_camp,"adset":e_adst,"creative":e_crea,
                "notes":e_notes,"last_contact":str(date.today()),
                "follow_up_date":str(e_fu_date) if e_fu_date else "",
                "offer_id": e_offer_id})
            db.log_activity(user["username"], lead_id, "UPDATED", f"Statut → {e_status}")
            st.success(t("detail_updated")); st.rerun()
        if user["role"] == "admin":
            st.markdown("---")
            if st.button(t("detail_btn_delete")):
                db.delete_lead(lead_id); db.log_activity(user["username"], lead_id, "DELETED", "")
                st.session_state.selected_lead = None; st.rerun()

    with t5:
        st.markdown(f"**🧾 {t('detail_docs_generated')}**")
        invoices = db.get_lead_invoices(lead_id)
        if not invoices:
            st.info(t("detail_no_docs"))
        else:
            for inv in invoices:
                with st.container():
                    st.markdown(f"""
                    <div style="background:var(--surface2); border:1px solid var(--border); border-radius:10px; padding:15px; margin-bottom:10px;">
                        <div style="font-weight:700; color:var(--text); margin-bottom:5px;">📄 {inv['invoice_number']}</div>
                        <div style="font-size:0.85rem; color:var(--text-muted); margin-bottom:10px;">
                            {t('detail_doc_amount')} : {inv['total_amount']} | Date : {inv['created_at'].strftime('%d/%m/%Y')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"[📥 {t('detail_btn_download')}]({inv['pdf_url']})")
                    with c2:
                        wa_msg = t("wa_invoice_msg").format(lead['name'], inv['pdf_url'])
                        link = wa_link(lead.get("phone",""), wa_msg)
                        st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="padding:6px 12px; font-size:0.8rem;">📲 {t("detail_btn_share_wa")}</a>', unsafe_allow_html=True)
                st.markdown("---")




# ── BULK MESSAGING ────────────────────────────────────────────────────────────

def page_bulk_messaging(user: dict):
    topbar(user)
    st.markdown(f'<div class="section-header"><span class="accent">🚀</span> {t("bulk_header")}</div>',
                unsafe_allow_html=True)
    
    is_admin = user["role"] == "admin"
    leads_df = db.get_leads(assigned_to=None if is_admin else user["username"])
    
    if leads_df.empty:
        st.info(t("bulk_no_leads")); return

    # Filters
    st.markdown(t("bulk_step1"))
    c1, c2 = st.columns(2)
    with c1:
        f_status = st.multiselect(t("bulk_filter_status"), STATUSES, default=["Nouveau", "Relance"],
                                 format_func=lambda x: f"{STATUS_EMOJI.get(x,'')} {t(STATUS_KEYS.get(x,x))}")
    with c2:
        f_temp   = st.multiselect(t("bulk_filter_temp"), [t("temp_hot"), t("temp_warm"), t("temp_cold")], 
                                  default=[t("temp_hot"), t("temp_warm")])

    
    filtered_df = leads_df.copy()
    if f_status:
        filtered_df = filtered_df[filtered_df["status"].isin(f_status)]
    if f_temp:
        filtered_df = filtered_df[filtered_df["temperature"].isin(f_temp)]
        
    st.info(t("bulk_count").format(len(filtered_df)))
    
    if filtered_df.empty:
        st.warning(t("bulk_no_match")); return

    # Template selection
    st.markdown("---")
    st.markdown(t("bulk_step2"))
    
    scripts = db.get_scripts()
    tpls = db.get_script_templates()
    
    all_templates = {}
    for day in ["J1", "J3", "J5", "J7"]:
        s = scripts.get(day)
        if s: all_templates[f"📜 {s['title']}"] = {"content": s["content"], "attachment": s.get("attachment_url", "")}
            
    for _, t_item in tpls.iterrows():
        all_templates[f"📚 {t_item['category']} : {t_item['name']}"] = {"content": t_item["content"], "attachment": t_item.get("attachment_url", "")}
        
    sel_tpl_name = st.selectbox(t("bulk_template"), list(all_templates.keys()))
    sel_tpl_data = all_templates[sel_tpl_name]
    sel_tpl_content = sel_tpl_data["content"]
    att = sel_tpl_data["attachment"]
    
    cfg = db.get_config()

    st.markdown("---")
    st.markdown(t("bulk_step3"))
    
    # Session state for stabilization
    if "bulk_leads_ids" not in st.session_state:
        st.session_state.bulk_leads_ids = []
    if "bulk_idx" not in st.session_state:
        st.session_state.bulk_idx = 0

    # Detect mismatch between filters and loaded list
    current_filter_ids = filtered_df["id"].tolist()
    mismatch = st.session_state.bulk_leads_ids != current_filter_ids
    
    if mismatch and st.session_state.bulk_leads_ids:
        st.warning(t("bulk_mismatch").format(len(current_filter_ids), len(st.session_state.bulk_leads_ids)))

    if not st.session_state.bulk_leads_ids or st.button(t("bulk_reload"), type="primary" if mismatch else "secondary"):
        st.session_state.bulk_leads_ids = current_filter_ids
        st.session_state.bulk_idx = 0
        st.rerun()

    total_leads = len(st.session_state.bulk_leads_ids)
    
    if st.session_state.bulk_idx < total_leads:
        current_id = st.session_state.bulk_leads_ids[st.session_state.bulk_idx]
        lead_data = db.get_lead(current_id)
        
        if not lead_data:
            st.session_state.bulk_idx += 1; st.rerun()

        # Prepare message with Offer/Config fallback
        prog_name = cfg.get("program_name", "")
        p_promo   = cfg.get("price_promo", "")
        s_date    = cfg.get("start_date", "")
        if lead_data.get("offer_id"):
            off_d = db.get_offer(lead_data["offer_id"])
            if off_d:
                prog_name = off_d.get("program_name", prog_name)
                p_promo   = off_d.get("price_promo", p_promo)
                s_date    = off_d.get("start_date", s_date)

        filled = inject_vars(sel_tpl_content, str(lead_data["name"]), str(lead_data.get("goal","")),
                             p_promo, prog_name, s_date)
        
        final_filled = filled
        if att:
            abs_url = get_absolute_url(att)
            final_filled += f"\n\n📎 {t('script_attachment')} : {abs_url}"
            
        st.markdown(f"""
        <div style="background:var(--surface2); padding: 20px; border-radius: 12px; border: 1px solid var(--purple); margin-bottom: 10px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: var(--purple-light);">
                {t('bulk_lead_info').format(st.session_state.bulk_idx + 1, total_leads, lead_data['name'])}
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">
                📞 {lead_data['phone']} | {t('col_status')}: {lead_data['status']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if att:
            st.info(f"📎 {t('bulk_attachment')}")
            
        final_filled_html = final_filled.replace("\n", "<br>")
        st.markdown(f'<div class="script-card">{final_filled_html}</div>', unsafe_allow_html=True)
        
        link = wa_link(str(lead_data["phone"]), final_filled)
        st.markdown(f'<a href="{link}" target="_blank" class="wa-btn" style="width: 100%; justify-content: center; text-align: center; margin-bottom: 10px;">{t("bulk_wa_btn")}</a>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button(t("bulk_confirm"), use_container_width=True, type="primary"):
                # Mark as contacted and Log
                if lead_data['status'] == t('status_new'):
                    db.update_lead(current_id, {**lead_data, 'status': t('status_contacted')})
                db.log_activity(user["username"], current_id, "WHATSAPP_SENT", f"Bulk: {sel_tpl_name}")
                st.session_state.bulk_idx += 1; st.rerun()
        
        with c2:
            if st.button(t("bulk_skip"), use_container_width=True):
                st.session_state.bulk_idx += 1; st.rerun()
                
        st.caption(t("bulk_caption"))
    else:
        st.balloons()
        st.success(t("bulk_done").format(total_leads))
        if st.button(t("bulk_restart")):
            st.session_state.bulk_leads_ids = []; st.session_state.bulk_idx = 0; st.rerun()




# ── ANALYTICS ─────────────────────────────────────────────────────────────────

def page_analytics(user: dict):
    topbar(user)
    st.markdown(f'<div class="section-header"><span class="accent">▶</span> {t("analytics_header")}</div>',
                unsafe_allow_html=True)
    is_admin = user["role"] == "admin"

    # ── Commission badge
    if is_admin:
        stats = db.get_team_stats()
        total_comm = float(stats["commission"].sum()) if not stats.empty else 0.0
        comm_label = t("analytics_comm_team")
        df = db.get_leads()
    else:
        total_comm = db.get_agent_commission(user["username"])
        comm_label = t("analytics_comm_mine").format(user['full_name'])
        df = db.get_leads(assigned_to=user["username"])

    st.markdown(f"""
    <div class="commission-badge" style="margin-bottom:1.5rem;">
      <div class="commission-label">{comm_label}</div>
      <div class="commission-amount">{int(total_comm):,} FCFA</div>
    </div>""", unsafe_allow_html=True)

    if is_admin:
        tops = db.get_weekly_kpis()
        tc = st.columns(3)
        if tops["closer"]:
            with tc[0]:
                agent_name = tops["closer"]["agent"].title()
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">🏆</div>
                  <div class="top-closer-text">
                    <strong>{t('dash_top_closer')} : {agent_name} 🔥</strong>
                    <span>{int(tops["closer"]["val"]*100)}% {t('dash_conv_rate')}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        if tops["contacts"]:
            with tc[1]:
                agent_name = tops["contacts"]["agent"].title()
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">📞</div>
                  <div class="top-closer-text">
                    <strong>{t('dash_top_prospe')} : {agent_name}</strong>
                    <span>{int(tops["contacts"]["val"])} {t('dash_leads_contacted')}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        if tops["commission"]:
            with tc[2]:
                agent_name = tops["commission"]["agent"].title()
                st.markdown(f"""
                <div class="top-closer-banner">
                  <div class="top-closer-icon">💰</div>
                  <div class="top-closer-text">
                    <strong>{t('dash_top_comm')} : {agent_name}</strong>
                    <span>{int(tops["commission"]["val"]):,} {t('dash_fcfa_earned')}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    if df.empty:
        st.info(t("analytics_no_data")); return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(t("analytics_funnel"))
        funnel = db.get_funnel_stats(assigned_to=None if is_admin else user["username"])
        if not funnel.empty:
            st.altair_chart(purple_chart(funnel, "status", "count"), use_container_width=True)

    with c2:
        st.markdown(t("analytics_temp"))
        temp_df = df.groupby("temperature").size().reset_index(name="count")
        if not temp_df.empty:
            st.altair_chart(purple_chart(temp_df, "temperature", "count"), use_container_width=True)

    if is_admin:
        st.markdown("---")
        st.markdown(t("analytics_roas"))
        roas = db.get_roas_by_creative()
        if not roas.empty:
            st.dataframe(roas, use_container_width=True, hide_index=True)
        else:
            st.info(t("analytics_no_roas"))

        st.markdown("---")
        st.markdown(t("analytics_agents"))
        if not stats.empty:
            disp = stats.rename(columns={"agent":t("col_agent"),"total_leads":t("col_total_leads"),"closed":t("col_closed"),
                                          "lost":t("col_lost"),"revenue":t("col_revenue"),
                                          "commission":t("col_commission"),"conversion_rate":t("col_conv")})
            st.dataframe(disp, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown(t("analytics_scores"))
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
    st.markdown(f'<div class="section-header"><span class="accent">▶</span> {t("resources_header")}</div>',
                unsafe_allow_html=True)

    sections = db.get_kit_sections()
    videos   = db.get_videos()

    # Build dynamic tabs: sections + videos tab
    tab_labels = [f"{s['icon']} {s['title']}" for s in sections] + [t("resources_videos_tab")]
    tabs = st.tabs(tab_labels)

    # Kit content sections
    for tab, section in zip(tabs[:-1], sections):
        with tab:
            st.markdown(section["content"])
            with st.expander(t("resources_raw")):
                st.text_area("", value=section["content"], height=250,
                             key=f"raw_{section['section_key']}", label_visibility="collapsed")

    # Videos tab
    with tabs[-1]:
        st.markdown(t("resources_video_intro"))
        if not videos:
            st.info(t("resources_no_video"))
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


    t_offers,t1,t2,t3,t4,t5,t6,t7,t8,t_sys = st.tabs([
        t("cockpit_tab_offers"), t("cockpit_tab_config"),
        t("cockpit_tab_scripts"), t("cockpit_tab_templates"),
        t("cockpit_tab_kit"), t("cockpit_tab_videos"),
        t("cockpit_tab_agents"), t("cockpit_tab_leaderboard"), t("cockpit_tab_invoices"),
        "🛠️ Système"
    ])

    cfg = db.get_config()

    # ── Offers CRUD
    with t_offers:
        st.markdown(f"#### {t('offers_add_title')}")
        with st.form("new_offer_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                n_prog  = st.text_input(t("offers_field_prog"),       placeholder="Community Manager Augmenté")
                n_start = st.text_input(t("offers_field_start"),      placeholder="18 Avril 2026")
                n_promo = st.text_input(t("offers_field_promo"),      placeholder="75 000 FCFA")
            with c2:
                n_std   = st.text_input(t("offers_field_std"),        placeholder="100 000 FCFA")
                n_comm  = st.number_input(t("offers_field_commission"), value=10.0, step=0.5, min_value=0.0, max_value=100.0)
                n_active= st.checkbox(t("offers_active"), value=True)
            add_offer_btn = st.form_submit_button(t("offers_btn_add"), type="primary", use_container_width=True)
        if add_offer_btn:
            if not n_prog:
                st.error(t("offers_err_prog"))
            else:
                db.add_offer({"program_name": n_prog, "start_date": n_start,
                              "price_promo": n_promo, "price_standard": n_std,
                              "commission_rate": n_comm, "is_active": n_active})
                st.success(t("offers_success_add")); st.rerun()

        st.markdown("---")
        st.markdown(t("offers_list_title"))
        existing_offers = db.get_offers()
        if not existing_offers:
            st.info(t("offers_no_offers"))
        else:
            for off in existing_offers:
                status_lbl = t("offers_active") if off.get("is_active") else t("offers_inactive")
                with st.expander(f"{status_lbl} — {off['program_name']} | {off.get('price_promo','—')} | {off.get('commission_rate',10)}%"):
                    ea, eb = st.columns([4, 1])
                    with ea:
                        with st.form(f"edit_offer_{off['id']}"):
                            ep = st.text_input(t("offers_field_prog"),        value=off.get("program_name",""),  key=f"op_{off['id']}")
                            es = st.text_input(t("offers_field_start"),        value=off.get("start_date",""),    key=f"os_{off['id']}")
                            epp= st.text_input(t("offers_field_promo"),        value=off.get("price_promo",""),   key=f"opp_{off['id']}")
                            est= st.text_input(t("offers_field_std"),           value=off.get("price_standard",""),key=f"ost_{off['id']}")
                            ec = st.number_input(t("offers_field_commission"),  value=float(off.get("commission_rate",10)), step=0.5, min_value=0.0, max_value=100.0, key=f"oc_{off['id']}")
                            ea2= st.checkbox(t("offers_active") if not off.get("is_active") else t("offers_toggle_active"),
                                             value=bool(off.get("is_active")), key=f"oa_{off['id']}")
                            sv_o = st.form_submit_button(t("offers_btn_save"), use_container_width=True)
                        if sv_o:
                            db.update_offer(int(off["id"]), {"program_name": ep, "start_date": es,
                                "price_promo": epp, "price_standard": est,
                                "commission_rate": ec, "is_active": ea2})
                            st.success(t("offers_success_update")); st.rerun()
                    with eb:
                        if st.button(t("offers_btn_delete"), key=f"del_off_{off['id']}"):
                            db.delete_offer(int(off["id"]))
                            st.success(t("offers_success_delete")); st.rerun()

    # ── Global Config (default values when no offer is assigned)
    with t1:
        with st.form("cfg"):
            pn  = st.text_input(t("config_prog"),        value=cfg.get("program_name",""))
            sd  = st.text_input(t("config_start"),       value=cfg.get("start_date",""))
            pp  = st.text_input(t("config_promo"),       value=cfg.get("price_promo",""))
            ps  = st.text_input(t("config_std"),         value=cfg.get("price_standard",""))
            cr  = st.text_input(t("config_commission"),  value=cfg.get("commission_rate","10"))
            sav = st.form_submit_button(t("btn_save"), type="primary", use_container_width=True)
        if sav:
            for k,v in [("program_name",pn),("start_date",sd),("price_promo",pp),
                        ("price_standard",ps),("commission_rate",cr)]: db.update_config(k,v)
            st.success(t("config_success")); st.rerun()


    # ── Scripts J1-J7
    with t2:
        sc = db.get_scripts()
        for day in ["J1","J3","J5","J7"]:
            d_item = sc.get(day,{})
            with st.expander(f"**{day}** — {d_item.get('title','')}"):
                with st.form(f"sc_{day}", clear_on_submit=False):
                    nt = st.text_input(t("scripts_title"),    value=d_item.get("title",""), key=f"t_{day}")
                    nc = st.text_area(t("scripts_content"),   value=d_item.get("content",""), height=250, key=f"c_{day}", 
                                      help="💡 WhatsApp : *Gras*, _Italique_, ~Barré~, ```Code```")
                    
                    up_s = st.file_uploader(t("scripts_attachment"), type=["pdf","jpg","jpeg","png","mp3","mp4"], key=f"fup_{day}")
                    na = st.text_input(t("scripts_ext_link"), value=d_item.get("attachment_url",""), key=f"a_{day}")
                    
                    sv = st.form_submit_button(t("scripts_btn_save").format(day), use_container_width=True)
                
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
        with st.expander(t("tpl_add_title"), expanded=False):
            with st.form("add_tpl_new", clear_on_submit=True):
                tn  = st.text_input(t("tpl_name"))
                tc_ = st.selectbox(t("tpl_category"), SCRIPT_CATEGORIES)
                tco = st.text_area(t("tpl_content"), height=200, help="💡 WhatsApp : *Gras*, _Italique_, ~Barré~")
                up_new = st.file_uploader(t("tpl_attachment"), type=["pdf","jpg","jpeg","png","mp3","mp4"])
                tau = st.text_input(t("tpl_ext_link"))
                atb = st.form_submit_button(t("tpl_btn_add"), type="primary", use_container_width=True)
            
            if atb:
                final_url = tau
                if up_new:
                    path_new = save_uploaded_file(up_new)
                    if path_new: final_url = path_new
                
                if tn and tco:
                    db.add_script_template(tn, tc_, tco, user["username"], final_url)
                    st.success(t("tpl_added")); st.rerun()
                else:
                    st.error(t("tpl_err"))

        tpls = db.get_script_templates()
        if tpls.empty:
            st.info(t("tpl_no_tpl"))
        else:
            for _, tr_item in tpls.iterrows():
                with st.expander(f"📄 {tr_item['name']} — {tr_item['category']}"):
                    ca, cb = st.columns([3, 1])
                    with ca:
                        with st.form(f"etpl_form_{tr_item['id']}"):
                            en = st.text_input(t("tpl_name"),      value=tr_item["name"],     key=f"en_{tr_item['id']}")
                            ec = st.selectbox(t("tpl_category"), SCRIPT_CATEGORIES,
                                             index=SCRIPT_CATEGORIES.index(tr_item["category"]) if tr_item["category"] in SCRIPT_CATEGORIES else 0,
                                             key=f"ec_{tr_item['id']}")
                            eco= st.text_area(t("tpl_content"),   value=tr_item["content"],  height=180, key=f"eco_{tr_item['id']}")
                            
                            up_e = st.file_uploader(t("scripts_attachment"), type=["pdf","jpg","jpeg","png","mp3","mp4"], key=f"up_e_{tr_item['id']}")
                            eau= st.text_input(t("tpl_ext_curr"), value=tr_item.get("attachment_url",""), key=f"eau_{tr_item['id']}")
                            
                            sv_tpl = st.form_submit_button(t("tpl_btn_edit"), use_container_width=True)
                        
                        if sv_tpl:
                            final_url = eau
                            if up_e:
                                path_e = save_uploaded_file(up_e)
                                if path_e: final_url = path_e
                            
                            db.update_script_template(int(tr_item["id"]), en, ec, eco, final_url)
                            st.success(t("tpl_saved")); st.rerun()
                    with cb:
                        st.markdown(f"*{t('tpl_by').format(tr_item.get('created_by','—'))}*")
                        if st.button(t("tpl_btn_delete"), key=f"dt_{tr_item['id']}"):
                            db.delete_script_template(int(tr_item["id"])); st.rerun()

    # ── Kit sections editor
    with t4:
        st.markdown(t("kit_intro"))
        sections = db.get_kit_sections()
        for sec in sections:
            with st.expander(f"{sec['icon']} {sec['title']}"):
                with st.form(f"kit_{sec['section_key']}"):
                    icon_  = st.text_input(t("kit_icon"), value=sec["icon"], key=f"ki_{sec['section_key']}")
                    title_ = st.text_input(t("kit_title_field"),       value=sec["title"], key=f"kt_{sec['section_key']}")
                    cont_  = st.text_area(t("kit_content"),   value=sec["content"],
                                         height=350, key=f"kc_{sec['section_key']}")
                    sv_kit = st.form_submit_button(t("kit_saved"), use_container_width=True)
                if sv_kit:
                    db.update_kit_section(sec["section_key"], title_, icon_, cont_)
                    st.success(t("kit_saved")); st.rerun()

    # ── Videos manager
    with t5:
        st.markdown(t("vid_manage"))
        with st.expander(t("vid_add"), expanded=False):
            with st.form("add_vid", clear_on_submit=True):
                vt  = st.text_input(t("vid_title"))
                vd  = st.text_input(t("vid_desc"))
                vu  = st.text_input(t("vid_url"))
                vo  = st.number_input(t("vid_order"), value=0, step=1)
                avb = st.form_submit_button(t("vid_btn_add"), type="primary", use_container_width=True)
            if avb:
                if vt and vu:
                    db.add_video(vt,vd,vu,int(vo),user["username"]); st.success(t("vid_added")); st.rerun()
                else: st.error(t("vid_err"))
        vids = db.get_videos()
        if not vids: st.info(t("vid_no_vid"))
        else:
            for v_item in vids:
                with st.expander(f"🎬 {v_item['title']}"):
                    embed_youtube(v_item["youtube_url"], height=250)
                    ca,cb = st.columns([3,1])
                    with ca:
                        with st.form(f"ev_{v_item['id']}"):
                            evt = st.text_input(t("vid_title"),       value=v_item["title"],       key=f"vt_{v_item['id']}")
                            evd = st.text_input(t("vid_desc"), value=v_item["description"], key=f"vd_{v_item['id']}")
                            evu = st.text_input(t("vid_url"),         value=v_item["youtube_url"], key=f"vu_{v_item['id']}")
                            evo = st.number_input(t("vid_order"),     value=int(v_item["order_idx"]), step=1, key=f"vo_{v_item['id']}")
                            svv = st.form_submit_button(t("tpl_btn_edit"), use_container_width=True)
                        if svv: db.update_video(int(v_item['id']),evt,evd,evu,int(evo)); st.success("✅"); st.rerun()
                    with cb:
                        if st.button(t("vid_btn_delete"), key=f"dv_{v_item['id']}"):
                            db.delete_video(int(v_item["id"])); st.rerun()


    # ── Agents
    with t6:
        users_df = db.get_all_users()
        if not users_df.empty:
            st.dataframe(users_df.rename(columns={"id":"ID","username":t("agents_username"),
                "full_name":t("agents_full_name"),"role":t("agents_role"),"active":t("status_active"),"created_at":t("col_created")}),
                use_container_width=True, hide_index=True)
        st.markdown("---")
        ca_ag, cb_ag = st.columns(2)
        with ca_ag:
            st.markdown(t("agents_create"))
            with st.form("new_user", clear_on_submit=True):
                fn = st.text_input(t("agents_full_name"),  placeholder="Paul Dupont")
                un = st.text_input(t("agents_username"),  placeholder="paul")
                pw = st.text_input(t("agents_password"), type="password")
                rl = st.selectbox(t("agents_role"), ["sales","admin"])
                cr_btn= st.form_submit_button(t("agents_btn_create"), type="primary", use_container_width=True)
            if cr_btn:
                if fn and un and pw:
                    ok = db.create_user(un,pw,rl,fn)
                    if ok: st.success(t("agents_created").format(fn)); st.rerun()
                    else: st.error(t("agents_dup").format(un))
                else: st.error(t("agents_all_required"))
        with cb_ag:
            st.markdown(t("agents_reset_pwd"))
            if not users_df.empty:
                with st.form("pwd_reset", clear_on_submit=True):
                    uid_map = {f"{r['full_name']} ({r['username']})": r["id"] for _,r in users_df.iterrows()}
                    sel_u   = st.selectbox(t("col_agent"), list(uid_map.keys()))
                    npw     = st.text_input(t("agents_new_pwd"), type="password")
                    rb_btn  = st.form_submit_button(t("agents_btn_reset"), use_container_width=True)
                if rb_btn:
                    if npw: db.reset_user_password(uid_map[sel_u],npw); st.success(t("agents_pwd_reset"))
                    else: st.error(t("agents_pwd_empty"))
        st.markdown("---")
        st.markdown(t("agents_toggle"))
        if not users_df.empty:
            for _,row_ag in users_df.iterrows():
                cn_ag, cb2_ag = st.columns([3,1])
                with cn_ag: st.markdown(f"{'🟢' if row_ag['active'] else '🔴'} **{row_ag['full_name']}** (`{row_ag['username']}`) — {row_ag['role']}")
                with cb2_ag:
                    lbl_ag = t("agents_deactivate") if row_ag["active"] else t("agents_activate")
                    if st.button(lbl_ag, key=f"tog_{row_ag['id']}"): db.update_user_status(int(row_ag['id']), not bool(row_ag['active'])); st.rerun()


    # ── Leaderboard & Export
    with t7:
        st.markdown(t("lb_title"))
        stats_lb = db.get_team_stats()
        tops_lb = db.get_weekly_kpis()
        top_c_lb = tops_lb["closer"]["agent"] if tops_lb["closer"] else ""
        if stats_lb.empty:
            st.info(t("lb_no_data"))
        else:
            stats_lb = stats_lb.sort_values("conversion_rate",ascending=False).reset_index(drop=True)
            for i_lb, row_lb in stats_lb.iterrows():
                rank_lb = ["🥇","🥈","🥉"][i_lb] if i_lb < 3 else f"#{i_lb+1}"
                is_t_lb = row_lb["agent"] == top_c_lb
                st.markdown(f"""
                <div class="leaderboard-row" style="{'border-color:var(--purple);' if is_t_lb else ''}">
                  <div class="leaderboard-rank">{rank_lb}</div>
                  <div class="leaderboard-name">{row_lb['agent'].title()}{'&nbsp;🔥' if is_t_lb else ''}</div>
                  <div class="leaderboard-stat">
                    <div style="color:var(--purple-light);font-weight:700;">{int(row_lb.get('conversion_rate',0))}% {t('lb_conv')}</div>
                    <div style="color:var(--green);">{int(row_lb.get('commission',0)):,}&nbsp;{t('lb_commission')}</div>
                    <div>{int(row_lb.get('closed',0))} / {int(row_lb.get('total_leads',0))}&nbsp;{t('lb_leads')}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(t("lb_export"))
        all_df_lb = db.get_leads()
        st.write(t("lb_leads_in_db").format(len(all_df_lb)))
        if not all_df_lb.empty:
            xlsx_lb = db.export_leads_excel()
            st.download_button(t("lb_dl_excel"), data=xlsx_lb,
                file_name=f"smix_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary", use_container_width=True)

    # ── Invoices Tab
    with t8:
        st.markdown(t("inv_generate"))
        leads_inv = db.get_leads()
        if leads_inv.empty:
            st.info(t("inv_no_lead"))
        else:
            with st.form("new_invoice", clear_on_submit=True):
                lead_options = {f"{r_i['name']} ({r_i['phone']})": r_i["id"] for _, r_i in leads_inv.iterrows()}
                sel_lead_label = st.selectbox(t("inv_select_lead"), list(lead_options.keys()))
                inv_num = st.text_input(t("inv_number"), value=db.get_next_invoice_number())
                
                st.markdown("---")
                st.markdown(t("inv_items"))
                item_desc = st.text_input(t("inv_desc"), value="Bootcamp Community Manager Augmenté")
                item_qty = st.number_input(t("inv_qty"), min_value=1, value=1)
                item_price = st.text_input(t("inv_price"), value=cfg.get("price_promo", "75 000 FCFA"))
                total_val = st.text_input(t("inv_total"), value=item_price)
                
                gen_btn = st.form_submit_button(t("inv_btn_gen"), type="primary", use_container_width=True)
            
            if gen_btn:
                sel_id_inv = lead_options[sel_lead_label]
                sel_lead_inv = next(r_ii for _, r_ii in leads_inv.iterrows() if r_ii["id"] == sel_id_inv)
                inv_data = {
                    "invoice_number": inv_num, "date": datetime.now().strftime("%d/%m/%Y"),
                    "client_name": sel_lead_inv["name"], "client_email": sel_lead_inv.get("email", ""),
                    "items": [{"desc": item_desc, "qty": item_qty, "price": item_price}],
                    "total": total_val
                }
                with st.spinner(t("inv_gen_spinner")):
                    pdf_bytes = ig.generate_invoice_pdf(inv_data)
                
                class BytesFile:
                    def __init__(self, b, name):
                        self.b = b; self.name = name
                    def getvalue(self): return self.b
                
                fake_file = BytesFile(pdf_bytes, f"{inv_num}.pdf")
                pdf_url = save_uploaded_file(fake_file)
                if pdf_url:
                    db.add_invoice(sel_id_inv, inv_num, f"{item_qty}x {item_desc}", total_val, pdf_url, user["username"])
                    
                    if sel_lead_inv["assigned_to"]:
                        db.add_notification(
                            sel_lead_inv["assigned_to"], 
                            f"🧾 {t('inv_success').format(inv_num)} - {sel_lead_inv['name']}.",
                            doc_type='invoice',
                            doc_id=sel_id_inv
                        )
                    
                    db.log_activity(user["username"], sel_id_inv, "INVOICE_CREATED", f"Facture {inv_num} générée.")
                    st.success(t("inv_success").format(inv_num))
                    st.markdown(t("inv_pdf_link").format(pdf_url))
    with t_sys:
        st.subheader("🛠️ Maintenance Système")
        st.warning("⚠️ Utilisez ces options uniquement en cas de problème technique avec la base de données.")
        if st.button("🔄 Forcer la synchronisation des tables (init_db)"):
            try:
                db.init_db()
                st.success("✅ Tables synchronisées avec succès ! Veuillez rafraîchir la page.")
            except Exception as e:
                st.error(f"❌ Erreur lors de la synchronisation : {e}")

    # ── Cockpit Tabs End



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
