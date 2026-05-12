# ======================================
# SCAM ANALYZER (FINAL VERSION)
# ======================================

def analyze_scam_text(text: str, mock_mode: bool, try_real_ai_func, mock_scam_func) -> dict:

    if mock_mode:
        raw = mock_scam_func(text)
    else:
        try:
            raw = try_real_ai_func("scam", text)
        except Exception as e:
            raw = mock_scam_func(text)
            raw["note"] = f"fallback_to_mock: {type(e).__name__}"

    return normalize_scam_output(raw, text)


# =========================
# NORMALIZER (KEY LAYER)
# =========================

def normalize_scam_output(r: dict, text: str) -> dict:
    labels = r.get("labels", [])

    # 🔥 EXTRA DETECTIE (BELANGRIJKSTE FIX)
    extra_labels = detect_scam_patterns(text)
    labels = list(set(labels + extra_labels))

    # 🔥 SCORE BASED TRUST (FIX)
    trust = calculate_trust(labels)

    analysis = build_analysis(labels, trust)
    next_steps = build_next_steps(trust)

    return {
        "mode": "scam",
        "trust_level": trust,
        "summary": build_summary(labels, trust),
        "analysis": analysis,
        "labels": labels,
        "response_suggestion": r.get("response_suggestion", ""),
        "next_steps": next_steps,
        "engine": r.get("engine", "rule+mock")
    }


# =========================
# 🔥 NIEUWE DETECTIE LOGICA
# =========================

def detect_scam_patterns(text: str):
    text = text.lower()
    labels = []

    if "http" in text or "www" in text:
        labels.append("link")

    if "bank" in text:
        labels.append("bank")

    if "pincode" in text or "code" in text or "otp" in text:
        labels.append("2fa/otp")

    if "account" in text or "login" in text:
        labels.append("account")

    if "binnen 24 uur" in text or "urgent" in text or "nu" in text:
        labels.append("urgent")

    if "bevestig" in text or "verifieer" in text:
        labels.append("gegevens")

    return labels


# =========================
# 🔥 SCORE ENGINE
# =========================

def calculate_trust(labels):

    score = 0

    if "link" in labels:
        score += 2

    if "bank" in labels:
        score += 2

    if "2fa/otp" in labels:
        score += 3

    if "account" in labels:
        score += 2

    if "urgent" in labels:
        score += 2

    if "gegevens" in labels:
        score += 2

    # 🔥 RESULTAAT (CORRECTE VOLGORDE)
    if score >= 6:
        return "Onbetrouwbaar"
    elif score >= 3:
        return "Extra controle aanbevolen"
    else:
        return "Betrouwbaar"


# =========================
# BUILDERS
# =========================

def build_summary(labels, trust):
    if trust == "Onbetrouwbaar":
        return "Sterk verdacht bericht met meerdere typische oplichtingssignalen."
    elif trust == "Extra controle aanbevolen":
        return "Er zijn enkele verdachte signalen aanwezig in deze tekst."
    else:
        return "Er werden weinig duidelijke oplichtingssignalen gevonden."


def build_analysis(labels, trust):
    analysis = []

    if not labels:
        return ["Geen duidelijke verdachte patronen gevonden."]

    if "urgent" in labels:
        analysis.append("De tekst probeert druk te zetten (urgentie), wat typisch is bij phishing.")

    if "dreiging" in labels:
        analysis.append("Er wordt gedreigd met gevolgen, wat vaak gebruikt wordt om paniek te creëren.")

    if "account" in labels:
        analysis.append("Er wordt verwezen naar een account of login, wat kan wijzen op phishing.")

    if "2fa/otp" in labels:
        analysis.append("Er wordt gevraagd naar een verificatiecode (OTP), wat zeer gevoelig is.")

    if "gegevens" in labels:
        analysis.append("Er wordt gevraagd naar persoonlijke gegevens, wat een groot risico vormt.")

    if "link" in labels or "klik-hier" in labels:
        analysis.append("Er zit een link in de tekst, wat vaak gebruikt wordt om slachtoffers te misleiden.")

    if "betaling" in labels or "giftcards" in labels or "crypto-betaling" in labels:
        analysis.append("Er wordt gevraagd om een betaling, wat typisch is bij oplichting.")

    if "bank" in labels or "overheid" in labels:
        analysis.append("De afzender doet zich mogelijk voor als een officiële instantie.")

    if "te-mooi" in labels or "winnaar" in labels:
        analysis.append("De boodschap lijkt te mooi om waar te zijn, wat een klassiek scam-signaal is.")

    if trust == "Onbetrouwbaar":
        analysis.append("De combinatie van deze signalen wijst sterk op oplichting.")

    return analysis


def build_next_steps(trust):
    if trust == "Onbetrouwbaar":
        return [
            "Klik niet op links en open geen bijlagen.",
            "Deel geen persoonlijke gegevens of codes.",
            "Verwijder het bericht.",
            "Controleer via officiële kanalen indien nodig."
        ]

    elif trust == "Extra controle aanbevolen":
        return [
            "Controleer de afzender zorgvuldig.",
            "Open links enkel via officiële websites.",
            "Deel geen gevoelige informatie.",
            "Wees extra waakzaam."
        ]

    else:
        return [
            "Geen directe actie nodig.",
            "Blijf alert bij onbekende berichten."
        ]
