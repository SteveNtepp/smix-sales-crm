import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import os
from sqlalchemy import create_engine
import hashlib
import urllib.parse
from datetime import datetime, date
import pandas as pd

@st.cache_resource
def parse_db_url():
    try:
        db_url = os.getenv("DB_URL") or st.secrets["DB_URL"]
    except KeyError:
        st.error("❌ Erreur de configuration : Clé 'DB_URL' manquante dans les Secrets Streamlit.")
        st.info("💡 Pour corriger : Allez dans 'Settings' > 'Secrets' sur Streamlit Cloud et ajoutez : `DB_URL = 'votre_url_supabase'`")
        st.stop()
        
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    # URL-encode the password automatically if it contains special chars like % or +
    try:
        parts = urllib.parse.urlsplit(db_url)
        if parts.password:
            safe_pwd = urllib.parse.quote(parts.password, safe='')
            # Reconstruct netloc with safely encoded password
            netloc = f"{parts.username}:{safe_pwd}@{parts.hostname}"
            if parts.port:
                netloc += f":{parts.port}"
            parts = parts._replace(netloc=netloc)
            db_url = urllib.parse.urlunsplit(parts)
    except Exception:
        pass
    
    return db_url

@st.cache_resource
def get_engine():
    return create_engine(parse_db_url())

def get_connection():
    conn = psycopg2.connect(parse_db_url(), cursor_factory=RealDictCursor)
    conn.autocommit = False
    return conn


