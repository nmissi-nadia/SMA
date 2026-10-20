import asyncio
import json
import random
import sys

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour

from config import DOMAIN, PASSWORD, SELLER, make_msg, run_agent


def get_user_input(prompt):
    """Récupère la saisie de l'utilisateur avec gestion propre de l'interruption."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return "p"


class BidBehaviour(CyclicBehaviour):
    """Comportement de l'acheteur : reçoit les annonces (cfp) et enchérit."""

    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return
        ag = self.agent
        perf = msg.get_metadata("performative")
        data = json.loads(msg.body)

        if perf == "cfp":
            current_price = data["price"]
            current_leader = data["leader"]
            item = data["item"]

            if current_leader == ag.name_jid:
                print(f"\n[{ag.short}] Vous menez déjà les enchères à {current_price} DH. En attente des autres acheteurs...")
                return

            if ag.interactive:
                # Mode interactif : l'utilisateur tape le prix au clavier dans le terminal
                print(f"\n" + "-" * 50)
                print(f"[ANNONCE] [{ag.short}] NOUVELLE ANNONCE DU VENDEUR")
                print(f"   Objet           : {item}")
                print(f"   Prix actuel     : {current_price} DH")
                print(f"   Leader actuel   : {current_leader or 'Aucun'}")
                print(f"   Votre budget    : {ag.budget} DH")
                print("-" * 50)

                if current_price >= ag.budget:
                    print(f"[{ag.short}] Le prix actuel ({current_price} DH) atteint ou dépasse votre budget ({ag.budget} DH). Vous passez ce tour.")
                    return

                prompt = f"[{ag.short}] Entrez votre enchère en DH (> {current_price} DH, ou 'p' pour passer) : "
                raw = await asyncio.to_thread(get_user_input, prompt)
                user_str = raw.strip()

                if not user_str or user_str.lower() in ["p", "pass", "non", "0"]:
                    print(f"[{ag.short}] Vous passez votre tour.")
                    return

                try:
                    new_bid = int(user_str)
                except ValueError:
                    print(f"[{ag.short}] Saisie invalide ('{user_str}'). Vous passez ce tour.")
                    return

                if new_bid <= current_price:
                    print(f"[{ag.short}] Offre invalide : {new_bid} DH doit être strictement supérieure à {current_price} DH. Tour passé.")
                    return

                if new_bid > ag.budget:
                    print(f"[{ag.short}] Offre invalide : {new_bid} DH dépasse votre budget maximal ({ag.budget} DH). Tour passé.")
                    return

                print(f"[{ag.short}] [OK] Offre confirmée : {new_bid} DH envoyée au vendeur...")
                await self.send(make_msg(SELLER, "propose", {"amount": new_bid}))

            else:
                # Mode automatique (robot avec enchère aléatoire dans son budget)
                new_bid = current_price + random.randint(5, 30)
                if new_bid > ag.budget:
                    print(f"[{ag.short}] Trop cher ({new_bid} DH > budget {ag.budget} DH), je passe.")
                    return
                await asyncio.sleep(random.uniform(0.5, 2.0))
                print(f"[{ag.short}] J'enchéris automatiquement: {new_bid} DH")
                await self.send(make_msg(SELLER, "propose", {"amount": new_bid}))

        elif perf == "inform":
            winner = data.get("winner")
            final_price = data.get("price")
            print("\n" + "=" * 50)
            if winner == ag.name_jid:
                print(f"[GAGNANT] [{ag.short}] FÉLICITATIONS ! Vous avez remporté l'enchère pour {final_price} DH !")
            elif winner:
                print(f"[FIN] [{ag.short}] Enchère terminée. Le gagnant est {winner} pour {final_price} DH.")
            else:
                print(f"[FIN] [{ag.short}] Enchère terminée. Aucun gagnant.")
            print("=" * 50 + "\n")
            ag.done = True


class BuyerAgent(Agent):
    """Agent SPADE représentant un acheteur (interactif ou robot)."""

    def __init__(self, jid, password, budget, interactive=True):
        super().__init__(jid, password, verify_security=False)
        self.name_jid, self.short = jid, jid.split("@")[0]
        self.budget, self.done = budget, False
        self.interactive = interactive

    async def setup(self):
        mode = "INTERACTIF (saisie au clavier)" if self.interactive else "AUTOMATIQUE (robot)"
        print(f"[{self.short}] Connecté au serveur Prosody | Budget = {self.budget} DH | Mode : {mode}")
        self.add_behaviour(BidBehaviour())


def start_buyer(name="acheteur1", budget=200, interactive=True):
    """Lance l'agent acheteur avec le nom et le budget donnés."""
    jid = name if "@" in name else f"{name}@{DOMAIN}"
    agent = BuyerAgent(jid, PASSWORD, budget, interactive=interactive)
    asyncio.run(run_agent(agent))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python acheteur.py acheteur1 300           # Mode interactif (au clavier)")
        print("  python acheteur.py acheteur2 250 --auto    # Mode robot automatique")
        sys.exit(1)

    role = sys.argv[1]
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    interactive = "--auto" not in sys.argv
    start_buyer(role, budget, interactive=interactive)
