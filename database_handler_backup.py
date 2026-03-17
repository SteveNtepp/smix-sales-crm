"""
database_handler.py — Smix Sales Assistant
SQLite persistence: users, leads, config, scripts, resources, videos.
"""

import sqlite3
import hashlib
from datetime import datetime, date
import pandas as pd

DB_PATH = "smix_sales.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


# ── INIT ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT NOT NULL DEFAULT 'sales',
            full_name  TEXT NOT NULL,
            active     INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # migrations for users
    user_cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if "active" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            phone            TEXT NOT NULL,
            email            TEXT,
            assigned_to      TEXT NOT NULL,
            status           TEXT DEFAULT 'Nouveau',
            goal             TEXT,
            profile_type     TEXT,
            urgency          TEXT,
            budget_confirmed INTEGER DEFAULT 0,
            available        INTEGER DEFAULT 0,
            fast_response    INTEGER DEFAULT 0,
            score            INTEGER DEFAULT 0,
            temperature      TEXT DEFAULT '❄️ Froid',
            campaign         TEXT,
            adset            TEXT,
            creative         TEXT,
            amount_paid      REAL DEFAULT 0,
            notes            TEXT,
            last_contact     TEXT,
            follow_up_date   TEXT,
            follow_up_day    INTEGER DEFAULT 0,
            created_at       TEXT DEFAULT (datetime('now')),
            updated_at       TEXT DEFAULT (datetime('now'))
        )
    """)

    lead_cols = [r[1] for r in c.execute("PRAGMA table_info(leads)").fetchall()]
    for col, defn in [("follow_up_date", "TEXT"), ("follow_up_day", "INTEGER DEFAULT 0")]:
        if col not in lead_cols:
            c.execute(f"ALTER TABLE leads ADD COLUMN {col} {defn}")

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
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            category   TEXT DEFAULT 'Personnalisé',
            content    TEXT NOT NULL,
            created_by TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kit_sections (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            section_key TEXT UNIQUE NOT NULL,
            title       TEXT NOT NULL,
            icon        TEXT DEFAULT '📄',
            content     TEXT NOT NULL,
            order_idx   INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            youtube_url TEXT NOT NULL,
            order_idx   INTEGER DEFAULT 0,
            created_by  TEXT DEFAULT 'admin',
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user       TEXT,
            lead_id    INTEGER,
            action     TEXT,
            detail     TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
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
        c.execute("INSERT OR IGNORE INTO users (username,password,role,full_name) VALUES (?,?,?,?)", u)
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
        c.execute("INSERT OR IGNORE INTO config(key,value) VALUES(?,?)", (k, v))
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
        c.execute("INSERT OR REPLACE INTO scripts(day,title,content) VALUES(?,?,?)", s)
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
            INSERT OR IGNORE INTO kit_sections (section_key, title, icon, content, order_idx)
            VALUES (?, ?, ?, ?, ?)
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
            INSERT OR IGNORE INTO videos (title, description, youtube_url, order_idx)
            SELECT ?, ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM videos WHERE youtube_url=?)
        """, (title, desc, url, order, url))
    conn.commit()


# ── AUTH ──────────────────────────────────────────────────────────────────────

def authenticate(username: str, password: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=? AND active=1",
              (username, hash_password(password)))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ── USER MANAGEMENT ───────────────────────────────────────────────────────────

def get_all_users() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, username, full_name, role, active, created_at FROM users ORDER BY id", conn)
    conn.close()
    return df


def create_user(username: str, password: str, role: str, full_name: str) -> bool:
    try:
        conn = get_connection()
        conn.execute("INSERT INTO users(username,password,role,full_name) VALUES(?,?,?,?)",
                     (username.strip().lower(), hash_password(password), role, full_name.strip()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def update_user_status(user_id: int, active: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET active=? WHERE id=?", (int(active), user_id))
    conn.commit()
    conn.close()


def reset_user_password(user_id: int, new_password: str):
    conn = get_connection()
    conn.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_password), user_id))
    conn.commit()
    conn.close()


def get_sales_agents() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT username, full_name FROM users WHERE active=1 ORDER BY full_name").fetchall()
    conn.close()
    return [(r["username"], r["full_name"]) for r in rows]


# ── CONFIG ────────────────────────────────────────────────────────────────────