def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def clear_cache():
    """Manually clear the cached data when a write operation occurs."""
    st.cache_data.clear()


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'sales',
            full_name  TEXT NOT NULL,
            active     BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    

    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            day     TEXT PRIMARY KEY,
            title   TEXT,
            content TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS script_templates (
            id         SERIAL PRIMARY KEY,
            name       TEXT NOT NULL,
            category   TEXT DEFAULT 'Personnalisé',
            content    TEXT NOT NULL,
            created_by TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kit_sections (
            id          SERIAL PRIMARY KEY,
            section_key TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            icon        TEXT DEFAULT '📄',
            content     TEXT NOT NULL,
            order_idx   INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id          SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            youtube_url TEXT UNIQUE NOT NULL,
            order_idx   INTEGER DEFAULT 0,
            created_by  TEXT DEFAULT 'admin',
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id               SERIAL PRIMARY KEY,
            name             TEXT NOT NULL,
            phone            TEXT,
            email            TEXT,
            assigned_to      TEXT,
            status           TEXT DEFAULT 'Nouveau',
            goal             TEXT,
            profile_type     TEXT,
            urgency          TEXT,
            budget_confirmed BOOLEAN DEFAULT false,
            available        BOOLEAN DEFAULT false,
            fast_response    BOOLEAN DEFAULT false,
            score            INTEGER DEFAULT 0,
            temperature      TEXT,
            campaign         TEXT,
            adset            TEXT,
            creative         TEXT,
            amount_paid      FLOAT DEFAULT 0,
            notes            TEXT,
            last_contact     TEXT,
            follow_up_date   TEXT,
            follow_up_day    INTEGER DEFAULT 0,
            created_at       TIMESTAMP DEFAULT NOW(),
            updated_at       TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id         SERIAL PRIMARY KEY,
            "user"       TEXT,
            lead_id    INTEGER,
            action     TEXT,
            detail     TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id             SERIAL PRIMARY KEY,
            lead_id        INTEGER REFERENCES leads(id) ON DELETE CASCADE,
            invoice_number TEXT UNIQUE NOT NULL,
            items          TEXT, -- Contenu textuel / JSON
            total_amount   TEXT,
            pdf_url        TEXT,
            created_by     TEXT,
            created_at     TIMESTAMP DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id           SERIAL PRIMARY KEY,
            recipient    TEXT NOT NULL, -- username
            message      TEXT NOT NULL,
            doc_type     TEXT, -- 'invoice', 'lead', etc.
            doc_id       INTEGER,
            is_read      BOOLEAN DEFAULT false,
            created_at   TIMESTAMP DEFAULT NOW()
        )
    """)

    # Schema Migrations
    try:
        c.execute("ALTER TABLE scripts ADD COLUMN IF NOT EXISTS attachment_url TEXT")
        c.execute("ALTER TABLE script_templates ADD COLUMN IF NOT EXISTS attachment_url TEXT")
        conn.commit()
    except Exception as e:
        conn.rollback()
        # Log error or ignore if columns already exist (though IF NOT EXISTS handles it)
        pass

    _seed_users(conn)
    _seed_config(conn)
    _seed_scripts(conn)
    _seed_kit(conn)
    _seed_videos(conn)
    conn.close()


# ── SEEDS ──────────────────────────────────────────────────────────────────────

def _seed_users(conn):
    c = conn.cursor()
    for u in [
        ("steve",    hash_password("smix2024"),  "admin", "Steve (Admin)"),
        ("alinne",   hash_password("alinne123"), "sales", "Alinne"),
        ("manuella", hash_password("manu123"),   "sales", "Manuella"),
    ]:
        c.execute("INSERT INTO users (username,password,role,full_name) VALUES (%s,%s,%s,%s) ON CONFLICT (username) DO NOTHING", u)
    conn.commit()


def _seed_config(conn):
    c = conn.cursor()
    for k, v in {
        "program_name":    "Community Manager Augmenté — Smix Academy",
        "start_date":      "18 Avril 2026",
        "price_promo":     "75 000 FCFA",
        "price_standard":  "100 000 FCFA",
        "commission_rate": "10",
    }.items():
        c.execute("INSERT INTO config(key,value) VALUES(%s,%s) ON CONFLICT (key) DO NOTHING", (k, v))
    conn.commit()


def _seed_scripts(conn):
    c = conn.cursor()
    scripts = [
        ("J1", "J+1 — Closing Soft (24h après premier contact)",
"""Bonjour [Prénom] 👋🏾
Je me permets de revenir vers toi concernant le bootcamp Community Manager Augmenté de Smix Academy.
Je voulais simplement savoir si tu avais pu voir mon précédent message 😊
Le programme a été pensé surtout pour les entrepreneurs et freelances qui veulent :
✅ mieux utiliser les réseaux pour leur activité
✅ créer plus vite avec l'IA
✅ comprendre Meta Ads
✅ automatiser certaines tâches
✅ mieux transformer leur visibilité en opportunités

👉 Dis-moi juste en une phrase : quel est ton objectif principal en ce moment avec le digital ?"""),

        ("J3", "J+3 — Orienté Valeur (Entrepreneur / Freelance)",
"""Bonjour [Prénom] 👋🏾
Je reviens vers toi parce qu'au vu de notre échange, je pense que Community Manager Augmenté peut vraiment t'aider si ton objectif est de [mieux vendre / gagner du temps / mieux communiquer / trouver plus de clients].

Beaucoup de personnes publient déjà sur les réseaux…
Mais très peu savent réellement comment :
• structurer une stratégie
• utiliser l'IA intelligemment
• lancer des campagnes Meta Ads
• automatiser certaines tâches
• transformer leur visibilité en résultats concrets

👉 C'est exactement ce qu'on travaille dans le programme.
📅 Début : 18 avril 2026
💸 Tarif de lancement : 75 000 FCFA (au lieu de 100 000 FCFA)

Si tu veux, je peux te dire en 2 minutes si le programme est vraiment adapté à ton profil."""),

        ("J5", "J+5 — Urgence Douce (Facilité de Paiement)",
"""Bonjour [Prénom] 👋🏾
Je te fais un petit rappel au sujet de Community Manager Augmenté.

📅 La cohorte démarre le 18 avril 2026
💸 Le tarif de lancement est actuellement à 75 000 FCFA au lieu de 100 000 FCFA
💳 Paiement possible en 2 tranches

Si ton objectif est de :
• mieux communiquer pour ton activité
• gagner du temps avec l'IA
• apprendre Meta Ads
• automatiser certaines tâches
• ou monétiser une compétence digitale

... alors c'est clairement une cohorte à considérer sérieusement.

👉 Souhaites-tu que je t'envoie le numéro de paiement, ou préfères-tu d'abord un appel rapide ?"""),

        ("J7", "J+7 — Dernier Rappel / Closing Final",
"""Bonjour [Prénom] 👋🏾
Ceci est mon dernier message concernant Community Manager Augmenté 😊

Je reviens vers toi une dernière fois parce que je pense sincèrement que ce programme peut être utile si tu veux :
• mieux structurer ta communication
• mieux utiliser l'IA
• gagner du temps
• mieux vendre en ligne
• ou développer une compétence monétisable

👉 Parfois, le vrai coût n'est pas le prix d'une formation...
C'est surtout de continuer plusieurs mois sans méthode claire ni système efficace.
📅 Début : 18 avril 2026
💸 Prix de lancement : 75 000 FCFA
💳 Paiement possible en 2 tranches

Si tu veux réserver ta place, je peux t'accompagner maintenant.
Sinon aucun souci, je resterai disponible pour la prochaine cohorte 🙏🏾"""),
    ]
    for s in scripts:
        c.execute("INSERT INTO scripts(day,title,content) VALUES(%s,%s,%s) ON CONFLICT (day) DO UPDATE SET title=EXCLUDED.title, content=EXCLUDED.content", s)
    conn.commit()


def _seed_kit(conn):
    c = conn.cursor()
    sections = [
        ("script_appel", "Script d'Appel", "📞", 0, """**SCRIPT D'APPEL (5 à 8 minutes max)**

> Remarques importantes :
> - Si le prospect est tiède/chaud, privilégier un appel court
> - Délai de rappel critique sur Meta : < 5 min pour lead chaud, < 30 min sinon

---

**1. Introduction (30 sec)**

Bonjour [Prénom du prospect], c'est [Nom] de Smix Academy.
Tu avais demandé des infos sur Community Manager Augmenté.
Je t'appelle rapidement, l'idée n'est pas de te retenir longtemps : je veux juste voir si le programme est réellement pertinent pour toi avant de t'orienter. Ça te va ?

---

**2. Qualification (2 min)**

Questions à poser :
- Aujourd'hui, tu fais quoi exactement ? *(entrepreneur, freelance, CM, salarié...)*
- Quel est ton objectif principal sur les 3 à 6 prochains mois ? *(clients / visibilité / compétence / reconversion...)*
- Qu'est-ce qui te bloque aujourd'hui ? *(manque de méthode / temps / résultats / outils)*
- Tu as déjà essayé quoi jusqu'ici ? *(formations gratuites, tutos, pub, etc.)*

---

**3. Reformulation (1 min)**

"Si je résume : aujourd'hui tu veux [objectif], mais tu es freiné par [blocage]. Et tu cherches une solution concrète pour [résultat attendu]. C'est bien ça ?"

> Cette étape est fondamentale. Le prospect doit se sentir compris, pas "pitché".

---

**4. Pitch ciblé (2 min)**

"Dans ce cas, le CMA peut clairement être pertinent pour toi. Parce que le programme a été conçu pour des profils comme toi : principalement des entrepreneurs, freelances et prestataires digitaux qui veulent :
- mieux exploiter les réseaux sociaux
- gagner du temps avec l'IA
- comprendre Meta Ads
- automatiser une partie de leur activité
- mieux vendre ou monétiser leurs compétences"

Format : 10 semaines | 100% en ligne | 6 sem. intensives + 4 sem. d'incubation | Cas pratiques + accompagnement

---

**5. Offre & Urgence (1 min)**

- Cohorte démarre le 18 avril 2026
- Prix de lancement : 75 000 FCFA au lieu de 100 000 FCFA
- Paiement en 2 tranches possible (- 5 000 FCFA si paiement en 1 tranche)

"Est-ce que tu veux payer en 1 tranche ou en 2 tranches ?"

---

**SCRIPT DE CLOSING DIRECT (prospect chaud)**

"Franchement, au vu de ce que tu m'as dit, le vrai risque n'est pas d'entrer dans le programme.
Le vrai risque, c'est de rester encore quelques mois à publier / travailler / prospecter sans méthode claire.
Avec le CMA, tu repars avec : un cadre, des outils, une meilleure productivité, une compétence directement exploitable.
Si tu es d'accord, je t'envoie tout de suite les numéros de paiement mobile pour bloquer ta place." """),

        ("objections", "Objections & Réponses", "🛡️", 1, """**OBJECTIONS LES PLUS PROBABLES + RÉPONSES**

> Une objection n'est pas un refus. C'est souvent un besoin de réassurance.

---

**1. "C'est intéressant, mais je n'ai pas les moyens pour l'instant."**

Réponse : "Je comprends. C'est justement pour ça qu'on a rendu le programme plus accessible. 75 000 FCFA au lieu de 100 000 FCFA, avec paiement en 2 tranches. Est-ce que le frein principal, c'est vraiment le montant... ou plutôt le timing ?"

---

**2. "Je dois réfléchir."**

Réponse : "Bien sûr, c'est normal. Pour t'aider, dis-moi juste : qu'est-ce que tu veux valider avant de te décider ? (si le programme est adapté / si tu auras le temps / si l'investissement est rentable / autre chose ?)"

---

**3. "Je n'ai pas le temps."**

Réponse : "C'est justement le cas de beaucoup de nos apprenants. Le programme est pensé pour des personnes qui ont déjà une activité. L'objectif est de t'aider à gagner du temps, travailler plus intelligemment et automatiser certaines tâches."

---

**4. "Je suis débutant, je ne sais pas si c'est pour moi."**

Réponse : "Le programme reste accessible si tu es motivé et prêt à appliquer. Ce qui compte, c'est d'avoir un vrai objectif, une envie de monter en compétence et la volonté d'exécuter."

---

**5. "J'ai déjà suivi des formations, mais ça ne m'a pas servi."**

Réponse : "Je comprends totalement. CMA n'est pas une formation théorique. C'est un bootcamp pratique avec : cas concrets, logique d'exécution, outils actionnables, accompagnement, orientation résultats."

---

**6. "Je ne suis pas sûr que ça va me rapporter."**

Réponse : "CMA t'aide à acquérir des compétences avec 3 effets concrets : mieux communiquer pour ton business, mieux attirer des clients, monétiser une nouvelle compétence. Le programme donne des leviers. La rentabilité dépend de ton application."

---

**7. "Je ne maîtrise pas encore l'IA / les outils."**

Réponse : "Justement, tu n'es pas censé déjà maîtriser tout ça. Le programme est là pour te donner les bons outils, la bonne méthode, la bonne logique d'usage."

---

**8. "Je veux d'abord voir le programme détaillé."**

Réponse : "Bien sûr. Mais avant, pour t'éviter de perdre du temps, je préfère vérifier si c'est adapté à ton profil. En 1 phrase, ton objectif principal c'est quoi ?"

---

**9. "Je veux en parler à mon associé / conjoint / équipe."**

Réponse : "Très bonne démarche. Je peux t'envoyer un message récapitulatif clair à lui transférer, avec le prix, les objectifs et les bénéfices."

---

**10. "Je m'inscris plus tard / à la prochaine cohorte."**

Réponse : "C'est possible, mais 2 choses : le tarif actuel (75 000 FCFA) est exceptionnel, et le vrai coût c'est de rester encore plusieurs mois sans méthode. Si ton besoin est présent aujourd'hui, il peut être plus rentable d'agir maintenant." """),

        ("criteres", "Critères de Qualification", "✅", 2, """**CRITÈRES DE QUALIFICATION D'UN PROSPECT**

Logique en 3 niveaux : Lead froid | Lead tiède | Lead chaud

---

**A. PROFIL IDÉAL CMA — Au moins 4 critères sur 7**

1. **Profil cohérent** : entrepreneur, freelance, CM, assistant virtuel, créateur de contenu, prestataire digital, salarié en reconversion avec projet clair

2. **Besoin explicite** : gagner du temps / mieux communiquer / trouver des clients / structurer la stratégie / apprendre Meta Ads / automatiser / monétiser

3. **Urgence / temporalité** : veut agir dans les 30 jours / s'intéresse à la cohorte en cours

4. **Capacité financière** : peut payer immédiatement / en 2 tranches / cherche activement une solution de paiement

5. **Niveau d'engagement** : répond vite / pose des questions précises / demande le programme / accepte un appel

6. **Maturité de décision** : comprend que c'est un investissement / ne cherche pas juste du gratuit

7. **Disponibilité minimale** : peut suivre un programme 100% en ligne (PC + internet) / a un minimum de temps hebdomadaire

---

**B. SCORING /10**

| Critère | Points |
|---|---|
| Profil adapté | 0–2 |
| Besoin clair | 0–2 |
| Urgence | 0–2 |
| Capacité de paiement | 0–2 |
| Engagement / réactivité | 0–2 |

- **8 à 10 = Lead chaud** → Priorité absolue, appel / closing rapide
- **5 à 7 = Lead tiède** → Nurturing + relance + appel si possible
- **0 à 4 = Lead froid** → Automation / suivi léger / contenu de réchauffement

---

**Notre promesse**

"Nous ne vendons pas juste une formation en Community Management. Nous aidons les entrepreneurs et freelances à faire du digital un levier de croissance, de productivité et de revenus." """),

        ("questions", "Questions de Qualification", "❓", 3, """**QUESTIONS DE QUALIFICATION (VERSION COURTE)**

Les 5 meilleures questions à standardiser :

---

**Q1.** Tu es actuellement : entrepreneur, freelance, salarié ou étudiant ?

**Q2.** Quel est ton objectif principal en rejoignant ce programme ?

**Q3.** Quel est ton plus grand blocage aujourd'hui dans le digital ?

**Q4.** Tu cherches à te former pour ton activité actuelle ou pour vendre cette compétence ?

**Q5.** Si le programme te correspond, tu serais prêt à démarrer sur cette cohorte ?

---

**Règle d'or :** Écoute d'abord. Reformule ensuite. Pitch seulement après avoir compris le besoin réel.

Un bon pitch sans bonne qualification = perte de temps pour les deux parties. """),

        ("interdits", "Les Interdits", "🚫", 4, """**CE QU'IL FAUT ABSOLUMENT ÉVITER**

---

**❌ 1. Vendre trop tôt**

Ne pas envoyer programme, prix ou lien sans mini-diagnostic préalable.
> Toujours qualifier AVANT de pitcher.

---

**❌ 2. Parler comme si c'était "juste une formation"**

Toujours vendre :
- productivité
- structuration
- acquisition
- monétisation
- levier business

> Le CMA est un investissement dans une compétence exploitable, pas une dépense.

---

**❌ 3. Répondre aux objections de façon défensive**

Une objection = une demande de réassurance, pas une attaque.
> Reformuler, comprendre, puis répondre avec empathie.

---

**❌ 4. Ne pas relancer**

Le suivi est la clé du closing.
> Un lead non relancé dans les délais est un lead perdu.

La séquence J1 → J3 → J5 → J7 doit être respectée STRICTEMENT.
Utilise les scripts de relance pour chaque étape. """),
    ]
    for key, title, icon, order, content in sections:
        c.execute("""
            INSERT INTO kit_sections (section_key, title, icon, content, order_idx)
            VALUES (%s, %s, %s, %s, %s) ON CONFLICT (section_key) DO NOTHING
        """, (key, title, icon, content, order))
    conn.commit()


