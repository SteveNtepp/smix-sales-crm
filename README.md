# 🎯 Smix Sales Assistant (Enterprise Edition V3.5)

Le **Smix Sales Assistant** est un CRM interne (Customer Relationship Management) développé spécifiquement pour les agents commerciaux de la **Smix Academy**. Conçue avec Streamlit, l'application est pensée pour être rapide, réactive, orientée mobile, et hautement optimisée pour la conversion de prospects (leads) issus de campagnes Meta Ads.

## ✨ Fonctionnalités Principales

### 👥 Gestion des Leads & Pipeline
- **Création rapide** : Formulaire optimisé pour capturer les leads avec des tags de qualification (Urgence, Budget, Disponibilité).
- **Scoring intelligent (/10)** : Évalue la "température" d'un lead (Froid ❄️, Tiède ⚡, Chaud 🔥) en fonction des critères de qualification.
- **Relances dynamiques** : Suivi des relances "Aujourd'hui", "En retard", et "À venir".

### 🧾 Système de Facturation & Reçus (NOUVEAU)
- **Génération PDF automatisée** : Les administrateurs peuvent générer des factures professionnelles aux couleurs de Smix en un clic depuis le Cockpit.
- **Hébergement Cloud** : Les documents sont automatiquement hébergés de manière sécurisée et permanente (via Catbox).
- **Partage WhatsApp** : Les agents peuvent envoyer le lien direct de la facture au prospect depuis la fiche lead.

### 🔔 Système de Notifications (NOUVEAU)
- **Alertes Agents** : Les agents reçoivent une notification visuelle immédiate dès qu'un document (facture) est créé pour un de leurs prospects.
- **Badge Centralisé** : Un indicateur visuel en haut d'écran permet de suivre les messages non lus.

### 💬 Moteur Commercial WhatsApp
- **Génération One-Click** : Génère des liens `api.whatsapp.com` avec des messages pré-remplis (encodés en UTF-8 pour supporter parfaitement les emojis).
- **Trame J1 à J7** : Scripts de relance standardisés pour les jours 1, 3, 5 et 7.

### 📚 Ressources & Formation Intégrées
- **Kit Commercial** : Un espace regroupant le script d'appel type, les objections courantes avec réponses, et les critères stricts de qualification.
- **Vidéos YouTube** : Formations embarquées directement lisibles depuis l'application.

### 💎 Branding Premium & White Label
- **Interface SaaS Pur** : Suppression totale des menus techniques de Streamlit (le menu "Hamburger", le footer "Made with Streamlit", etc.) pour un aspect 100% professionnel.
- **Design Système** : Thème personnalisé "Midnight Blue & Smix Purple" (#5e17eb).

## 🛠️ Stack Technique

- **Interface Serveur** : [Streamlit](https://streamlit.io) 
- **Moteur PDF** : fpdf2 pour la génération dynamique de documents.
- **Base de Données** : Supabase (PostgreSQL) — migration effectuée depuis SQLite pour supporter la multi-connexion et la persistence cloud.
- **Hébergement Cloud** : Streamlit Cloud & Catbox.moe pour les fichiers.

## 🚀 Installation Locale (Développement)

1. **Cloner le projet** ou récupérer le dossier.
2. **Créer un environnement virtuel** :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   ```
3. **Configurer les Secrets** :
   Créez un fichier `.streamlit/secrets.toml` avec votre connexion Supabase :
   ```toml
   DB_URL = "postgresql://user:password@host:port/dbname"
   ```
4. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```
5. **Lancer l'application** :
   ```bash
   streamlit run app_sales.py
   ```

---
*Développé pour l'équipe Commerciale Smix Academy.*
