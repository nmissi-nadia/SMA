import asyncio
import json
import sys

from slixmpp.features.feature_mechanisms.mechanisms import FeatureMechanisms
from spade.message import Message

# Encodage de la console sous Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Autorise l'authentification PLAIN sur connexion locale non chiffrée
FeatureMechanisms.default_config["unencrypted_plain"] = True

# --- Configuration du réseau et des identifiants XMPP ---
DOMAIN = "localhost"
PASSWORD = "1234"
SELLER = f"vendeur@{DOMAIN}"
BUYERS = [f"acheteur{i}@{DOMAIN}" for i in (1, 2, 3)]
ROUND_SECONDS = 30  # Temps accordé aux acheteurs pour répondre (en secondes)


def make_msg(to: str, performative: str, payload: dict) -> Message:
    """Crée un message FIPA-ACL au format JSON."""
    m = Message(to=to)
    m.set_metadata("performative", performative)  # cfp / propose / inform
    m.body = json.dumps(payload)
    return m


async def run_agent(agent):
    """Démarre un agent SPADE, attend la fin de sa tâche puis l'arrête proprement."""
    FeatureMechanisms.default_config["unencrypted_plain"] = True
    await agent.start(auto_register=True)
    while not agent.done:
        await asyncio.sleep(0.5)
    await agent.stop()