def _seed_videos(conn):
    c = conn.cursor()
    videos = [
        ("Formation 1 — Community Manager Augmenté", "Introduction au programme CMA", "https://youtu.be/ZZ2mOsTRXJU?si=kngwJYrbpRhY88Do", 0),
        ("Formation 2 — Stratégie Réseaux Sociaux",  "Stratégie et création de contenu", "https://youtu.be/Jeu_Kcx3aQo?si=3ppxZREntVPpk9t1", 1),
        ("Formation 3 — Intelligence Artificielle",   "Utilisation de l'IA pour les CMs",  "https://youtu.be/kalJWpz0PcQ?si=_0Nf4QWazigUpNli", 2),
        ("Formation 4 — Meta Ads Fondamentaux",       "Bases des publicités Meta Ads",      "https://youtu.be/aGI7puAXf6w?si=pMNiIjvvo6nqZ2dK", 3),
        ("Formation 5 — Automatisation",              "Automatiser les tâches digitales",    "https://youtu.be/mt4AMRYTV3s?si=h7KUoJDBPSRCDy9b", 4),
        ("Formation 6 — Monétisation",                "Monétiser ses compétences digitales", "https://youtu.be/Gh6FnldzR_k?si=2Oa1CY2gV4vlJvQ2", 5),
    ]
    for title, desc, url, order in videos:
        c.execute("""
            INSERT INTO videos (title, description, youtube_url, order_idx)
            VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING
        """, (title, desc, url, order))
    conn.commit()


