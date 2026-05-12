def build_response(result):
    response = {
        "trust": result.get("trust"),
        "summary": result.get("summary"),
        "signals": result.get("signals", []),
        "analysis": result.get("analysis", []),
        "steps": result.get("steps", []),
        "links": result.get("links", [])
    }

    if result.get("type") == "scam":
        if result.get("risk_level") == "high":
            response["message"] = "⚠️ High risk scam detected"
            response["advice"] = "Do NOT send money or personal data."
        else:
            response["message"] = "⚠️ Possible scam"
            response["advice"] = "Be careful and verify the source."
    else:
        if result.get("risk_level") == "high":
            response["message"] = "🚨 Critical negative review"
            response["advice"] = "Respond professionally and resolve fast."
        else:
            response["message"] = "💬 Neutral/low review"
            response["advice"] = "Acknowledge and improve if needed."

    return response