def get_config() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def update_config(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO config(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


# ── SCRIPTS ───────────────────────────────────────────────────────────────────

def get_scripts() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT day, title, content FROM scripts").fetchall()
    conn.close()
    return {r["day"]: {"title": r["title"], "content": r["content"]} for r in rows}


def update_script(day: str, title: str, content: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO scripts(day,title,content) VALUES(?,?,?)",
                 (day, title, content))
    conn.commit()
    conn.close()


# ── SCRIPT TEMPLATES ──────────────────────────────────────────────────────────

def get_script_templates() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM script_templates ORDER BY created_at DESC", conn)
    conn.close()
    return df


def add_script_template(name: str, category: str, content: str, created_by: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO script_templates(name,category,content,created_by) VALUES(?,?,?,?)",
              (name, category, content, created_by))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid


def update_script_template(tid: int, name: str, category: str, content: str):
    conn = get_connection()
    conn.execute("UPDATE script_templates SET name=?,category=?,content=? WHERE id=?",
                 (name, category, content, tid))
    conn.commit()
    conn.close()


def delete_script_template(tid: int):
    conn = get_connection()
    conn.execute("DELETE FROM script_templates WHERE id=?", (tid,))
    conn.commit()
    conn.close()


# ── KIT SECTIONS ──────────────────────────────────────────────────────────────

def get_kit_sections() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM kit_sections ORDER BY order_idx").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_kit_section(section_key: str, title: str, icon: str, content: str):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO kit_sections (section_key, title, icon, content, order_idx)
        VALUES (?, ?, ?, ?,
            COALESCE((SELECT order_idx FROM kit_sections WHERE section_key=?), 99))
    """, (section_key, title, icon, content, section_key))
    conn.commit()
    conn.close()


# ── VIDEOS ────────────────────────────────────────────────────────────────────

def get_videos() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM videos ORDER BY order_idx, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_video(title: str, description: str, youtube_url: str, order_idx: int, created_by: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO videos(title,description,youtube_url,order_idx,created_by) VALUES(?,?,?,?,?)",
              (title, description, youtube_url, order_idx, created_by))
    vid = c.lastrowid
    conn.commit()
    conn.close()
    return vid


def update_video(vid_id: int, title: str, description: str, youtube_url: str, order_idx: int):
    conn = get_connection()
    conn.execute("UPDATE videos SET title=?,description=?,youtube_url=?,order_idx=? WHERE id=?",
                 (title, description, youtube_url, order_idx, vid_id))
    conn.commit()
    conn.close()


def delete_video(vid_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM videos WHERE id=?", (vid_id,))
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
    score, temp = calculate_score(
        data.get("profile_type"), data.get("urgency"),
        data.get("budget_confirmed", 0), data.get("available", 0), data.get("fast_response", 0),
    )
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO leads
        (name,phone,email,assigned_to,status,goal,profile_type,urgency,
         budget_confirmed,available,fast_response,score,temperature,
         campaign,adset,creative,notes,last_contact,follow_up_date,follow_up_day)
        VALUES
        (:name,:phone,:email,:assigned_to,:status,:goal,:profile_type,:urgency,
         :budget_confirmed,:available,:fast_response,:score,:temperature,
         :campaign,:adset,:creative,:notes,:last_contact,:follow_up_date,:follow_up_day)
    """, {**data, "score": score, "temperature": temp,
          "follow_up_date": data.get("follow_up_date", ""),
          "follow_up_day":  data.get("follow_up_day", 0)})
    lead_id = c.lastrowid
    conn.commit()
    conn.close()
    return lead_id


def update_lead(lead_id: int, data: dict):
    score, temp = calculate_score(
        data.get("profile_type"), data.get("urgency"),
        data.get("budget_confirmed", 0), data.get("available", 0), data.get("fast_response", 0),
    )
    data.update({"score": score, "temperature": temp,
                 "updated_at": datetime.now().isoformat(), "id": lead_id})
    conn = get_connection()
    conn.execute("""
        UPDATE leads SET
            name=:name, phone=:phone, email=:email, assigned_to=:assigned_to,
            status=:status, goal=:goal, profile_type=:profile_type, urgency=:urgency,
            budget_confirmed=:budget_confirmed, available=:available,
            fast_response=:fast_response, score=:score, temperature=:temperature,
            campaign=:campaign, adset=:adset, creative=:creative,
            amount_paid=:amount_paid, notes=:notes, last_contact=:last_contact,
            follow_up_date=:follow_up_date, updated_at=:updated_at
        WHERE id=:id
    """, data)
    conn.commit()
    conn.close()


def get_leads(assigned_to: str = None) -> pd.DataFrame:
    conn = get_connection()
    if assigned_to:
        df = pd.read_sql_query(
            "SELECT * FROM leads WHERE assigned_to=? ORDER BY created_at DESC",
            conn, params=(assigned_to,))
    else:
        df = pd.read_sql_query("SELECT * FROM leads ORDER BY created_at DESC", conn)
    conn.close()
    return df


def get_lead(lead_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


def delete_lead(lead_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM leads WHERE id=?", (lead_id,))
    conn.commit()
    conn.close()


def get_upcoming_followups(assigned_to: str = None) -> pd.DataFrame:
    conn = get_connection()
    if assigned_to:
        df = pd.read_sql_query("""
            SELECT id,name,phone,goal,status,temperature,follow_up_date,assigned_to
            FROM leads WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
              AND assigned_to=? ORDER BY follow_up_date ASC
        """, conn, params=(assigned_to,))
    else:
        df = pd.read_sql_query("""
            SELECT id,name,phone,goal,status,temperature,follow_up_date,assigned_to
            FROM leads WHERE follow_up_date IS NOT NULL AND follow_up_date != ''
            ORDER BY follow_up_date ASC
        """, conn)
    conn.close()
    return df


# ── ANALYTICS ─────────────────────────────────────────────────────────────────

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
            ROUND(COALESCE(SUM(CASE WHEN status='Inscrit/Soldé' THEN amount_paid ELSE 0 END), 0) * 0.10, 0) AS commission
        FROM leads GROUP BY assigned_to
    """, conn)
    conn.close()
    if not df.empty:
        df["conversion_rate"] = df.apply(
            lambda r: round(r["closed"] / r["total_leads"] * 100, 1) if r["total_leads"] > 0 else 0.0,
            axis=1)
    return df


def get_agent_commission(username: str) -> float:
    """Commission for a specific agent from their closed leads."""
    conn = get_connection()
    row = conn.execute("""
        SELECT COALESCE(SUM(amount_paid), 0) AS revenue
        FROM leads WHERE assigned_to=? AND status='Inscrit/Soldé'
    """, (username,)).fetchone()
    conn.close()
    return float(row["revenue"]) * 0.10 if row else 0.0


def get_weekly_top_closer() -> str:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT assigned_to, COUNT(*) AS total,
               SUM(CASE WHEN status='Inscrit/Soldé' THEN 1 ELSE 0 END) AS closed
        FROM leads WHERE created_at >= datetime('now', '-7 days')
        GROUP BY assigned_to
    """, conn)
    conn.close()
    if df.empty: return ""
    df["rate"] = df.apply(lambda r: r["closed"] / r["total"] if r["total"] > 0 else 0, axis=1)
    top = df.sort_values("rate", ascending=False).iloc[0]
    return top["assigned_to"] if top["rate"] > 0 else ""


def get_funnel_stats(assigned_to: str = None) -> pd.DataFrame:
    conn = get_connection()
    if assigned_to:
        df = pd.read_sql_query(
            "SELECT status, COUNT(*) AS count FROM leads WHERE assigned_to=? GROUP BY status",
            conn, params=(assigned_to,))
    else:
        df = pd.read_sql_query("SELECT status, COUNT(*) AS count FROM leads GROUP BY status", conn)
    conn.close()
    return df


def get_roas_by_creative() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT creative, COUNT(*) AS leads,
               SUM(CASE WHEN status='Inscrit/Soldé' THEN 1 ELSE 0 END) AS conversions,
               COALESCE(SUM(amount_paid), 0) AS revenue
        FROM leads WHERE creative IS NOT NULL AND creative != ''
        GROUP BY creative ORDER BY revenue DESC
    """, conn)
    conn.close()
    return df


def export_leads_excel() -> bytes:
    import io
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM leads", conn)
    conn.close()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Leads")
    return buf.getvalue()


# ── ACTIVITY LOG ──────────────────────────────────────────────────────────────

def log_activity(user: str, lead_id: int, action: str, detail: str = ""):
    conn = get_connection()
    conn.execute("INSERT INTO activity_log(user,lead_id,action,detail) VALUES(?,?,?,?)",
                 (user, lead_id, action, detail))
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 20) -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", conn, params=(limit,))
    conn.close()
    return df