# ── AUTH ──────────────────────────────────────────────────────────────────────

def authenticate(username: str, password: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=%s AND password=%s AND active=true",
              (username, hash_password(password)))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

def get_all_users() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id", get_engine())
    conn.close()
    return df


def create_user(username: str, password: str, role: str, full_name: str) -> bool:
    clear_cache()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users(username,password,role,full_name) VALUES(%s,%s,%s,%s)",
                      (username.strip().lower(), hash_password(password), role, full_name.strip()))
        conn.commit()
        conn.close()
        return True
    except psycopg2.errors.UniqueViolation:
        return False


def update_user_status(user_id: int, active: bool):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET active=%s WHERE id=%s", (bool(active), user_id))
    conn.commit()
    conn.close()


def reset_user_password(user_id: int, new_password: str):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (hash_password(new_password), user_id))
    conn.commit()
    conn.close()


@st.cache_data
def get_sales_agents() -> list:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT username, full_name FROM users WHERE active=true ORDER BY full_name")
        rows = cur.fetchall()
    conn.close()
    return [(r["username"], r["full_name"]) for r in rows]


# ── CONFIG ────────────────────────────────────────────────────────────────────

@st.cache_data
def get_config() -> dict:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT key, value FROM config")
        rows = cur.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def update_config(key: str, value: str):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO config(key,value) VALUES(%s,%s) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))
    conn.commit()
    conn.close()


