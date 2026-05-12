
# REVIEWSCAN – CORE API (SINGLE SOURCE OF TRUTH)
# reviewscan_api.py — MOCK-MODE READY + MODE SUPPORT (review / scam)
# + REPORT DOWNLOAD (TXT) ✅
# + TEST PAGE WITHOUT JSON OUTPUT ✅

from flask import Flask, request, jsonify, abort, make_response, Response
from flask_cors import CORS
from dotenv import load_dotenv
import os, uuid, datetime, json, re

from trust_engine_v2.analyzers.review_analyzer  import analyze_review_text
from trust_engine_v2.analyzers.scam_analyzer import analyze_scam_text
from trust_engine_v2.result_model import create_result
from trust_engine_v2.response_builder import build_response

load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Config ---
MOCK_MODE = os.getenv("MOCK_MODE", "1") in ("1", "true", "True", "yes", "on")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # mag leeg zijn in mock

# --- Mini storage (verdwijnt bij restart) ---
STORE = {} # {id: {mode, text, result, created_at}}

# =========================
# MOCK MODULE: REVIEW
# =========================

ISSUE_PATTERNS = {

    # 🍽️ HORECA
    "bediening": ["bediening", "service", "personeel", "onvriendelijk", "traag", "niet geholpen"],
    "eten_kwaliteit": ["koud eten", "slecht eten", "niet lekker", "rauw", "verbrand", "smakeloos"],
    "prijs_waarde": ["te duur", "prijs", "waarde", "overpriced", "veel te duur", "prijs kwaliteit"],
    "hygiëne": ["vuil", "dirty", "onhygiënisch", "smerig", "vuile tafels", "vuile toiletten"],
    "wachttijd_horeca": ["lang wachten", "40 minuten", "duurde lang", "niet bediend"],

    # 🏥 MEDISCH / ORTHOPEDIE
    "communicatie": ["geen reactie", "niet bereikbaar", "geen antwoord", "niet teruggebeld", "genegeerd"],
    "administratie": ["factuur", "aanmaning", "kosten", "verkeerd aangerekend", "extra kosten", "10,5%"],
    "opvolging": ["geen opvolging", "niet opgevolgd", "geen feedback", "niet gecontacteerd"],
    "wachttijd": ["lange wachttijd", "vertraging", "te laat geholpen", "lang moeten wachten"],
    "professionaliteit": ["onprofessioneel", "respectloos", "onbeleefd", "niet correct behandeld"],

    # 🔧 DIENSTVERLENING (algemeen)
    "afspraken": ["afspraak", "niet nagekomen", "te laat", "niet komen opdagen", "afgezegd"],
    "kwaliteit_werk": ["slecht werk", "fout uitgevoerd", "problemen", "niet opgelost", "half werk"],
    "nazorg": ["geen service na", "geen garantie", "niet opgelost na klacht"],
   
    # ⚖️ RISICO / REPUTATIE
    "vertrouwen": ["oplichting", "boeven", "fraude", "niet te vertrouwen", "pas op", "opgepast"],
    "frustratie": ["nooit meer", "zeer slecht", "dramatisch", "verschrikkelijk", "hopeloos"],
    "waarschuwing": ["pas op", "raad af", "niet doen", "grote fout", "vermijden"],

    # 💬 EMOTIE / TONE
    "boos": ["boos", "kwaad", "woedend"],
    "teleurgesteld": ["teleurgesteld", "jammer", "spijtig"],
    "agressief": ["boeven", "schandalig", "belachelijk"]
}

def extract_labels(text: str, patterns):
    hits = set()

    if isinstance(patterns, dict):
        for label, words in patterns.items():
            if any(word in text for word in words):
                hits.add(label)
    else:
        for label, rx in patterns:
            if rx.search(text):
                hits.add(label)

    return sorted(hits)

negative_words_nl = [
"slecht","vreselijk","verschrikkelijk","teleurstellend","schandalig",
"nooit meer","kom hier nooit meer","geen aanrader","af te raden",
"lang wachten","te lang wachten","wachttijd","traag","heel traag",
"koud","eten koud","lauw eten","niet warm",
"vies","vuile","onhygiënisch","onproper",
"onvriendelijk","onbeleefd","slechte bediening","slechte service",
"duur","te duur","prijs te hoog","overpriced",
"niet lekker","smaakt niet","slechte kwaliteit",
"teleurgesteld","erg teleurgesteld","valt tegen","tegengevallen",
"slechte ervaring","geen goede ervaring"
]

