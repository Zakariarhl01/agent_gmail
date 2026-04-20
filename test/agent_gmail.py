from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64
from datetime import datetime

# --- Connexion LM Studio ---
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)

# --- Connexion Gmail ---
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

service = get_gmail_service()

# --- Outils Gmail ---
def lire_emails(nombre=5, depuis=None):
    query = ""
    if depuis:
        query = f"after:{depuis}"

    results = service.users().messages().list(
        userId="me",
        maxResults=nombre,
        labelIds=["INBOX"],
        q=query
    ).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        txt = service.users().messages().get(userId="me", id=msg["id"]).execute()
        payload = txt["payload"]
        headers = payload["headers"]

        sujet = next((h["value"] for h in headers if h["name"] == "Subject"), "Sans sujet")
        expediteur = next((h["value"] for h in headers if h["name"] == "From"), "Inconnu")

        corps = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    corps = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    break
        elif "body" in payload:
            data = payload["body"].get("data", "")
            corps = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        emails.append({
            "id": msg["id"],
            "sujet": sujet,
            "expediteur": expediteur,
            "corps": corps[:500]
        })

    return json.dumps(emails, ensure_ascii=False)

def marquer_lu(email_id):
    service.users().messages().modify(
        userId="me",
        id=email_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    return f"Email {email_id} marqué comme lu"

def envoyer_email(destinataire, sujet, corps):
    message = f"To: {destinataire}\nSubject: {sujet}\n\n{corps}"
    encoded = base64.urlsafe_b64encode(message.encode()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": encoded}
    ).execute()
    return f"Email envoyé à {destinataire}"

def creer_label(nom):
    try:
        label = service.users().labels().create(
            userId="me",
            body={"name": nom}
        ).execute()
        return f"Label '{nom}' créé avec l'id: {label['id']}"
    except Exception as e:
        labels = service.users().labels().list(userId="me").execute()
        for l in labels["labels"]:
            if l["name"].lower() == nom.lower():
                return f"Label '{nom}' existe déjà avec l'id: {l['id']}"
        return f"Erreur: {e}"

def appliquer_label(email_id, label_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=email_id,
            body={"addLabelIds": [label_id]}
        ).execute()
        return f"Label appliqué à l'email {email_id}"
    except Exception as e:
        return f"Erreur: {e}"

def lister_labels():
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    return json.dumps([{"id": l["id"], "nom": l["name"]} for l in labels], ensure_ascii=False)

# --- Outils pour l'agent générique ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "lire_emails",
            "description": "Lit les derniers emails de la boîte de réception Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "integer",
                        "description": "Nombre d'emails à récupérer (défaut: 5)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "marquer_lu",
            "description": "Marque un email comme lu",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "L'ID de l'email à marquer comme lu"
                    }
                },
                "required": ["email_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "envoyer_email",
            "description": "Envoie un email via Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinataire": {"type": "string", "description": "Adresse email du destinataire"},
                    "sujet": {"type": "string", "description": "Sujet de l'email"},
                    "corps": {"type": "string", "description": "Contenu de l'email"}
                },
                "required": ["destinataire", "sujet", "corps"]
            }
        }
    }
]

# --- Exécution des outils ---
def execute_tool(name, arguments):
    if name == "lire_emails":
        return lire_emails(arguments.get("nombre", 5))
    elif name == "marquer_lu":
        return marquer_lu(arguments["email_id"])
    elif name == "envoyer_email":
        return envoyer_email(arguments["destinataire"], arguments["sujet"], arguments["corps"])
    return "Outil inconnu"

# --- Détection de date dans le message ---
def detecter_date(message):
    msg = message.lower()
    now = datetime.now()

    # Mois en français
    mois = {
        "janvier": "01", "février": "02", "mars": "03", "avril": "04",
        "mai": "05", "juin": "06", "juillet": "07", "août": "08",
        "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
    }

    # Cherche une année explicite (2025 ou 2026)
    annee = str(now.year)
    for a in ["2025", "2026"]:
        if a in msg:
            annee = a
            break

    # Cherche un mois explicite
    for nom_mois, num_mois in mois.items():
        if nom_mois in msg:
            return f"{annee}/{num_mois}/01"

    # "ce mois" ou "ce mois-ci"
    if "ce mois" in msg or "mois-ci" in msg:
        return now.strftime("%Y/%m/01")

    # "cette année" ou "début de l'année"
    if "cette année" in msg or "début de l'année" in msg:
        return f"{annee}/01/01"

    # "semaine" → 7 jours en arrière
    if "semaine" in msg or "cette semaine" in msg:
        from datetime import timedelta
        date = now - timedelta(days=7)
        return date.strftime("%Y/%m/%d")

    return None