# ── SCRIPTS ───────────────────────────────────────────────────────────────────

@st.cache_data
def get_scripts() -> dict:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT day, title, content, attachment_url FROM scripts")
        rows = cur.fetchall()
    conn.close()
    return {r["day"]: {"title": r["title"], "content": r["content"], "attachment_url": r.get("attachment_url", "")} for r in rows}


def update_script(day: str, title: str, content: str, attachment_url: str = ""):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scripts(day,title,content,attachment_url) VALUES(%s,%s,%s,%s) 
            ON CONFLICT (day) DO UPDATE SET title=EXCLUDED.title, content=EXCLUDED.content, attachment_url=EXCLUDED.attachment_url
        """, (day, title, content, attachment_url))
    conn.commit()
    conn.close()


# ── SCRIPT TEMPLATES ──────────────────────────────────────────────────────────

@st.cache_data
def get_script_templates() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM script_templates ORDER BY created_at DESC", get_engine())
    conn.close()
    return df


def add_script_template(name: str, category: str, content: str, created_by: str, attachment_url: str = "") -> int:
    clear_cache()
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO script_templates(name,category,content,created_by,attachment_url) VALUES(%s,%s,%s,%s,%s) RETURNING id",
              (name, category, content, created_by, attachment_url))
    tid = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return tid


def update_script_template(tid: int, name: str, category: str, content: str, attachment_url: str = ""):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE script_templates SET name=%s,category=%s,content=%s,attachment_url=%s WHERE id=%s",
                     (name, category, content, attachment_url, tid))
    conn.commit()
    conn.close()


def delete_script_template(tid: int):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM script_templates WHERE id=%s", (tid,))
    conn.commit()
    conn.close()


# ── KIT SECTIONS ──────────────────────────────────────────────────────────────

@st.cache_data
def get_kit_sections() -> list:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM kit_sections ORDER BY order_idx")
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_kit_section(section_key: str, title: str, icon: str, content: str):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO kit_sections (section_key, title, icon, content, order_idx)
            VALUES (%s, %s, %s, %s,
                COALESCE((SELECT order_idx FROM kit_sections WHERE section_key=%s), 99)) 
            ON CONFLICT (section_key) DO UPDATE SET title=EXCLUDED.title, icon=EXCLUDED.icon, content=EXCLUDED.content
        """, (section_key, title, icon, content, section_key))
    conn.commit()
    conn.close()