negative_words_en = [
"bad","very bad","really bad","terrible","awful","horrible",
"worst","worst ever","never again","not recommended",
"long wait","waited too long","waiting time","very slow","slow service",
"cold","food was cold","not warm",
"dirty","filthy","not clean",
"rude","very rude","unfriendly","bad service","poor service",
"expensive","too expensive","overpriced",
"not good","not tasty","bad quality","poor quality",
"disappointed","very disappointed","let down",
"bad experience","terrible experience"
]
def mock_analyze_review(text: str) -> dict:
    t = (text or "").strip()
    tl = t.lower()

    neg = any(w in tl for w in negative_words_nl + negative_words_en)
   
   
    pos = any(w in tl for w in [
        "heerlijk","vriendelijk","top","fantastisch","aanrader","lekker","snel geholpen"
    ])

    if neg and not pos:
        sentiment = "negatief"
    elif pos and not neg:
        sentiment = "positief"
    else:
        sentiment = "neutraal"

    toontype = "boos, beschuldigend" if ("nooit meer" in tl or "schandalig" in tl) else ("positief" if sentiment=="positief" else "neutraal")
    issues = extract_labels(tl, ISSUE_PATTERNS)

    # Empathische mock-reactie
    if sentiment == "negatief":
        parts = []
        if "lange wachttijd" in issues:
            wait_match = re.search(r"(\d{1,3})\s*min", tl)
            wait_txt = f"{wait_match.group(1)} minuten " if wait_match else ""
            parts.append(f"Het spijt ons te horen dat u {wait_txt}hebt moeten wachten.")
        if "bediening" in issues:
            parts.append("We nemen uw feedback over de bediening zeer serieus en bespreken dit intern met het team om onze service te verbeteren.")
        if "koud eten" in issues:
            parts.append("Dat uw gerecht koud was, is niet de standaard die wij nastreven.")
        if not parts:
            parts.append("Bedankt voor uw feedback. Het spijt ons dat uw ervaring niet goed was. We bekijken dit intern, en we streven constant verbetering na. Uw ervaring helpt ons om onze service naar u verder te verfijnen. Neem gerust persoonlijk contact met ons op zodat we dit samen kunnen bekijken.")

        parts.append("Als u wil, stuur ons kort meer details (datum/uur) zodat we dit kunnen rechtzetten.")
        response_suggestion = "⚠️ " + " ".join(parts)
    elif sentiment == "positief":
        response_suggestion = "✅ Dank u wel voor uw positieve review! We hopen u snel opnieuw te verwelkomen."
    else:
        response_suggestion = "ℹ️ Bedankt voor uw feedback. We nemen dit mee in onze verbetering."

    # Betrouwbaarheid (menselijk)
    if sentiment in ("positief", "negatief"):
        trust = "Betrouwbaar"
    else:
        trust = "Extra controle aanbevolen"

    return {
        "mode": "review",
        "text": text,
        "sentiment": sentiment,
        "toontype": toontype,
        "labels": issues,
        "trust_level": trust,
        "summary": f"Review-analyse: {sentiment}. Signalen: {', '.join(issues) or 'geen duidelijke signalen'}",
        "response_suggestion": response_suggestion,
        "engine": "mock",
    }


# =========================
# MOCK MODULE: SCAM
# =========================

