# 🎯 Smix Sales Assistant (Enterprise Edition V3)

Le **Smix Sales Assistant** est un CRM interne (Customer Relationship Management) développé spécifiquement pour les agents commerciaux de la **Smix Academy**. Conçue avec Streamlit, l'application est pensée pour être rapide, réactive, orientée mobile, et hautement optimisée pour la conversion de prospects (leads) issus de campagnes Meta Ads.

## ✨ Fonctionnalités Principales

### 👥 Gestion des Leads & Pipeline
- **Création rapide** : Formulaire optimisé pour capturer les leads avec des tags de qualification (Urgence, Budget, Disponibilité).
- **Scoring intelligent (/10)** : Évalue la "température" d'un lead (Froid ❄️, Tiède ⚡, Chaud 🔥) en fonction des critères de qualification.
- **Relances dynamiques** : Suivi des relances "Aujourd'hui", "En retard", et "À venir".

### 💬 Moteur Commercial WhatsApp
- **Génération One-Click** : Génère des liens `api.whatsapp.com` avec des messages pré-remplis (encodés en UTF-8 pour supporter parfaitement les emojis).
- **Trame J1 à J7** : Scripts de relance standardisés pour les jours 1, 3, 5 et 7.
- **Variables Dynamiques** : Substitution automatique du `[Prénom]`, de l'`{{objectif}}`, du prix promotionnel et de la date de démarrage dans les messages.

### 📚 Ressources & Formation Intégrées
- **Kit Commercial** : Un espace regroupant le script d'appel type, les objections courantes avec réponses, et les critères stricts de qualification.
- **Vidéos YouTube** : Formations embarquées (via iframes) directement lisibles depuis l'application sans en sortir.

### 📊 Analytiques & Gamification (RBAC)
- **Role-Based Access Control** : Les vues s'adaptent au rôle connecté (`admin` vs `sales`).
- **Dashboard Global (Admin)** : Vision panoramique de l'équipe, pipeline, CA généré, et leaderboard des commerciaux.
- **Vue Commerciale (Sales)** : Un agent ne voit **que ses leads** et sa propre commission.
- **KPIs Équipe** : Bandeaux "Top Closer🏆", "Top Prospection📞", et "Top Commission💰" visibles par tous. L'agent remportant un de ces titres a droit à une animation "Ballons" 🎈.

### ⚙️ Cockpit Admin
Espace de configuration complet pour le manager :
- **Paramètres de l'Offre** : Configuration globale du prix, du nom du programme et des dates.
- **Éditeur de Scripts & Kit** : Ajout et modification des scripts WhatsApp et du Kit sans toucher au code.
- **Gestionnaire Vidéos** : Ajout d'URL YouTube pour le module Formation.
- **Gestion des Accès** : Création de comptes, resets de mots de passe, et (dés)activation d'agents.

## 🛠️ Stack Technique

- **Interface Serveur** : [Streamlit](https://streamlit.io) 
- **Base de Données** : SQLite (`sqlite3` local avec une structure relationnelle).
- **Visualisation de données** : Altair (`alt.Chart`) avec graphiques responsifs.
- **Outils Data** : Pandas pour l'agrégation et l'export Excel (`openpyxl`).
- **Thème Visual CSS** : CSS Vanilla sur-mesure (thème "Midnight Blue & Smix Purple").

## 🚀 Installation Locale (Développement)

1. **Cloner le projet** ou récupérer le dossier.
2. **Créer un environnement virtuel** (recommandé) :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   # ou venv\Scripts\activate pour Windows
   ```
3. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
4. **Lancer l'application** :
   ```bash
   streamlit run app_sales.py
   ```
   *L'application sera accessible sur `http://localhost:8501`. La base de données `smix_sales.db` se créera automatiquement avec un compte `steve` (mot de passe: `admin123`) au premier lancement.*

---
*Développé pour l'équipe Commerciale Smix.*