# ── VIDEOS ────────────────────────────────────────────────────────────────────

@st.cache_data
def get_videos() -> list:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM videos ORDER BY order_idx, id")
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_video(title: str, description: str, youtube_url: str, order_idx: int, created_by: str) -> int:
    clear_cache()
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO videos(title,description,youtube_url,order_idx,created_by) VALUES(%s,%s,%s,%s,%s) RETURNING id",
              (title, description, youtube_url, order_idx, created_by))
    vid = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return vid


def update_video(vid_id: int, title: str, description: str, youtube_url: str, order_idx: int):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE videos SET title=%s,description=%s,youtube_url=%s,order_idx=%s WHERE id=%s",
                     (title, description, youtube_url, order_idx, vid_id))
    conn.commit()
    conn.close()


def delete_video(vid_id: int):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM videos WHERE id=%s", (vid_id,))
    conn.commit()
    conn.close()


# ── LEADS ─────────────────────────────────────────────────────────────────────

def calculate_score(profile_type, urgency, budget_confirmed, available, fast_response):
    score = 0
    if profile_type in ("Entrepreneur", "Freelance"): score += 2
    if urgency == "Immédiate":                        score += 2
    if budget_confirmed:                               score += 2
    if available:                                      score += 2
    if fast_response:                                  score += 2
    if score >= 8:   temp = "🔥 Chaud"
    elif score >= 5: temp = "⚡ Tiède"
    else:            temp = "❄️ Froid"
    return score, temp


def add_lead(data: dict) -> int:
    clear_cache()
    # Ensure booleans are actually booleans for PostgreSQL
    budget_confirmed = bool(data.get("budget_confirmed", False))
    available = bool(data.get("available", False))
    fast_response = bool(data.get("fast_response", False))

    score, temp = calculate_score(
        data.get("profile_type"), data.get("urgency"),
        budget_confirmed, available, fast_response,
    )

    # Defaults for all expected keys to avoid KeyError from psycopg2
    lead_defaults = {
        "name": "", "phone": "", "email": "", "assigned_to": "", "status": "Nouveau",
        "goal": "", "profile_type": "", "urgency": "", "budget_confirmed": budget_confirmed,
        "available": available, "fast_response": fast_response, "score": score,
        "temperature": temp, "campaign": "", "adset": "", "creative": "",
        "notes": "", "last_contact": "", "follow_up_date": "", "follow_up_day": 0,
        "amount_paid": 0.0
    }
    
    data_to_save = {**lead_defaults, **data}
    # Re-apply calculated values
    data_to_save.update({"score": score, "temperature": temp, 
                        "budget_confirmed": budget_confirmed, "available": available, 
                        "fast_response": fast_response})

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO leads
            (name,phone,email,assigned_to,status,goal,profile_type,urgency,
             budget_confirmed,available,fast_response,score,temperature,
             campaign,adset,creative,notes,last_contact,follow_up_date,follow_up_day,amount_paid)
            VALUES
            (%(name)s,%(phone)s,%(email)s,%(assigned_to)s,%(status)s,%(goal)s,%(profile_type)s,%(urgency)s,
             %(budget_confirmed)s,%(available)s,%(fast_response)s,%(score)s,%(temperature)s,
             %(campaign)s,%(adset)s,%(creative)s,%(notes)s,%(last_contact)s,%(follow_up_date)s,%(follow_up_day)s,%(amount_paid)s)
            RETURNING id
        """, data_to_save)
        lead_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id: int, data: dict):
    clear_cache()
    # Ensure booleans are actually booleans for PostgreSQL
    budget_confirmed = bool(data.get("budget_confirmed", False))
    available = bool(data.get("available", False))
    fast_response = bool(data.get("fast_response", False))

    score, temp = calculate_score(
        data.get("profile_type"), data.get("urgency"),
        budget_confirmed, available, fast_response,
    )
    
    # Defaults for all expected keys
    lead_defaults = {
        "name": "", "phone": "", "email": "", "assigned_to": "", "status": "Nouveau",
        "goal": "", "profile_type": "", "urgency": "", "budget_confirmed": budget_confirmed,
        "available": available, "fast_response": fast_response, "score": score,
        "temperature": temp, "campaign": "", "adset": "", "creative": "",
        "notes": "", "last_contact": "", "follow_up_date": "", "amount_paid": 0.0
    }

    data_to_update = {**lead_defaults, **data}
    data_to_update.update({
        "score": score, "temperature": temp,
        "budget_confirmed": budget_confirmed, "available": available, 
        "fast_response": fast_response, "updated_at": datetime.now(), "id": lead_id
    })

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE leads SET
                name=%(name)s, phone=%(phone)s, email=%(email)s, assigned_to=%(assigned_to)s,
                status=%(status)s, goal=%(goal)s, profile_type=%(profile_type)s, urgency=%(urgency)s,
                budget_confirmed=%(budget_confirmed)s, available=%(available)s,
                fast_response=%(fast_response)s, score=%(score)s, temperature=%(temperature)s,
                campaign=%(campaign)s, adset=%(adset)s, creative=%(creative)s,
                amount_paid=%(amount_paid)s, notes=%(notes)s, last_contact=%(last_contact)s,
                follow_up_date=%(follow_up_date)s, updated_at=%(updated_at)s
            WHERE id=%(id)s
        """, data_to_update)
    conn.commit()
    conn.close()