SCAM_PATTERNS = [
    # Urgentie / druk
    ("urgent", re.compile(r"\b(dringend|meteen|nu|onmiddellijk|direct|asap|laatste kans|binnen \d+\s*(min|minuten|uur|uren))\b")),

    # Dreiging / intimidatie / legal
    ("dreiging", re.compile(r"\b(geblokkeerd|geschorst|afsluiten|gedeactiveerd|bevroren|in beslag|arrest|dagvaarding)\b")),
    ("politie/justitie", re.compile(r"\b(politie|federale politie|interpol|justitie|parket|gerecht|rechtbank)\b")),
    ("boete/incasso", re.compile(r"\b(boete|incasso|deurwaarder|aanmaning|vordering|openstaand bedrag|achterstallig)\b")),

    # Identiteit / inloggen / account
    ("account", re.compile(r"\b(account|profiel|login|inlog|aanmelden|wachtwoord|password|gebruikersnaam)\b")),
    ("2fa/otp", re.compile(r"\b(otp|2fa|authenticator|sms\s*code|verificatiecode|bevestigingscode|pincode)\b")),
    ("reset", re.compile(r"\b(reset|herstel|recovery|opnieuw instellen)\b")),

    # Persoonlijke gegevens / KYC
    ("gegevens", re.compile(r"\b(identiteitskaart|paspoort|rijbewijs|bsn|rrn|bankkaartnummer|kaartnummer|cvv|cvc)\b")),
    ("kyc", re.compile(r"\b(kyc|verificatie|verifieer|identiteit bevestigen|bewijs van adres)\b")),

    # Links / domeinen / verkorte links
    ("link", re.compile(r"(http[s]?://|www\.|bit\.ly|tinyurl|t\.co|goo\.gl|qr\s*code|scan\s*de\s*code)")),
    ("klik-hier", re.compile(r"\b(klik hier|open link|bezoek deze pagina|log hier in)\b")),

    # Betaling / geld / cadeaubonnen
    ("codes", re.compile(r"\b(code|persoonlijke\s=+code|beveiligingscode|codes|toegangscode)\b")),
    ("betaling", re.compile(r"\b(betaal|overschrijving|storten|bijbetalen|factuur|betaling bevestigen|transactie)\b")),
    ("giftcards", re.compile(r"\b(giftcard|cadeaukaart|apple gift card|google play card|steam kaart)\b")),
    ("crypto-betaling", re.compile(r"\b(bitcoin|btc|ethereum|eth|usdt|wallet|seed phrase|mnemonic|private key)\b")),
    ("betaaldienst", re.compile(r"\b(paypal|revolut|wise|western union|moneygram|payconiq)\b")),

    # Te mooi om waar te zijn
    ("te-mooi", re.compile(r"\b(gratis geld|verdien\s*snel|snel rijk|garantie|100% zeker|risicoloos|dubbel terug)\b")),
    ("winnaar", re.compile(r"\b(winnaar|lotto|loterij|prijs gewonnen|jackpot|giveaway)\b")),

    # Impersonatie / bekende merken / instanties
    ("bank", re.compile(r"\b(ing|kbc|belfius|bnpp|fortis|rabobank|abn|sns|bank)\b")),
    ("overheid", re.compile(r"\b(overheid|fiscus|belastingdienst|financi[eë]n|douane|gemeente|stad)\b")),
    ("tech-merken", re.compile(r"\b(microsoft|apple|google|amazon|netflix|facebook|meta|instagram|whatsapp)\b")),
    ("bezorging", re.compile(r"\b(bpost|postnl|dhl|dpd|gls|ups|fedex|track\s*en\s*trace|pakket)\b")),

    # “Support” / remote access scams
    ("support", re.compile(r"\b(helpdesk|klantenservice|support|service desk|technische dienst)\b")),
    ("remote", re.compile(r"\b(teamviewer|anydesk|remote|scherm delen|installeren)\b")),

    # Romance / sociale manipulatie
    ("romance", re.compile(r"\b(schat|lief|babe|ik hou van je|vertrouw me|alleen jij)\b")),
    ("afschermen", re.compile(r"\b(hou dit geheim|zeg het aan niemand|discreet|privé)\b")),

    # Job/Investment scams
    ("job", re.compile(r"\b(thuiswerk|remote job|vacature|salaris|loon|sollicitatie)\b")),
    ("investment", re.compile(r"\b(investeer|investering|trading|broker|rendement|profit|roi)\b")),
    ("ponzi", re.compile(r"\b(verdien per dag|upline|downline|referral|invite code|affiliate)\b")),

    # Taalpatronen die vaak scam zijn
    ("taalfouten", re.compile(r"\b(geachte klant|beste gebruiker|uw account)\b")),
    ("druk-zinnen", re.compile(r"\b(om problemen te voorkomen|om verdere schade te voorkomen|handel nu)\b")),
]

