from emotion_agent import detect_emotion
from agents_core import ( #type: ignore
    detect_intent,
    handle_task,
    handle_event,
    handle_notes,
    save_memory,
)


def main_agent(user_id, user_input):
    intent = detect_intent(user_input)
    emotion = detect_emotion(user_input)

    if intent == "task":
        response = handle_task(user_id, user_input)

    elif intent == "event":
        response = handle_event(user_id, user_input)

    elif intent == "note":
        response = handle_notes(user_id, user_input)

    else:
        response = "I can help with tasks, events, and notes!"

    # Save memory
    save_memory(user_id, user_input, intent, emotion)

    return response