def get_leads(assigned_to: str = None) -> pd.DataFrame:
    if assigned_to:
        df = pd.read_sql_query(
            "SELECT * FROM leads WHERE assigned_to=%s ORDER BY created_at DESC",
            get_engine(), params=(assigned_to,))
    else:
        df = pd.read_sql_query("SELECT * FROM leads ORDER BY created_at DESC", get_engine())
    return df


def get_lead(lead_id: int) -> dict:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM leads WHERE id=%s", (lead_id,))
        row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def delete_lead(lead_id: int):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM leads WHERE id=%s", (lead_id,))
    conn.commit()
    conn.close()


def get_upcoming_followups(assigned_to: str = None) -> pd.DataFrame:
    if assigned_to:
        df = pd.read_sql_query("""
            SELECT id,name,phone,goal,status,temperature,follow_up_date,assigned_to
            FROM leads WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
              AND assigned_to=%s ORDER BY follow_up_date ASC
        """, get_engine(), params=(assigned_to,))
    else:
        df = pd.read_sql_query("""
            SELECT id,name,phone,goal,status,temperature,follow_up_date,assigned_to
            FROM leads WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
            ORDER BY follow_up_date ASC
        """, get_engine())
    return df


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_team_stats() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            assigned_to AS agent,
            COUNT(*) AS total_leads,
            SUM(CASE WHEN status='Inscrit/Soldé' THEN 1 ELSE 0 END) AS closed,
            SUM(CASE WHEN status='Perdu'         THEN 1 ELSE 0 END) AS lost,
            SUM(CASE WHEN status='Nouveau'       THEN 1 ELSE 0 END) AS new_leads,
            COALESCE(SUM(CASE WHEN status='Inscrit/Soldé' THEN amount_paid ELSE 0 END), 0) AS revenue,
            ROUND(CAST(COALESCE(SUM(CASE WHEN status='Inscrit/Soldé' THEN amount_paid ELSE 0 END), 0) * 0.10 AS NUMERIC), 0) AS commission
        FROM leads GROUP BY assigned_to
    """, get_engine())
    conn.close()
    if not df.empty:
        df["conversion_rate"] = df.apply(
            lambda r: round(r["closed"] / r["total_leads"] * 100, 1) if r["total_leads"] > 0 else 0.0,
            axis=1)
    return df


def get_agent_commission(username: str) -> float:
    """Commission for a specific agent from their closed leads."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(amount_paid), 0) AS revenue
            FROM leads WHERE assigned_to=%s AND status='Inscrit/Soldé'
        """, (username,))
        row = cur.fetchone()
    conn.close()
    return float(row["revenue"]) * 0.10 if row else 0.0


@st.cache_data(ttl=300)
def get_weekly_kpis() -> dict:
    engine = get_engine()
    
    # 1. Contacted Leads (last 7 days)
    # Counts unique leads that were either moved from Nouveau or had a contact action
    df_contacts = pd.read_sql_query("""
        SELECT "user" as agent, COUNT(DISTINCT lead_id) AS contacted
        FROM activity_log
        WHERE created_at >= NOW() - INTERVAL '7 days'
          AND (
            (action = 'UPDATED' AND detail NOT LIKE '%%→ Nouveau%%' AND detail LIKE '%%Statut →%%')
            OR action IN ('CONTACTED', 'WHATSAPP_SENT')
          )
        GROUP BY "user"
    """, engine)

    # 2. Closed Leads & Revenue (last 7 days)
    # Counts leads moved to 'Inscrit/Soldé'
    df_sales = pd.read_sql_query("""
        SELECT a."user" as agent, COUNT(DISTINCT a.lead_id) AS closed, SUM(l.amount_paid) AS revenue
        FROM activity_log a
        JOIN leads l ON a.lead_id = l.id
        WHERE a.created_at >= NOW() - INTERVAL '7 days'
          AND a.action = 'UPDATED' AND a.detail LIKE '%%Inscrit/Soldé%%'
        GROUP BY a."user"
    """, engine)

    # Merge stats
    agents = pd.concat([df_contacts["agent"], df_sales["agent"]]).unique()
    stats = pd.DataFrame({"agent": agents})
    stats = stats.merge(df_contacts, on="agent", how="left").fillna(0)
    stats = stats.merge(df_sales, on="agent", how="left").fillna(0)
    
    # Conversion rate: closed / contacted (of the week)
    stats["rate"] = stats.apply(lambda r: r["closed"] / r["contacted"] if r["contacted"] > 0 else 0, axis=1)
    stats["commission"] = stats["revenue"] * 0.10
    
    if stats.empty: return {"closer": None, "contacts": None, "commission": None}
    
    top_closer = stats[stats["rate"] > 0].sort_values("rate", ascending=False).iloc[0] if not stats[stats["rate"] > 0].empty else None
    top_contact = stats[stats["contacted"] > 0].sort_values("contacted", ascending=False).iloc[0] if not stats[stats["contacted"] > 0].empty else None
    top_comm = stats[stats["commission"] > 0].sort_values("commission", ascending=False).iloc[0] if not stats[stats["commission"] > 0].empty else None
    
    return {
        "closer": {"agent": top_closer["agent"], "val": top_closer["rate"]} if top_closer is not None else None,
        "contacts": {"agent": top_contact["agent"], "val": top_contact["contacted"]} if top_contact is not None else None,
        "commission": {"agent": top_comm["agent"], "val": top_comm["commission"]} if top_comm is not None else None,
    }


@st.cache_data(ttl=300)
def get_funnel_stats(assigned_to: str = None) -> pd.DataFrame:
    conn = get_connection()
    if assigned_to:
        df = pd.read_sql_query(
            "SELECT status, COUNT(*) AS count FROM leads WHERE assigned_to=%s GROUP BY status",
            get_engine(), params=(assigned_to,))
    else:
        df = pd.read_sql_query("SELECT status, COUNT(*) AS count FROM leads GROUP BY status", get_engine())
    conn.close()
    return df


@st.cache_data(ttl=300)
def get_roas_by_creative() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT creative, COUNT(*) AS leads,
               SUM(CASE WHEN status='Inscrit/Soldé' THEN 1 ELSE 0 END) AS conversions,
               COALESCE(SUM(amount_paid), 0) AS revenue
        FROM leads WHERE creative IS NOT NULL AND creative != ''
        GROUP BY creative ORDER BY revenue DESC
    """, get_engine())
    conn.close()
    return df