def mock_analyze_scam(text: str) -> dict:
    t = (text or "").strip()
    tl = t.lower()

    labels = extract_labels(tl, SCAM_PATTERNS)

    score = 0
    weights = {
        "urgentie": 4, "dreiging": 4, "bank/overheid": 3, "link/klik": 4,
        "inlog/gegevens": 7, "betaling": 4, "codes": 8, "te mooi": 4, "doet alsof": 4
    }
    for lb in labels:
        score += weights.get(lb, 1)

    # Betrouwbaarheid (menselijk)
    if score >= 8:
        trust = "Onbetrouwbaar"
    elif score >= 4:
        trust = "Extra controle aanbevolen"
    else:
        trust = "Betrouwbaar"

    if trust == "Onbetrouwbaar":
        summary = "Sterk verdacht: meerdere klassieke phishing/oplichting-signalen."
        response_suggestion = (
            "🚫 Dit lijkt sterk op oplichting. Klik niet op links, deel geen codes/gegevens en betaal niets. "
            "Verifieer via de officiële website/telefoon (zelf opzoeken)."
        )
    elif trust == "Extra controle aanbevolen":
        summary = "Mogelijk verdacht: er zijn enkele risico-signalen."
        response_suggestion = (
            "⚠️ Wees voorzichtig: deel geen gegevens, controleer afzender en URL. "
            "Contacteer het bedrijf via officiële kanalen."
        )
    else:
        summary = "Weinig duidelijke oplichtingssignalen gevonden in deze tekst."
        response_suggestion = "✅ Lijkt niet sterk verdacht op basis van tekst alleen. Blijf alert."

    return {
        "mode": "scam",
        "text": text,
        "labels": labels,
        "trust_level": trust,
        "summary": summary,
        "response_suggestion": response_suggestion,
        "engine": "mock",
    }


# =========================
# OPTIONAL: ECHTE AI (later)
# =========================

