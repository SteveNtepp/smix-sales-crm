# 🚀 Déploiement : Smix Sales Assistant (Streamlit Cloud)

Ce guide décrit la méthode la plus simple et recommandée pour mettre en ligne l'application de façon **gratuite** et accessible de n'importe où, avec le **Streamlit Community Cloud**.

---

## Étape 1 : Héberger le code sur GitHub 🐙

Streamlit Cloud lit le code source depuis un dépôt GitHub public ou privé.

1. Créez un compte GitHub si vous n'en possédez pas ([github.com](https://github.com)).
2. Créez **un nouveau dépôt** (repository) en haut à droite (*New* ou le `+`).
3. Nommez-le, par exemple, `smix-sales-assistant` (vous pouvez le mettre en **Privé** si vous ne souhaitez pas que le code métier soit visible).
4. Mettre les fichiers du projet en ligne. Le dépôt GitHub final **doit contenir, au minimum, les fichiers suivants à la racine** :
   - `app_sales.py` (L'application principale)
   - `database_handler.py` (Code de la base SQLite)
   - `style.css` (Design et charte graphique)
   - `requirements.txt` (Les dépendances Python : `streamlit`, `pandas`, `openpyxl`, `altair`)
   - `.gitignore` *(Optionnel mais recommandé, pour ignorer `smix_sales.db` et le dossier `__pycache__/`)*

> **⚠️ Attention sur les bases SQLite (Important)** : Le Streamlit Community Cloud recrée régulièrement le conteneur du serveur. Si vous déployez sur l'environnement gratuit de Streamlit Cloud avec **SQLite**, les données saisies par les commerciaux **seront régulièrement perdues/effacées** lors des redémarrages de l'application !
> 
> **Solutions durables pour l'avenir :**
> - **Option 1** (Gratuite & Cloud-native) : Remplacer `SQLite` par **Supabase** (PostgreSQL gratuit).
> - **Option 2** (Hébergement VPS) : Déployer le code sur un VPS via Docker (OVH, DigitalOcean, Render) et héberger votre `sqlite3` via un volume persistant.

---

## Étape 2 : Lier GitHub et Streamlit Cloud ☁️

1. Allez sur **[share.streamlit.io](https://share.streamlit.io/)**
2. Connectez-vous en choisissant **"Continue with GitHub"** (Ceci permet à Streamlit d'avoir les droits de lecture sur votre dépôt pour initialiser l'app).
3. Cliquez sur **“Log In”**. La console (Workspace) s'affiche.

---

## Étape 3 : Déployer l'application 🌍

1. Cliquez sur le bouton bleu **"New app"** (Nouvelle application) en haut à droite.
2. Autorisez l'accès à vos dépôts GitHub si cela vous est demandé.
3. Remplissez le formulaire de déploiement :
   - **Repository** : Sélectionnez le dépôt que vous avez créé à l'étape 1 (ex: `votre-nom/smix-sales-assistant`).
   - **Branch** : Laissez généralement `main` ou `master` (la valeur par défaut).
   - **Main file path** : Renseignez le nom du fichier principal (Ici, ce doit être **`app_sales.py`**).
   - **App URL** : Streamlit peut générer un lien plus agréable en personnalisant l'URL (ex: `smix-crm.streamlit.app`).
4. Cliquez sur **"Deploy!"** 🚀

---

## Étape 4 : Configurer les Secrets (CRITIQUE pour Supabase) 🔐

Puisque nous utilisons désormais **Supabase**, l'application a besoin d'une clé secrète pour se connecter à la base de données. **Sans cette étape, l'application affichera une erreur.**

1. Sur votre tableau de bord Streamlit Cloud, localisez votre application.
2. Cliquez sur les **trois petits points (⋮)** à droite du nom de l'app, puis sur **Settings**.
3. Dans le menu de gauche, cliquez sur **Secrets**.
4. Dans la zone de texte, copiez et collez la ligne suivante (remplacez par votre URL réelle si nécessaire, mais vous pouvez copier celle de votre fichier `.streamlit/secrets.toml` local) :

```toml
DB_URL = "postgresql://postgres.oebqgbfazfdmeakqqpko:SmixAdmin2026@aws-1-eu-central-2.pooler.supabase.com:5432/postgres"
```

5. Cliquez sur **Save**. L'application va redémarrer automatiquement et se connecter à votre base de données cloud !

---

## Mettre à jour l'application 🔄

C'est simple ! Si vous avez besoin de changer du code Python ou des styles CSS dans le futur :

1. Faites vos modifications en local sur votre éditeur de code.
2. "Poussez" ou copiez/uploadez les fichiers modifiés **directement sur GitHub**.
3. **C'est tout !**
Le serveur Streamlit Cloud s'aperçoit d'un changement dans la branche GitHub et se **re-déploiera automatiquement (Hot Reloading)** sans qu'il soit nécessaire d'intervenir sur le site de Streamlit.