def export_leads_excel() -> bytes:
    import io
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM leads", get_engine())
    conn.close()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Leads")
    return buf.getvalue()


# ── ACTIVITY LOG ──────────────────────────────────────────────────────────────

def log_activity(user: str, lead_id: int, action: str, detail: str = ""):
    clear_cache()
    # Ensure lead_id is an int (not numpy.int64)
    lead_id = int(lead_id)
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO activity_log(\"user\",lead_id,action,detail) VALUES(%s,%s,%s,%s)",
                     (user, lead_id, action, detail))
    conn.commit()
    conn.close()


@st.cache_data(ttl=60)
def get_recent_activity(limit: int = 20) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT %s", get_engine(), params=(limit,))
    return df
# ── INVOICES ───────────────────────────────────────────────────────────────

def add_invoice(lead_id: int, invoice_number: str, items: str, total_amount: str, pdf_url: str, created_by: str) -> int:
    clear_cache()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO invoices (lead_id, invoice_number, items, total_amount, pdf_url, created_by)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    """, (lead_id, invoice_number, items, total_amount, pdf_url, created_by))
    inv_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return inv_id

def get_lead_invoices(lead_id: int) -> list:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM invoices WHERE lead_id=%s ORDER BY created_at DESC", (lead_id,))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_next_invoice_number() -> str:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM invoices")
        count = cur.fetchone()["count"]
    conn.close()
    return f"INV-{datetime.now().strftime('%Y%m')}-{count + 1:03d}"

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────

def add_notification(recipient: str, message: str, doc_type: str = None, doc_id: int = None):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO notifications (recipient, message, doc_type, doc_id)
            VALUES (%s, %s, %s, %s)
        """, (recipient, message, doc_type, doc_id))
    conn.commit()
    conn.close()

@st.cache_data
def get_notifications(recipient: str, only_unread: bool = True) -> list:
    conn = get_connection()
    with conn.cursor() as cur:
        query = "SELECT * FROM notifications WHERE recipient=%s"
        if only_unread:
            query += " AND is_read=false"
        query += " ORDER BY created_at DESC LIMIT 50"
        cur.execute(query, (recipient,))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notification_as_read(notif_id: int):
    clear_cache()
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE notifications SET is_read=true WHERE id=%s", (notif_id,))
    conn.commit()
    conn.close()