# --- Agent triage (logique contrôlée par Python) ---
def run_agent_gmail_triage(nombre=100, depuis=None):
    if depuis:
        print(f"\n📬 Lecture des emails depuis {depuis}...\n")
    else:
        print(f"\n📬 Lecture de {nombre} emails...\n")

    # Étape 1 : lire les emails
    emails_json = lire_emails(nombre, depuis)
    emails = json.loads(emails_json)

    if not emails:
        print("📭 Aucun email trouvé pour cette période.")
        return

    print(f"✅ {len(emails)} emails récupérés\n")

    # Étape 2 : classification par lots de 50
    classifications = []
    taille_lot = 50
    lots = [emails[i:i+taille_lot] for i in range(0, len(emails), taille_lot)]

    for i, lot in enumerate(lots):
        print(f"🧠 Classification lot {i+1}/{len(lots)} ({len(lot)} emails)...")

        emails_pour_prompt = [
            {"id": e["id"], "sujet": e["sujet"], "expediteur": e["expediteur"], "corps": e["corps"][:200]}
            for e in lot
        ]

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {
                    "role": "user",
                    "content": f"""Voici {len(lot)} emails. Pour chacun, donne-moi UNIQUEMENT un JSON avec ce format :
[
  {{"id": "id_email", "label": "Professionnel", "urgence": "Urgent"}},
  ...
]

Labels possibles : Professionnel, Personnel, Factures, Newsletter
Urgence possible : Urgent, Normal, Peut attendre

Emails :
{json.dumps(emails_pour_prompt, ensure_ascii=False)}

Réponds UNIQUEMENT avec le JSON, rien d'autre."""
                }
            ]
        )

        content = response.choices[0].message.content.strip()

        # Nettoie le JSON si le modèle ajoute des backticks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        try:
            lot_classifications = json.loads(content)
            classifications.extend(lot_classifications)
            print(f"   ✅ Lot {i+1} classifié\n")
        except Exception as e:
            print(f"   ❌ Erreur lot {i+1} : {e}")
            print(f"   Réponse : {content[:200]}")

    if not classifications:
        print("❌ Aucune classification obtenue.")
        return

    print(f"✅ {len(classifications)} emails classifiés\n")

    # Étape 3 : créer les labels
    labels_necessaires = set()
    for c in classifications:
        labels_necessaires.add(c.get("label", "Personnel"))
        labels_necessaires.add(c.get("urgence", "Normal"))

    label_ids = {}
    for nom in labels_necessaires:
        creer_label(nom)
        tous_labels = json.loads(lister_labels())
        for l in tous_labels:
            if l["nom"].lower() == nom.lower():
                label_ids[nom] = l["id"]
                break

    print(f"🏷️  Labels prêts : {list(label_ids.keys())}\n")

    # Étape 4 : appliquer les labels
    for c in classifications:
        email_id = c["id"]
        sujet = next((e["sujet"] for e in emails if e["id"] == email_id), "?")

        for key in ["label", "urgence"]:
            nom = c.get(key)
            if nom and nom in label_ids:
                appliquer_label(email_id, label_ids[nom])

        print(f"📧 [{c.get('urgence', '?')}][{c.get('label', '?')}] {sujet}")

    print(f"\n✅ Triage terminé ! {len(classifications)} emails classés.")

# --- Agent générique ---
def run_agent(user_message):
    messages = [
        {
            "role": "user",
            "content": f"""Tu es un assistant personnel qui gère les emails Gmail.
Tu peux lire, résumer et envoyer des emails.
Réponds toujours en français.

Demande : {user_message}"""
        }
    ]
    print(f"\n👤 User: {user_message}\n")

    for _ in range(10):
        response = client.chat.completions.create(
            model="local-model",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "stop":
            print(f"🤖 Agent: {message.content}")
            return message.content

        if finish_reason == "tool_calls":
            messages.append(message)
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                print(f"🔧 Outil : {name}({arguments})")
                result = execute_tool(name, arguments)
                print(f"   → OK\n")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

    print("⚠️ Nombre maximum d'itérations atteint")

# --- Détection automatique de l'intention ---
def detecter_intention(message):
    mots_triage = ["trie", "classe", "range", "catégorie", "label", "organise", "trier", "classer"]
    for mot in mots_triage:
        if mot in message.lower():
            return "triage"
    return "general"

# --- Boucle principale ---
print("🤖 Agent Gmail prêt ! (tape 'quit' pour quitter)\n")
print("💡 Exemples :")
print("   - 'trie mes mails depuis le début d'avril 2026'")
print("   - 'trie mes mails de cette semaine'")
print("   - 'trie mes 20 derniers mails'")
print("   - 'lis mes 5 derniers emails'")
print("   - 'envoie un email à ...'")
print()

while True:
    user_input = input("👤 Toi: ")
    if user_input.lower() == "quit":
        break

    intention = detecter_intention(user_input)

    if intention == "triage":
        depuis = detecter_date(user_input)
        nombre = 100

        # Extrait un nombre explicite si mentionné
        for word in user_input.split():
            if word.isdigit():
                nombre = int(word)
                break

        if depuis:
            print(f"📅 Filtre détecté : depuis le {depuis}")

        run_agent_gmail_triage(nombre, depuis)
    else:
        run_agent(user_input)