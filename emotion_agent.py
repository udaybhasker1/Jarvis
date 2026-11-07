def detect_emotion(text):
    text = text.lower()

    if any(word in text for word in ["sad", "tired", "upset", "depressed"]):
        return "sad"
    elif any(word in text for word in ["happy", "great", "awesome", "excited"]):
        return "happy"
    elif any(word in text for word in ["angry", "frustrated", "irritated"]):
        return "angry"
    else:
        return "neutral"