def try_real_ai(mode: str, text: str) -> dict:
    """
    Optioneel: echte AI. Valt automatisch terug op mock bij fouten.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("No API key")

    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    if mode == "review":
        prompt = (
            "Analyseer deze bedrijfsreview en geef uitsluitend geldige JSON terug met velden: "
            '{"mode","sentiment","toontype","labels","trust_level","summary","response_suggestion"} '
            f'Tekst: """{text}"""'
        )
    else:
        prompt = (
            "Analyseer deze tekst op phishing/oplichting en geef uitsluitend geldige JSON terug met velden: "
            '{"mode","labels","trust_level","summary","response_suggestion"} '
            f'Tekst: """{text}"""'
        )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Je antwoordt alleen met geldige JSON in het Nederlands."},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(resp.choices[0].message.content.strip())
    data["engine"] = "openai"
    return data


# =========================
# ROUTER
# =========================

def analyze_text(mode: str, text: str) -> dict:
    print("BACKEND MODE RAW:",mode)
    # ============================
    # MODE NORMALISATIE
    # ============================
    mode = (mode or "review").strip().lower()
    if mode not in ("review", "scam"):
        mode = "review"

    # ============================
    # CORE ANALYSE (blijft hetzelfde)
    # ============================
    if mode == "scam":
        raw = analyze_scam_text(
            text,
            MOCK_MODE,
            try_real_ai,
            mock_analyze_scam
        )
    else:
        raw = analyze_review_text(
            text,
            MOCK_MODE,
            try_real_ai,
            mock_analyze_review
        )

    # =====================================
    # 🔥 BESLISSING LOGICA (UPGRADE V2)
    # =====================================

    score = 0
    text_lower = text.lower()
    detected = []

    # 🔴 KRITIEKE SIGNALEN (zwaar)
    critical = [
        "pincode", "pin code", "wachtwoord", "bankgegevens",
        "reset wachtwoord", "login bevestigen",
        "bitcoin", "crypto", "wallet",
        "stuur geld", "betaling", "overschrijving"
    ]

    # 🟠 URGENTIE SIGNALEN (druk)
    urgency = [
        "urgent", "onmiddellijk", "nu", "dringend",
        "laatste kans", "actie vereist"
    ]

    # 🟡 CONTEXT SIGNALEN (typische scam context)
    context = [
        "account geblokkeerd", "toegang geblokkeerd",
        "verifieer", "bevestig", "login",
        "bank", "itsme", "paypal", "kbc", "belfius",
        "bpost", "postnl", "dhl", "pakket"
    ]

    # ============================
    # 🔎 SCORING
    # ============================

    for word in critical:
        if word in text_lower:
            score += 3
            detected.append(word)

    for word in urgency:
        if word in text_lower:
            score += 1
            detected.append(word)

    for word in context:
        if word in text_lower:
            score += 1
            detected.append(word)

    # ============================
    # 🎯 BESLISSING
    # ============================

    # BESLISSING
    if mode == "scam":
        if score >= 5:
            result = create_result("high", detected, "scam")
        elif score >= 2:
            result = create_result("medium", detected, "scam")
        else:
            result = create_result("low", ["generic scam pattern"], "scam")

    else:
        if score >= 5:
            result = create_result("high", detected, "review")
        elif score >= 2:
            result = create_result("medium", detected, "review")
        else:
            result = create_result("low", ["generic language"], "review")

    # ============================
    # RESPONSE
    # ============================

    response = build_response(result)
    return response
# =========================
# REPORT BUILDER (TXT)
# =========================

def build_report_text(item: dict) -> str:
    """
    Maakt een nette TXT-rapportstring op basis van opgeslagen STORE item.
    """
    rid = item.get("id", "")
    created = item.get("created_at", "")
    mode = item.get("mode", "")
    text = item.get("text", "")
    r = item.get("result", {}) or {}

    lines = []
    lines.append("REVIEWSCAN RAPPORT")
    lines.append("=" * 50)
    lines.append(f"ID: {rid}")
    lines.append(f"Datum (UTC): {created}")
    lines.append(f"Mode: {mode}")
    lines.append(f"Engine: {r.get('engine','')}")
    lines.append("")
    lines.append("ORIGINELE TEKST")
    lines.append("-" * 50)
    lines.append(text)
    lines.append("")
    lines.append("ANALYSE")
    lines.append("-" * 50)
    if mode == "review":
        lines.append(f"Sentiment: {r.get('sentiment','')}")
        lines.append(f"Toontype: {r.get('toontype','')}")
    lines.append(f"Betrouwbaarheid: {r.get('trust_level','')}")
    labels = r.get("labels", [])
    lines.append(f"Signalen: {', '.join(labels) if labels else '—'}")
    lines.append(f"Samenvatting: {r.get('summary','')}")
    lines.append("")
    lines.append("VOORSTEL REACTIE / ADVIES")
    lines.append("-" * 50)
    lines.append(r.get("response_suggestion", ""))
    lines.append("")
    lines.append("TIP")
    lines.append("-" * 50)
    if mode == "review":
        lines.append("Gebruik de voorstelreactie als basis en blijf altijd beleefd en feitelijk.")
    else:
        lines.append("Deel nooit codes of gegevens. Verifieer altijd via officiële kanalen.")
    lines.append("")
    return "\n".join(lines)
def normalize_output(r: dict, mode: str) -> dict:
    labels = r.get("labels", [])
    trust = r.get("trust_level", "onbekend")

    return {
        "mode": mode,
        "sentiment": r.get("sentiment"),
        "toontype": r.get("toontype"),
        "trust_level": trust,
        "summary": r.get("summary", ""),
        "analysis": build_analysis(labels, trust, mode),
        "labels": labels,
        "response_suggestion": r.get("response_suggestion", ""),
        "next_steps": build_next_steps(mode, trust),
        "engine": r.get("engine", "mock")
    }


def build_analysis(labels, trust, mode):

    if not labels:
        return ["Geen duidelijke signalen gevonden."]

    out = []

    for l in labels:

        if l in ["bediening"]:
            out.append("Probleem met service of personeel.")

        elif l in ["wachttijd", "wachttijd_horeca"]:
            out.append("Er is sprake van lange wachttijden.")

        elif l in ["eten_kwaliteit"]:
            out.append("De kwaliteit van het product wordt negatief beoordeeld.")

        elif l in ["prijs_waarde"]:
            out.append("De prijs wordt als te hoog ervaren.")

        elif l in ["vertrouwen"]:
            out.append("Er zijn signalen van wantrouwen of beschuldigingen.")

        elif l == "urgent":
            out.append("De tekst probeert druk te zetten (urgentie).")

        elif l == "dreiging":
            out.append("Er wordt gedreigd om actie af te dwingen.")

        elif l in ["link", "klik-hier"]:
            out.append("Er zit een link in de tekst, mogelijk phishing.")

        elif l in ["betaling", "codes"]:
            out.append("Er wordt gevraagd om betaling of gevoelige informatie.")

        else:
            out.append(f"Signaal gedetecteerd: {l}")

    if trust == "Onbetrouwbaar":
        out.append("De combinatie van signalen wijst sterk op risico.")

    return out


def build_next_steps(mode, trust):

    if mode == "review":

        if trust == "Betrouwbaar":
            return [
                "Gebruik deze feedback intern.",
                "Verbeter waar nodig.",
                "Geen dringende actie nodig."
            ]
        else:
            return [
                "Controleer de review inhoud.",
                "Reageer professioneel.",
                "Rapporteer indien nodig."
            ]

    else:

        if trust == "Onbetrouwbaar":
            return [
                "Klik nergens op.",
                "Deel geen gegevens.",
                "Verwijder het bericht.",
                "Verifieer via officiële kanalen."
            ]

        elif trust == "Extra controle aanbevolen":
            return [
                "Controleer de afzender.",
                "Open links niet zomaar.",
                "Blijf voorzichtig."
            ]

        else:
            return [
                "Geen directe actie nodig.",
                "Blijf alert."
            ]

# =========================
# API ENDPOINTS
# =========================


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or data.get("review") or "").strip()
    mode = (data.get("mode") or "review").strip().lower()
    print("MODE ONTVANGEN:", mode)

    if not text:
        return jsonify({"error": "Missing field: 'text' (or 'review')"}), 400

    if mode == "scam":
        result = analyze_scam_text(
            text,
            MOCK_MODE,
            try_real_ai,
            mock_analyze_scam
        )
    else:
        result = analyze_review_text(
            text,
            MOCK_MODE,
            try_real_ai,
            mock_analyze_review
        )

    rid = uuid.uuid4().hex[:12]
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    STORE[rid] = {
        "id": rid,
        "mode": result.get("mode", mode),
        "text": text,
        "result": result,
        "created_at": created_at
    }

    response = build_response(result)

    return jsonify({
        "id": rid,
        "link": f"http://127.0.0.1:5000/r/{rid}",
        "report_link": f"http://127.0.0.1:5000/r/{rid}/report.txt",
        **result,
        "message": response.get("message"),
        "advice": response.get("advice")
})



# Backwards compatible endpoint
@app.route("/analyze_review", methods=["POST"])
def analyze_review_legacy():
    data = request.get_json(force=True, silent=True) or {}
    review = (data.get("review") or "").strip()

    if not review:
        return jsonify({"error": "Missing field: 'review'"}), 400

    result = analyze_review_text(
    review,
    MOCK_MODE,
    try_real_ai,
    mock_analyze_review
)

    rid = uuid.uuid4().hex[:12]
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    STORE[rid] = {"id": rid, "mode": "review", "text": review, "result": result, "created_at": created_at}

    return jsonify({
        "id": rid,
        "link": f"http://127.0.0.1:5000/r/{rid}",
        "report_link": f"http://127.0.0.1:5000/r/{rid}/report.txt",
        **result
    })


# =========================
# TEST PAGE (NO JSON DISPLAY)
# =========================

@app.route("/test", methods=["GET"])
def test_page():
    html = """"
    <html lang="nl">
