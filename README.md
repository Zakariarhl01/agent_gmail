# 🤖 Agent Gmail IA — Local AI powered by LM Studio

Un agent IA **100% local** qui se connecte à ta boîte Gmail pour lire, trier, classifier et envoyer des emails — sans envoyer tes données à un serveur externe. Interface web incluse.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![LM Studio](https://img.shields.io/badge/LM%20Studio-local%20LLM-purple)
![Gmail API](https://img.shields.io/badge/Gmail-API-red?logo=gmail)

---

## 📸 Aperçu

```
✉️ Agent Gmail IA
─────────────────────────────────
👤 Toi : trie mes mails de cette semaine
📅 Filtre détecté : depuis le 2026/04/13
📬 Lecture des emails depuis 2026/04/13...
✅ 20 emails récupérés
🧠 Classification lot 1/2...
   ✅ Lot 1 classifié
🏷️  Labels créés : Professionnel, Personnel, Urgent, Normal
📧 [Urgent][Professionnel] Offre d'emploi - Développeur Fullstack
📧 [Normal][Personnel] Votre commande a été expédiée
✅ Triage terminé ! 20 emails classés.
```

---

## 🧠 Architecture

```
Navigateur (index.html)
        ↓ fetch POST /chat
Serveur Flask (app.py)
        ↓
Détection d'intention
   ├── "triage" → run_triage() → Gmail API + LM Studio
   └── "general" → run_agent() → LM Studio (avec outils)
        ↓
LM Studio (LLM local — Qwen2.5 / Mistral)
        ↓
Gmail API (lecture, labels, envoi)
```

### Stack technique

| Composant | Technologie | Rôle |
|-----------|------------|------|
| LLM local | LM Studio + Qwen2.5-7B | Cerveau de l'agent |
| Backend | Python 3 + Flask | Serveur API |
| Frontend | HTML/CSS/JS vanilla | Interface utilisateur |
| Email | Gmail API v1 (Google) | Lecture et actions Gmail |
| Auth | OAuth 2.0 (Google) | Authentification sécurisée |
| Protocole LLM | OpenAI-compatible API | Communication avec LM Studio |

---

## 📋 Prérequis

Avant de commencer, assure-toi d'avoir :

- **macOS / Linux / Windows** (testé sur macOS avec puce Apple Silicon)
- **Python 3.9+** installé
- **LM Studio** installé ([lmstudio.ai](https://lmstudio.ai))
- Un **compte Google** avec Gmail
- **Git** installé

---

## 🚀 Installation complète

### Étape 1 — Cloner le projet

```bash
git clone https://github.com/ton-username/agent-gmail-ia.git
cd agent-gmail-ia
```

### Étape 2 — Installer les dépendances Python

```bash
pip3 install flask flask-cors openai google-auth google-auth-oauthlib google-api-python-client
```

Ou via le fichier requirements :

```bash
pip3 install -r requirements.txt
```

### Étape 3 — Configurer LM Studio

1. Télécharge et installe [LM Studio](https://lmstudio.ai)
2. Dans l'onglet **Discover** 🔍, cherche `Qwen2.5-7B-Instruct`
3. Télécharge la version **lmstudio-community/Qwen2.5-7B-Instruct** (Q4_K_M recommandé)
4. Va dans l'onglet **Local Server**
5. Charge le modèle téléchargé
6. Clique sur **Start Server**
7. Vérifie que le serveur tourne sur `http://localhost:1234`

> **Pourquoi Qwen2.5 ?** Ce modèle supporte nativement le *function calling* (outils), indispensable pour que l'agent puisse appeler les fonctions Gmail.

> **Besoin de RAM ?** Qwen2.5-7B-Q4 nécessite environ 6-8 Go de RAM. Sur Apple Silicon (M1/M2/M3/M4/M5), la mémoire unifiée est partagée entre CPU et GPU — LM Studio en tire pleinement parti.

### Étape 4 — Configurer l'API Gmail (OAuth 2.0)

#### 4a. Créer un projet Google Cloud

1. Va sur [console.cloud.google.com](https://console.cloud.google.com)
2. Clique sur **"Nouveau projet"** en haut à gauche
3. Donne un nom au projet (ex: `Agent Gmail IA`) et clique **Créer**

#### 4b. Activer l'API Gmail

1. Dans le menu → **"APIs & Services"** → **"Bibliothèque"**
2. Cherche **"Gmail API"** et clique **Activer**

#### 4c. Configurer l'écran de consentement OAuth

1. Menu → **"APIs & Services"** → **"Écran de consentement OAuth"**
2. Choisis **"Externe"** → **Créer**
3. Remplis les champs obligatoires :
   - **Nom de l'application** : `Agent Gmail IA`
   - **Email d'assistance** : ton adresse Gmail
   - **Email du développeur** : ton adresse Gmail
4. Clique **Enregistrer et continuer** sur chaque écran
5. Sur l'écran **"Utilisateurs test"** → **Ajouter des utilisateurs** → ajoute ton adresse Gmail
6. Clique **Enregistrer et continuer** jusqu'à la fin

#### 4d. Créer les identifiants OAuth

1. Menu → **"APIs & Services"** → **"Identifiants"**
2. Clique **"+ Créer des identifiants"** → **"ID client OAuth"**
3. Type d'application : **Application de bureau**
4. Nom : `Agent Gmail Local`
5. Clique **Créer**
6. Télécharge le fichier JSON → renomme-le **`credentials.json`**
7. Place `credentials.json` dans le dossier du projet

#### 4e. Générer le token d'authentification

Lance ce script une seule fois pour autoriser l'accès :

```bash
python3 auth_gmail.py
```

Une fenêtre de navigateur s'ouvre → connecte-toi avec ton compte Google → autorise l'accès. Un fichier `token.json` est créé automatiquement. **Ne le supprime pas**, il évite de refaire l'auth à chaque fois.

### Étape 5 — Lancer l'application

```bash
python3 app.py
```

Tu devrais voir :

```
* Running on http://127.0.0.1:5000
* Press CTRL+C to quit
```

Ouvre ton navigateur sur **[http://localhost:5000](http://localhost:5000)** 🎉

---

## 📁 Structure du projet

```
agent-gmail-ia/
├── app.py              # Serveur Flask + logique agent
├── auth_gmail.py       # Script d'authentification Gmail (à lancer 1 fois)
├── index.html          # Interface web
├── credentials.json    # 🔒 Identifiants OAuth Google (ne pas commiter)
├── token.json          # 🔒 Token d'accès Gmail (généré automatiquement)
├── requirements.txt    # Dépendances Python
├── .gitignore          # Exclut les fichiers sensibles
└── README.md           # Ce fichier
```

---

## 🔧 Fichiers de configuration

### `requirements.txt`

```
flask
flask-cors
openai
google-auth
google-auth-oauthlib
google-api-python-client
```

### `auth_gmail.py`

```python
from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("token.json", "w") as f:
    f.write(creds.to_json())

print("✅ Authentification réussie ! token.json créé.")
```

### `.gitignore`

```
# Fichiers sensibles — NE JAMAIS commiter
credentials.json
token.json

# Python
__pycache__/
*.pyc
*.pyo
.env
venv/
.venv/

# OS
.DS_Store
Thumbs.db
```

> ⚠️ **Important** : Ne commite **jamais** `credentials.json` ni `token.json` sur GitHub. Ces fichiers contiennent des accès à ta boîte mail.

---

## 💬 Utilisation

### Actions rapides (boutons dans l'interface)

| Bouton | Action |
|--------|--------|
| 📥 Lire 5 derniers | Lit et affiche les 5 derniers emails |
| 📋 Lire 10 derniers | Lit et affiche les 10 derniers emails |
| 🗂 Trier cette semaine | Trie les emails des 7 derniers jours |
| 🗂 Trier ce mois | Trie les emails du mois en cours |
| 🗂 Trier 20 derniers | Trie les 20 derniers emails |
| 🔴 Emails urgents | Liste les emails urgents |
| 📝 Résumer non lus | Résume les emails non lus |

### Commandes en langage naturel

Tu peux écrire librement dans le champ de saisie :

```
lis mes 5 derniers emails
trie mes mails depuis le début d'avril 2026
trie mes mails de cette semaine
classe mes 30 derniers emails
envoie un email à exemple@gmail.com
résume mes emails non lus
quels sont mes emails urgents ?
```

### Labels créés automatiquement dans Gmail

Après un triage, l'agent crée ces labels dans ta boîte :

- **Professionnel** — emails liés au travail, offres d'emploi, etc.
- **Personnel** — emails personnels, achats, abonnements
- **Factures** — factures, reçus, paiements
- **Newsletter** — newsletters, promotions
- **Urgent** — emails nécessitant une action rapide
- **Normal** — emails sans urgence particulière
- **Peut attendre** — emails non prioritaires

---

## 🔌 Comment fonctionne l'agent

### 1. Détection d'intention

Quand tu envoies un message, le backend analyse les mots-clés :

```python
# Mots déclencheurs du mode triage
["trie", "classe", "range", "catégorie", "label", "organise", "trier", "classer"]
```

- Si un mot correspond → mode **triage** (logique contrôlée par Python)
- Sinon → mode **agent général** (boucle tool_use avec LM Studio)

### 2. Mode triage (logique Python)

```
1. lire_emails(n, depuis)     → récupère les emails Gmail
2. LM Studio classify         → classe chaque email en JSON
3. creer_label(nom)           → crée les labels dans Gmail
4. appliquer_label(id, lid)   → applique les labels email par email
```

Le traitement se fait par **lots de 10** pour ne pas dépasser le contexte du modèle.

### 3. Mode agent général (boucle tool_use)

```
User message
    ↓
LM Studio (avec outils disponibles)
    ↓
finish_reason == "tool_calls" ?
    ├── Oui → exécute l'outil → renvoie résultat → reboucle
    └── Non → réponse finale affichée
```

### 4. Outils disponibles pour l'agent

| Outil | Description |
|-------|-------------|
| `lire_emails(nombre, depuis)` | Lit les N derniers emails, avec filtre de date optionnel |
| `marquer_lu(email_id)` | Marque un email comme lu |
| `envoyer_email(dest, sujet, corps)` | Envoie un email |
| `creer_label(nom)` | Crée un label Gmail |
| `appliquer_label(email_id, label_id)` | Applique un label à un email |
| `lister_labels()` | Liste tous les labels existants |

---

## ⚙️ Configuration avancée

### Changer de modèle LLM

Dans `app.py`, modifie le client OpenAI si tu utilises un autre port ou modèle :

```python
client = OpenAI(
    base_url="http://localhost:1234/v1",  # Port LM Studio
    api_key="lm-studio"                   # Valeur fictive obligatoire
)
```

Et dans les appels au modèle :

```python
model="local-model"  # LM Studio ignore ce champ, il utilise le modèle chargé
```

### Modèles recommandés (par ordre de préférence)

| Modèle | RAM requise | Support outils | Notes |
|--------|------------|----------------|-------|
| Qwen2.5-7B-Instruct Q4_K_M | ~6 Go | ✅ Excellent | Recommandé |
| Qwen2.5-7B-Instruct Q8 | ~10 Go | ✅ Excellent | Meilleure qualité |
| Mistral-7B-Instruct-v0.3 | ~6 Go | ✅ Bon | Alternative |
| Llama-3.1-8B-Instruct | ~7 Go | ✅ Bon | Alternative Meta |

### Augmenter le contexte dans LM Studio

Par défaut LM Studio utilise 4096 tokens de contexte. Pour traiter plus d'emails :

1. Dans LM Studio → **Local Server**
2. Cherche **"Context Length"**
3. Mets **8192** ou **16384**
4. Redémarre le serveur

### Modifier les catégories de triage

Dans `app.py`, trouve ce prompt et modifie les labels/urgences selon tes besoins :

```python
content": f"""Classe ces {len(lot)} emails. Réponds UNIQUEMENT en JSON :
[{{"id":"...","label":"Professionnel","urgence":"Urgent"}}]
Labels: Professionnel, Personnel, Factures, Newsletter   ← modifie ici
Urgence: Urgent, Normal, Peut attendre                   ← modifie ici
```

---

## 🐛 Résolution de problèmes

### `Failed to fetch` dans l'interface

Le serveur Flask ne tourne pas. Lance :
```bash
python3 app.py
```
Garde ce terminal ouvert pendant l'utilisation.

### `Error 403: access_denied` lors de l'auth Google

Tu n'es pas dans les utilisateurs test. Va sur [console.cloud.google.com](https://console.cloud.google.com) → **Écran de consentement OAuth** → **Utilisateurs test** → ajoute ton adresse Gmail.

### `Only user and assistant roles are supported`

Le modèle chargé dans LM Studio ne supporte pas le function calling. Charge **Qwen2.5-7B-Instruct** depuis la communauté lmstudio-community.

### `n_keep >= n_ctx` (contexte dépassé)

Trop d'emails envoyés au modèle d'un coup. Dans `app.py` :
```python
taille_lot = 5   # Réduis à 5 au lieu de 10
```
Ou augmente le contexte dans LM Studio (voir section ci-dessus).

### `token.json` expiré

Supprime `token.json` et relance l'auth :
```bash
rm token.json
python3 auth_gmail.py
```

---

## 🔒 Sécurité & vie privée

- **100% local** : le LLM tourne sur ta machine, tes emails ne quittent jamais ton ordinateur
- **OAuth 2.0** : l'authentification Gmail est sécurisée via le protocole standard Google
- **Scope limité** : seul le scope `gmail.modify` est demandé (lecture + modification, pas suppression)
- **Aucune télémétrie** : aucune donnée n'est envoyée à des services tiers

---

## 🗺️ Roadmap

- [ ] Résumé quotidien automatique par email
- [ ] Connexion Google Calendar (créer des événements depuis les emails)
- [ ] Connexion LinkedIn (rédiger des messages de prospection)
- [ ] Réponses automatiques avec brouillons Gmail
- [ ] Filtrage et suppression des newsletters
- [ ] Support multi-comptes Gmail
- [ ] Mode planificateur (lancer des tâches à heure fixe)

---

## 📚 Ressources utiles

- [LM Studio](https://lmstudio.ai) — interface pour modèles LLM locaux
- [Gmail API Docs](https://developers.google.com/gmail/api) — documentation officielle
- [Google Cloud Console](https://console.cloud.google.com) — gestion des credentials
- [Flask Docs](https://flask.palletsprojects.com) — documentation Flask
- [OpenAI Python SDK](https://github.com/openai/openai-python) — utilisé pour l'API LM Studio

---

## 📄 Licence

MIT License — libre d'utilisation, modification et distribution.

---

*Projet réalisé dans le cadre d'un apprentissage des agents IA locaux.*# agent_gmail
