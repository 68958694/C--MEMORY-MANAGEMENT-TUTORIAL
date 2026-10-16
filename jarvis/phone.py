"""Phone calls and text messages to you, via Twilio.

Setup: create a Twilio account (twilio.com), buy a phone number, then set
TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER and JARVIS_MY_PHONE
(numbers in +countrycode format). On a Twilio trial account you must first
verify your own number in the Twilio console.
"""

from xml.sax.saxutils import escape

from jarvis import config
from jarvis.errors import SetupNeeded


def is_configured() -> bool:
    return all((config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN,
                config.TWILIO_FROM_NUMBER, config.MY_PHONE_NUMBER))


def _client():
    if not is_configured():
        raise SetupNeeded("Phone calls and texts need Twilio. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                          "TWILIO_FROM_NUMBER and JARVIS_MY_PHONE in your .env file.")
    try:
        from twilio.rest import Client
    except ImportError:
        raise SetupNeeded("The Twilio package is missing. Run: pip install twilio")
    return Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)


def call_me(message: str) -> str:
    intro = f"Hello {config.USER_TITLE}, this is {config.NAME}. "
    twiml = (f'<Response><Pause length="1"/><Say voice="Polly.Brian">{escape(intro + message)}</Say>'
             f'<Pause length="1"/><Say voice="Polly.Brian">{escape("Goodbye.")}</Say></Response>')
    _client().calls.create(to=config.MY_PHONE_NUMBER, from_=config.TWILIO_FROM_NUMBER, twiml=twiml)
    return f"Calling your phone now, {config.USER_TITLE}."


def text_me(message: str) -> str:
    body = f"{config.NAME}: {message}"
    _client().messages.create(to=config.MY_PHONE_NUMBER, from_=config.TWILIO_FROM_NUMBER, body=body[:1500])
    return "Text message sent to your phone."
