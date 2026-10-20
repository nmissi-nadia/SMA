import asyncio
import json
import time

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour

from config import BUYERS, PASSWORD, ROUND_SECONDS, SELLER, make_msg, run_agent


def get_auction_details():
    """Demande interactivement au vendeur l'article et le prix de départ."""
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


class AuctionBehaviour(OneShotBehaviour):
    """Comportement du vendeur : orchestre les tours d'enchères anglaises."""

    async def run(self):
        ag = self.agent
        price, leader = ag.start_price, None
        print(f"\n[Vendeur] ==========================================")
        print(f"[Vendeur] MISE EN VENTE : {ag.item} à {price} DH")
        print(f"[Vendeur] ==========================================")
        print(f"[Vendeur] Attente de 10 secondes pour la connexion des acheteurs...")
        await asyncio.sleep(10)

        tour = 1
        while True:
            print(f"\n[Vendeur] --- Tour {tour} ---")
            print(f"[Vendeur] Prix actuel : {price} DH | Enchérisseur en tête : {leader or 'Aucun'}")
            for b in BUYERS:
                await self.send(make_msg(b, "cfp", {
                    "item": ag.item, "price": price, "leader": leader}))

            print(f"[Vendeur] En attente des offres pendant {ROUND_SECONDS} secondes...")
            # Collecte des offres pendant le temps du tour
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
    """Agent SPADE représentant le vendeur aux enchères."""

    def __init__(self, jid, password, item, start_price):
        super().__init__(jid, password, verify_security=False)
        self.item, self.start_price, self.done = item, start_price, False

    async def setup(self):
        self.add_behaviour(AuctionBehaviour())


def start_seller(item=None, start_price=None):
    """Lance l'agent vendeur de manière autonome."""
    if item is None or start_price is None:
        item, start_price = get_auction_details()
    agent = SellerAgent(SELLER, PASSWORD, item=item, start_price=start_price)
    asyncio.run(run_agent(agent))


if __name__ == "__main__":
    print("[Vendeur] Démarrage du Vendeur dans ce terminal...")
    start_seller()
