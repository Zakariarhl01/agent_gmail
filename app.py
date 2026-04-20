from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64
from datetime import datetime

app = Flask(__name__, static_folder=".")
CORS(app)

# ─── Connexion LM Studio ─────────────────────────────────────────────────────
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# ─── Connexion Gmail ─────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    return build("gmail", "v1", credentials=creds)

service = get_gmail_service()

# ─── Fonctions Gmail ─────────────────────────────────────────────────────────
def lire_emails(nombre=5, depuis=None):
    query = f"after:{depuis}" if depuis else ""
    results = service.users().messages().list(
        userId="me", maxResults=nombre, labelIds=["INBOX"], q=query
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
        emails.append({"id": msg["id"], "sujet": sujet, "expediteur": expediteur, "corps": corps[:500]})
    return emails

def marquer_lu(email_id):
    service.users().messages().modify(
        userId="me", id=email_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    return f"Email {email_id} marqué comme lu"

def envoyer_email(destinataire, sujet, corps):
    message = f"To: {destinataire}\nSubject: {sujet}\n\n{corps}"
    encoded = base64.urlsafe_b64encode(message.encode()).decode()
    service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    return f"Email envoyé à {destinataire}"

def creer_label(nom):
    try:
        label = service.users().labels().create(userId="me", body={"name": nom}).execute()
        return label["id"]
    except Exception:
        labels = service.users().labels().list(userId="me").execute()
        for l in labels["labels"]:
            if l["name"].lower() == nom.lower():
                return l["id"]
        return None

def appliquer_label(email_id, label_id):
    try:
        service.users().messages().modify(
            userId="me", id=email_id, body={"addLabelIds": [label_id]}
        ).execute()
        return True
    except Exception:
        return False

def lister_labels():
    results = service.users().labels().list(userId="me").execute()
    return [{"id": l["id"], "nom": l["name"]} for l in results.get("labels", [])]

# ─── Détection ───────────────────────────────────────────────────────────────
def detecter_date(message):
    msg = message.lower()
    now = datetime.now()
    from datetime import timedelta

    mois = {"janvier":"01","février":"02","mars":"03","avril":"04","mai":"05","juin":"06",
            "juillet":"07","août":"08","septembre":"09","octobre":"10","novembre":"11","décembre":"12"}

    # "cette semaine" → priorité absolue avant les mois
    if "semaine" in msg:
        return (now - timedelta(days=7)).strftime("%Y/%m/%d")

    # "aujourd'hui"
    if "aujourd" in msg:
        return now.strftime("%Y/%m/%d")

    annee = str(now.year)
    for a in ["2025","2026"]:
        if a in msg: annee = a; break

    # Cherche un mois explicite
    for nom, num in mois.items():
        if nom in msg: return f"{annee}/{num}/01"

    # "ce mois" ou "mois-ci"
    if "ce mois" in msg or "mois-ci" in msg:
        return now.strftime("%Y/%m/01")

    # "cette année"
    if "cette année" in msg:
        return f"{annee}/01/01"

    return None

def detecter_intention(message):
    mots = ["trie","classe","range","catégorie","label","organise","trier","classer"]
    return "triage" if any(m in message.lower() for m in mots) else "general"

# ─── Outils agent ────────────────────────────────────────────────────────────
tools = [
    {"type": "function", "function": {
        "name": "lire_emails",
        "description": "Lit les derniers emails Gmail",
        "parameters": {"type": "object", "properties": {
            "nombre": {"type": "integer", "description": "Nombre d'emails"}
        }}
    }},
    {"type": "function", "function": {
        "name": "marquer_lu",
        "description": "Marque un email comme lu",
        "parameters": {"type": "object", "properties": {
            "email_id": {"type": "string"}
        }, "required": ["email_id"]}
    }},
    {"type": "function", "function": {
        "name": "envoyer_email",
        "description": "Envoie un email",
        "parameters": {"type": "object", "properties": {
            "destinataire": {"type": "string"},
            "sujet": {"type": "string"},
            "corps": {"type": "string"}
        }, "required": ["destinataire", "sujet", "corps"]}
    }}
]

def execute_tool(name, arguments):
    if name == "lire_emails":
        emails = lire_emails(arguments.get("nombre", 5))
        return json.dumps(emails, ensure_ascii=False)
    elif name == "marquer_lu":
        return marquer_lu(arguments["email_id"])
    elif name == "envoyer_email":
        return envoyer_email(arguments["destinataire"], arguments["sujet"], arguments["corps"])
    return "Outil inconnu"

# ─── Routes Flask ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    intention = detecter_intention(message)

    logs = []

    def log(msg, type="info"):
        logs.append({"text": msg, "type": type})

    if intention == "triage":
        depuis = detecter_date(message)
        nombre = 20
        for w in message.split():
            if w.isdigit(): nombre = int(w); break

        if depuis:
            log(f"📅 Filtre détecté : depuis le {depuis}", "info")

        log(f"📬 Lecture des emails{' depuis ' + depuis if depuis else ''}...", "info")
        emails = lire_emails(nombre, depuis)

        if not emails:
            log("📭 Aucun email trouvé.", "warning")
            return jsonify({"logs": logs})

        log(f"✅ {len(emails)} emails récupérés", "success")

        classifications = []
        taille_lot = 10
        lots = [emails[i:i+taille_lot] for i in range(0, len(emails), taille_lot)]

        for i, lot in enumerate(lots):
            log(f"🧠 Classification lot {i+1}/{len(lots)}...", "info")
            prompt_emails = [{"id": e["id"], "sujet": e["sujet"], "expediteur": e["expediteur"][:30], "corps": e["corps"][:50]} for e in lot]
            resp = client.chat.completions.create(
                model="local-model",
                messages=[{"role": "user", "content": f"""Classe ces {len(lot)} emails. Réponds UNIQUEMENT en JSON :
[{{"id":"...","label":"Professionnel","urgence":"Urgent"}}]
Labels: Professionnel, Personnel, Factures, Newsletter
Urgence: Urgent, Normal, Peut attendre
Emails: {json.dumps(prompt_emails, ensure_ascii=False)}"""
                }]
            )
            content = resp.choices[0].message.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"): content = content[4:]
            try:
                classifications.extend(json.loads(content))
                log(f"   ✅ Lot {i+1} classifié", "success")
            except Exception as e:
                log(f"   ❌ Erreur lot {i+1}: {e}", "error")

        if not classifications:
            log("❌ Aucune classification obtenue.", "error")
            return jsonify({"logs": logs})

        labels_necessaires = set(c.get("label","Personnel") for c in classifications) | set(c.get("urgence","Normal") for c in classifications)
        label_ids = {}
        for nom in labels_necessaires:
            lid = creer_label(nom)
            if lid: label_ids[nom] = lid

        log(f"🏷️  Labels créés : {', '.join(label_ids.keys())}", "info")

        for c in classifications:
            email_id = c["id"]
            sujet = next((e["sujet"] for e in emails if e["id"] == email_id), "?")
            for key in ["label","urgence"]:
                nom = c.get(key)
                if nom and nom in label_ids:
                    appliquer_label(email_id, label_ids[nom])
            urgence = c.get("urgence","?")
            label = c.get("label","?")
            tag = "urgent" if urgence == "Urgent" else "normal"
            log(f"📧 [{urgence}][{label}] {sujet[:60]}", tag)

        log(f"✅ Triage terminé ! {len(classifications)} emails classés.", "success")

    else:
        messages = [{"role": "user", "content": f"Tu es un assistant Gmail. Réponds en français.\nDemande : {message}"}]
        for _ in range(10):
            resp = client.chat.completions.create(model="local-model", messages=messages, tools=tools, tool_choice="auto")
            msg = resp.choices[0].message
            finish = resp.choices[0].finish_reason
            if finish == "stop":
                log(f"🤖 {msg.content}", "agent")
                break
            if finish == "tool_calls":
                messages.append(msg)
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    log(f"🔧 Outil utilisé : {name}", "info")
                    result = execute_tool(name, args)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return jsonify({"logs": logs})

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")