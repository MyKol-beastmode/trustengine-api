def analyze_review_text(text: str, mock_mode: bool, try_real_ai_func, mock_review_func) -> dict:
    if mock_mode:
        result = mock_review_func(text)
    else:
        try:
            result = try_real_ai_func("review", text)
        except Exception as e:
            result = mock_review_func(text)
            result["note"] = f"fallback_to_mock: {type(e).__name__}"

    text_lower = text.lower()

    issue_patterns = {
        "eten_kwaliteit": [
            "food", "meal", "dish", "menu", "plate", "dinner", "lunch", "breakfast",
            "eten", "gerecht", "maaltijd", "schotel", "bord",
            "cold food", "raw food", "burnt food", "stale food",
            "koud eten", "rauw", "aangebrand", "oud eten", "smaakloos",
            "bad taste", "terrible taste", "bland", "salty", "too salty", "too spicy",
            "no taste", "weird taste", "nasty food", "disgusting food",
            "niet lekker", "slecht eten", "slecht voedsel", "eten was slecht",
            "terrible food", "bad food", "awful food", "food was bad", "food was terrible",
            "heerlijk eten", "lekker eten", "goed eten"
        ],
        "bediening": [
            "service", "staff", "waiter", "waitress", "server", "crew", "team",
            "bediening", "ober", "personeel", "medewerker", "werknemer",
            "rude staff", "unfriendly staff", "bad service", "poor service",
            "slechte service", "onvriendelijk", "arrogant", "onbeleefd", "asociaal",
            "ignored us", "ignored me", "no attention", "didn't care",
            "geen aandacht", "ons genegeerd", "mij genegeerd", "niet behulpzaam",
            "not helpful", "lazy staff", "slow staff", "terrible waiter",
            "bad bediening", "slechte bediening", "trage bediening"
        ],
        "wachttijd_horeca": [
            "wait", "waiting", "slow", "late", "delay", "minutes", "hour", "hours",
            "wachten", "wachttijd", "traag", "lang moeten wachten", "duurde", "te laat",
            "took forever", "too long", "long wait", "very slow", "extremely slow",
            "40 minutes", "30 minutes", "20 minutes", "an hour",
            "eeuwigheid", "heel traag", "super traag", "langzaam",
            "order took long", "service took long", "still waiting",
            "lang wachten", "duurde lang"
        ],
        "hygiëne": [
            "dirty", "filthy", "unclean", "sticky", "smelly", "stinks",
            "vuil", "vies", "onhygiënisch", "stinkt", "plakkerig", "smerig",
            "dirty table", "dirty floor", "dirty toilet", "dirty bathroom",
            "vuile tafel", "vuile vloer", "vuile wc", "vuile toiletten",
            "hair in food", "bug", "insect", "mold", "schimmel"
        ],
        "prijs_kwaliteit": [
            "expensive", "overpriced", "too expensive", "not worth it", "rip off",
            "duur", "te duur", "veel te duur", "afzetterij",
            "small portion", "tiny portion", "poor value", "bad value",
            "kleine portie", "weinig eten", "prijs kwaliteit slecht",
            "not worth the money", "waste of money", "zonde van het geld"
        ],
        "bestelling_fout": [
            "wrong order", "incorrect order", "missing item", "forgot", "forgotten",
            "verkeerde bestelling", "foute bestelling", "iets vergeten", "ontbrak",
            "cold fries instead", "missing sauce", "wrong drink", "wrong meal",
            "bestelling fout", "niet gekregen wat besteld was", "verkeerd geleverd"
        ],
        "sfeer": [
            "loud", "too loud", "noise", "noisy", "chaotic", "stressful",
            "lawaai", "te luid", "rumoer", "chaotisch", "druk", "onrustig",
            "bad atmosphere", "awkward atmosphere", "uncomfortable", "ongezellig",
            "muziek te luid", "music too loud"
        ],
        "reservatie": [
            "reservation", "booking", "booked", "table reserved",
            "reservatie", "boeking", "gereserveerd", "tafel gereserveerd",
            "lost reservation", "no table", "reservation ignored",
            "reservatie kwijt", "geen tafel", "reservatie genegeerd"
        ],
        "levering": [
            "delivery", "delivered late", "never arrived", "driver", "courier",
            "levering", "bezorging", "niet geleverd", "veel te laat geleverd",
            "bestelling kwam niet", "cold delivery", "soggy", "mushy"
        ],
        "management": [
            "manager", "management", "owner", "chef",
            "manager was rude", "owner was rude", "no apology", "didn't care",
            "manager onbeleefd", "eigenaar onbeleefd", "geen excuses", "niet opgelost",
            "complaint ignored", "klacht genegeerd", "geen oplossing"
        ],
        "klantenservice": [
            "email", "emails", "mail", "mailtje", "mailtjes",
            "contact", "contacteer", "contact opnemen",
            "telefonisch", "telefoon", "telefoontje", "oproep",
            "klantenservice", "customer service", "support", "helpdesk",
            "niet bereikbaar", "onbereikbaar", "moeilijk bereikbaar",
            "geen antwoord", "niet beantwoord", "geen reactie", "niet gereageerd",
            "geen reply", "no response", "no reply", "didn't respond",
            "ignored email", "ignored my email", "never replied",
            "niemand neemt op", "neemt niet op", "krijg niemand te pakken",
            "geen gehoor", "geen contact mogelijk", "no one answers",
            "niet teruggebeld", "never called back", "wordt niet teruggebeld"
        ],
        "bereikbaarheid": [
            "bereikbaar", "niet bereikbaar", "onbereikbaar", "moeilijk bereikbaar",
            "telefonisch niet bereikbaar", "krijg niemand te pakken",
            "line busy", "always busy", "voicemail", "antwoordapparaat",
            "geen gehoor", "slecht bereikbaar", "amper bereikbaar"
        ],
        "communicatie": [
            "slechte communicatie", "onduidelijke communicatie", "geen communicatie",
            "onduidelijk", "niet duidelijk", "verwarrend", "miscommunicatie",
            "geen uitleg", "slechte uitleg", "weinig uitleg",
            "no communication", "bad communication", "unclear", "confusing",
            "geen feedback", "geen update", "niet op de hoogte gehouden",
            "niet teruggebeld", "geen opvolging", "slechte opvolging"
        ],
        "administratie": [
            "verkeerde factuur", "foute factuur", "factuur klopt niet",
            "dubbel aangerekend", "te veel aangerekend", "verkeerd aangerekend",
            "administratieve fout", "fout in dossier", "verkeerde gegevens",
            "foute gegevens", "fout document", "verkeerde informatie",
            "wrong invoice", "incorrect invoice", "billing error",
            "double charged", "overcharged", "wrong information", "wrong details",
            "bill was wrong", "invoice was wrong"
        ]
    }

    negative_patterns = [
        "bad", "very bad", "terrible", "awful", "horrible", "worst", "disgusting",
        "slecht", "heel slecht", "verschrikkelijk", "vreselijk", "afschuwelijk",
        "not good", "not great", "not fresh", "not tasty", "not worth it",
        "niet goed", "niet lekker", "niet vers", "niet oké", "niet waard",
        "poor", "poorly", "disappointing", "disappointed", "frustrating", "frustrated",
        "teleurstellend", "teleurgesteld", "frustrerend", "frustratie",
        "rude", "unfriendly", "cold", "dry", "burnt", "raw", "stale", "salty",
        "onbeleefd", "onvriendelijk", "koud", "droog", "aangebrand", "rauw", "oud",
        "slow", "late", "dirty", "filthy", "smelly", "sticky",
        "traag", "te laat", "vuil", "vies", "stinkt", "plakkerig",
        "never again", "won't return", "do not recommend", "avoid this place",
        "nooit meer", "kom niet terug", "geen aanrader", "vermijden",
        "waste of money", "rip off", "scam", "afzetterij", "zonde van het geld",
        "niet beantwoord", "geen reactie", "factuur klopt niet", "wrong invoice", "bill was wrong"
    ]

    positive_patterns = [
        "good", "great", "excellent", "amazing", "perfect", "delicious", "fresh",
        "goed", "heel goed", "lekker", "heerlijk", "uitstekend", "top",
        "vriendelijk", "snelle service", "proper", "netjes"
    ]

    signals = result.get("signals", [])
    if not isinstance(signals, list):
        signals = []

    has_negative = any(p in text_lower for p in negative_patterns)
    has_positive = any(p in text_lower for p in positive_patterns)

    detected_categories = []

    for category, patterns in issue_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                if category not in detected_categories:
                    detected_categories.append(category)
                break

    if not detected_categories and has_negative:
        detected_categories.append("algemeen_negatief")

    if detected_categories and not has_positive:
        has_negative = True

    for category in detected_categories:
        if category not in signals:
            signals.append(category)

    if has_negative and "negative_sentiment" not in signals:
        signals.append("negative_sentiment")

    result["signals"] = signals

    clean_categories = [
        c for c in signals
        if c not in ["algemeen_negatief", "negative_sentiment", "general_negative"]
    ]

    if clean_categories:
        result["issues"] = clean_categories
        result["what_went_wrong"] = clean_categories
        result["summary"] = (
            f"Review-analyse: "
            f"{'negatief' if has_negative and not has_positive else 'positief' if has_positive and not has_negative else 'neutraal'}. "
            f"Signalen: {', '.join(clean_categories)}"
        )
    else:
        result["issues"] = []
        result["what_went_wrong"] = []
        result["summary"] = (
            f"Review-analyse: "
            f"{'negatief' if has_negative and not has_positive else 'positief' if has_positive and not has_negative else 'neutraal'}. "
            f"Signalen: geen duidelijke signalen"
        )

    if has_negative and not has_positive:
        if result.get("sentiment") in [None, "", "neutraal", "neutral"]:
            result["sentiment"] = "negatief"

    if has_positive and not has_negative:
        if result.get("sentiment") in [None, "", "neutraal", "neutral"]:
            result["sentiment"] = "positief"

    return result