<head>
  <meta charset="UTF-8">
  <title>ReviewScan – Test</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; max-width: 900px; }
    .row { display:flex; gap:12px; align-items:center; margin-bottom: 12px; flex-wrap: wrap; }
    select, textarea, button { font-size: 16px; }
    textarea { width:100%; height:120px; padding:10px; }
    button { padding:10px 16px; cursor:pointer; border-radius: 10px; border: 1px solid #ccc; background: #fff; }
    .card { border:1px solid #ddd; border-radius:12px; padding:16px; margin-top:16px; }
    .muted { color:#666; font-size: 0.9em; }
    .pill { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:600; }
    .ok { background:#e8f6ec; border:1px solid #bfe6c9; }
    .warn { background:#fff7e6; border:1px solid #f2d49b; }
    .bad { background:#fdecec; border:1px solid #f2b8b8; }
    .actions { display:flex; gap:10px; flex-wrap:wrap; margin-top: 10px; }
    a.btnlink { text-decoration:none; }
    .block { background:#fafafa; padding: 12px; border-radius: 10px; border: 1px solid #eee; margin-top: 10px; }
    .label { font-weight: 700; margin-bottom: 6px; }
    ul { margin: 0; padding-left: 18px; }
  </style>
</head>
<body>
  <h2>ReviewScan – Test</h2>
  <div class="muted">MOCK_MODE · kies mode en analyseer tekst.</div>

  <div class="row">
    <label for="mode"><b>Mode:</b></label>
    <select id="mode">
      <option value="review">Review (B2B)</option>
      <option value="scam">Scam / Oplichting (B2C)</option>
    </select>
    <button id="btn">Analyseer</button>
  </div>

  <textarea id="text">Knip of plak hier de tekst.</textarea>
  <script>
document.getElementById("btn").addEventListener("click", function() {
    const mode = document.getElementById("mode").value;
    window.reviewscan_mode = mode;
});
</script>
  <div class="card">
    <h3>Resultaat</h3>
    <div id="trustBadge"></div>
    <div class="actions" id="actions"></div>

    <div class="actions">
      <button id="copyBtn" disabled>📋 Kopieer voorstel</button>
      <span id="copyMsg" class="muted"></span>
    </div>

    <div class="block">
      <div class="label">Samenvatting</div>
      <div id="summary">—</div>
    </div>

    <div class="block">
      <div class="label">Wat liep er mis:</div>
      <div id="signals">—</div>
    </div>

    <div class="block">
      <div class="label">Voorstel reactie om direct te gebruiken</div>
      <div id="advice">—</div>
    </div>

    <div class="block">
      <div class="label">Wat nu doen?</div>
      <div id="nextSteps">—</div>
    </div>
  </div>

<script>
const btn = document.getElementById("btn");
const trustBadge = document.getElementById("trustBadge");
const actions = document.getElementById("actions");
const summaryEl = document.getElementById("summary");
const signalsEl = document.getElementById("signals");
const adviceEl = document.getElementById("advice");
const copyBtn = document.getElementById("copyBtn");
const copyMsg = document.getElementById("copyMsg");
const nextStepsEl = document.getElementById("nextSteps");

let latestSuggestion = "";

function badgeClass(trust) {
  if (trust === "Betrouwbaar") return "pill ok";
  if (trust === "Extra controle aanbevolen") return "pill warn";
  return "pill bad";
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function buildNextSteps(data) {
  const mode = (data.mode || "").toLowerCase();
  const trust = data.trust_level || "";

  let steps = [];
  let links = [];

  if (mode === "review") {
    if (trust === "Betrouwbaar") {
      steps = [
        "Geen dringende actie nodig.",
        "Gebruik deze feedback intern om je service te verbeteren.",
        "Bewaar het rapport voor interne documentatie."
      ];
    } else {
      steps = [
        "Controleer datum, uur en details van de review.",
        "Reageer professioneel (gebruik het voorgestelde antwoord).",
        "Indien onterecht of fake: rapporteer de review."
      ];
      links = [
        { label: "Google review rapporteren", url: "https://support.google.com/business/answer/4596773" }
      ];
    }
  } else if (mode === "scam") {
    if (trust === "Betrouwbaar") {
      steps = [
        "Geen sterke scam-indicatie op basis van tekst.",
        "Blijf alert en deel nooit codes of wachtwoorden."
      ];
    } else {
      steps = [
        "Klik nergens op en deel geen persoonlijke gegevens.",
        "Neem onmiddellijk contact op met je bank indien betaling gebeurde.",
        "Bewaar bewijs en download het rapport."
      ];
      links = [
        { label: "Politie – Wat te doen bij oplichting", url: "https://www.politie.be" }
      ];
    }
  } else {
    steps = ["—"];
  }

  let html = "<ul>";
  for (const s of steps) {
    html += "<li>" + escapeHtml(s) + "</li>";
  }
  html += "</ul>";

  if (links.length) {
    html += "<div style='margin-top:8px; display:flex; gap:10px; flex-wrap:wrap;'>";
    for (const l of links) {
      html += "<a href='" + l.url + "' target='_blank'>" + escapeHtml(l.label) + "</a>";
    }
    html += "</div>";
  }

  return html;
}

function extractIssues(data) {
  if (Array.isArray(data.what_went_wrong) && data.what_went_wrong.length) {
    return data.what_went_wrong;
  }
  if (Array.isArray(data.issues) && data.issues.length) {
    return data.issues;
  }
  if (Array.isArray(data.labels) && data.labels.length) {
    return data.labels;
  }
  if (Array.isArray(data.signals) && data.signals.length) {
    return data.signals.filter(x =>
      !["negative_sentiment", "general_negative", "algemeen_negatief"].includes(x)
    );
  }
  return [];
}

copyBtn.addEventListener("click", async () => {
  if (!latestSuggestion) return;

  try {
    await navigator.clipboard.writeText(latestSuggestion);
    copyMsg.textContent = "✓ Gekopieerd";
    setTimeout(() => {
      copyMsg.textContent = "";
    }, 2000);
  } catch (e) {
    copyMsg.textContent = "Kopiëren mislukt";
  }
});

btn.addEventListener("click", async () => {
  trustBadge.innerHTML = "";
  actions.innerHTML = "";
  summaryEl.textContent = "Bezig...";
  signalsEl.textContent = "—";
  adviceEl.textContent = "—";
  nextStepsEl.textContent = "—";
  copyBtn.disabled = true;
  copyMsg.textContent = "";
  latestSuggestion = "";

  const mode = document.getElementById("mode").value;
  const text = document.getElementById("text").value;

  try {
    const resp = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, text })
    });

    const data = await resp.json();

    const trust = data.trust_level || "";
    trustBadge.innerHTML =
      "<strong>Betrouwbaarheid:</strong> <span class='" + badgeClass(trust) + "'>" + escapeHtml(trust) + "</span>";

    if (data.report_link) {
      actions.innerHTML =
        "<a class='btnlink' href='" + data.report_link + "'><button>⬇️ Download rapport</button></a>";
    }

    summaryEl.textContent = data.summary || "—";

    const issues = extractIssues(data);
    if (issues.length) {
      signalsEl.innerHTML = "<ul>" + issues.map(x => "<li>" + escapeHtml(x) + "</li>").join("") + "</ul>";
    } else {
      signalsEl.textContent = "—";
    }

    latestSuggestion = data.response_suggestion || "";
    adviceEl.textContent = latestSuggestion || "—";
    copyBtn.disabled = !latestSuggestion;

    nextStepsEl.innerHTML = buildNextSteps(data);

  } catch (e) {
    summaryEl.textContent = "Fout: " + String(e);
    signalsEl.textContent = "—";
    adviceEl.textContent = "—";
    nextStepsEl.textContent = "—";
    copyBtn.disabled = true;
  }
});
</script>
</body>
</html>"""

    return make_response(html, 200)


# =========================
# REPORT DOWNLOAD (TXT)
# =========================

@app.route("/r/<rid>/report.txt", methods=["GET"])
def download_report_txt(rid):
    item = STORE.get(rid)
    if not item:
        abort(404)

    content = build_report_text(item)
    filename = f"reviewscan_report_{rid}.txt"

    return Response(
        content,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "ok",
        "mock_mode": MOCK_MODE,
        "endpoints": ["/test", "POST /analyze", "POST /analyze_review (legacy)", "/r/<id>", "/r/<id>/report.txt"]
    })


if __name__ == "__main__":
    print(f"MOCK_MODE = {MOCK_MODE} (env: MOCK_MODE)")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))