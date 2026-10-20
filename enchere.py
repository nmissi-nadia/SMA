import asyncio
import json
import random
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import ray
from slixmpp.features.feature_mechanisms.mechanisms import FeatureMechanisms
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message

# Autorise l'authentification PLAIN sur connexion locale non chiffrée
FeatureMechanisms.default_config["unencrypted_plain"] = True

DOMAIN = "localhost"
PASSWORD = "1234"
SELLER = f"vendeur@{DOMAIN}"
BUYERS = [f"acheteur{i}@{DOMAIN}" for i in (1, 2, 3)]
ROUND_SECONDS = 15  # Temps accordé aux acheteurs pour répondre (en secondes)


def make_msg(to, performative, payload):
    m = Message(to=to)
    m.set_metadata("performative", performative)  # cfp / propose / inform
    m.body = json.dumps(payload)
    return m


def get_user_input(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        return "p"


def get_auction_details():
    item = ""
    while not item:
        item = input("[Vendeur] Nom de l'article à vendre : ").strip()
        if not item:
            print("[Vendeur] Le nom de l'article ne peut pas être vide.")

    while True:
        raw_price = input("[Vendeur] Prix de départ en DH (nombre entier positif) : ").strip()
        try:
            start_price = int(raw_price)
        except ValueError:
            print("[Vendeur] Saisissez un prix sous forme de nombre entier.")
            continue
        if start_price <= 0:
            print("[Vendeur] Le prix de départ doit être supérieur à zéro.")
            continue
        return item, start_price


# ---------------------------------------------------------------- VENDEUR
class AuctionBehaviour(OneShotBehaviour):
    async def run(self):
        ag = self.agent
        price, leader = ag.start_price, None
        print(f"\n[Vendeur] ==========================================")
        print(f"[Vendeur] MISE EN VENTE : {ag.item} à {price} DH")
        print(f"[Vendeur] ==========================================")
        print(f"[Vendeur] Attente de 3 secondes pour la connexion des acheteurs...")
        await asyncio.sleep(3)

        tour = 1
        while True:
            print(f"\n[Vendeur] --- Tour {tour} ---")
            print(f"[Vendeur] Prix actuel : {price} DH | Enchérisseur en tête : {leader or 'Aucun'}")
            for b in BUYERS:
                await self.send(make_msg(b, "cfp", {
                    "item": ag.item, "price": price, "leader": leader}))

            print(f"[Vendeur] En attente des offres pendant {ROUND_SECONDS} secondes...")
            # collecte des offres pendant ROUND_SECONDS
            bids = {}
            end = time.monotonic() + ROUND_SECONDS
            while (left := end - time.monotonic()) > 0:
                msg = await self.receive(timeout=left)
                if msg and msg.get_metadata("performative") == "propose":
                    amount = json.loads(msg.body)["amount"]
                    sender = str(msg.sender).split("/")[0]
                    bids[sender] = amount
                    print(f"[Vendeur] Offre reçue de {sender} : {amount} DH")

            valid = {b: a for b, a in bids.items() if a > price}
            if not valid:
                print(f"[Vendeur] Aucune offre supérieure reçue.")
                break
            leader, price = max(valid.items(), key=lambda x: x[1])
            print(f"[Vendeur] Nouveau prix retenu : {price} DH par {leader}")
            tour += 1

        print(f"\n[Vendeur] ==========================================")
        if leader:
            print(f"[Vendeur] ADJUGÉ, VENDU à {leader} pour {price} DH !")
        else:
            print(f"[Vendeur] Objet non vendu (aucune offre retenue).")
        print(f"[Vendeur] ==========================================\n")

        for b in BUYERS:
            await self.send(make_msg(b, "inform", {"winner": leader, "price": price}))
        await asyncio.sleep(1)
        ag.done = True


class SellerAgent(Agent):
    def __init__(self, jid, password, item, start_price):
        super().__init__(jid, password, verify_security=False)
        self.item, self.start_price, self.done = item, start_price, False

    async def setup(self):
        self.add_behaviour(AuctionBehaviour())


# --------------------------------------------------------------- ACHETEUR
class BidBehaviour(CyclicBehaviour):
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
                print(f"\n" + "-"*50)
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
                # Mode automatique (bot avec enchère aléatoire)
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
            print("\n" + "="*50)
            if winner == ag.name_jid:
                print(f"[GAGNANT] [{ag.short}] FELICITATIONS ! Vous avez remporté l'enchère pour {final_price} DH !")
            elif winner:
                print(f"[FIN] [{ag.short}] Enchère terminée. Le gagnant est {winner} pour {final_price} DH.")
            else:
                print(f"[FIN] [{ag.short}] Enchère terminée. Aucun gagnant.")
            print("="*50 + "\n")
            ag.done = True


class BuyerAgent(Agent):
    def __init__(self, jid, password, budget, interactive=True):
        super().__init__(jid, password, verify_security=False)
        self.name_jid, self.short = jid, jid.split("@")[0]
        self.budget, self.done = budget, False
        self.interactive = interactive

    async def setup(self):
        mode = "INTERACTIF (saisie au clavier)" if self.interactive else "AUTOMATIQUE (robot)"
        print(f"[{self.short}] Connecté au serveur Prosody | Budget = {self.budget} DH | Mode : {mode}")
        self.add_behaviour(BidBehaviour())


# ------------------------------------------------------- EXÉCUTION AGENT
async def _run(agent):
    FeatureMechanisms.default_config["unencrypted_plain"] = True
    await agent.start(auto_register=True)
    while not agent.done:
        await asyncio.sleep(0.5)
    await agent.stop()


# Tâches Ray pour le mode automatique "all"
@ray.remote
def run_seller_ray():
    agent = SellerAgent(SELLER, PASSWORD, item="Tableau ancien", start_price=100)
    asyncio.run(_run(agent))
    return "Vendeur terminé"


@ray.remote
def run_buyer_ray(name, budget):
    # En mode Ray automatique "all", les acheteurs sont en mode bot
    agent = BuyerAgent(f"{name}@{DOMAIN}", PASSWORD, budget, interactive=False)
    asyncio.run(_run(agent))
    return f"{name} terminé"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python enchere.py acheteur1 300           # Mode interactif : vous saisissez vos prix en DH")
        print("  python enchere.py acheteur2 250 --auto    # Mode robot automatique")
        print("  python enchere.py vendeur                 # Lance le vendeur")
        print("  python enchere.py all                     # Simulation automatique complète avec Ray")
        sys.exit(1)

    role = sys.argv[1]

    if role == "all":
        try:
            ray.init(address="auto", logging_level="ERROR")
        except Exception:
            ray.init(logging_level="ERROR")

        print("Démarrage de la simulation automatique d'enchères (Ray)...")
        tasks = [
            run_buyer_ray.remote("acheteur1", 200),
            run_buyer_ray.remote("acheteur2", 250),
            run_buyer_ray.remote("acheteur3", 180),
            run_seller_ray.remote(),
        ]
        results = ray.get(tasks)
        for res in results:
            print(res)

    elif role == "vendeur":
        print("[Vendeur] Démarrage du Vendeur dans ce terminal...")
        item, start_price = get_auction_details()
        agent = SellerAgent(SELLER, PASSWORD, item=item, start_price=start_price)
        asyncio.run(_run(agent))

    else:
        # Rôle acheteur (ex: acheteur1, acheteur2, acheteur3)
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        interactive = "--auto" not in sys.argv
        agent = BuyerAgent(f"{role}@{DOMAIN}", PASSWORD, budget, interactive=interactive)
        asyncio.run(_run(agent))