"""Point d'entrée principal et orchestration des enchères multi-agents."""

import asyncio
import sys
import ray

from acheteur import BidBehaviour, BuyerAgent, start_buyer
from config import DOMAIN, PASSWORD, SELLER, run_agent
from vendeur import AuctionBehaviour, SellerAgent, start_seller


# --- Tâches Ray pour la simulation automatique complète ("all") ---
@ray.remote
def run_seller_ray():
    agent = SellerAgent(SELLER, PASSWORD, item="Tableau ancien", start_price=100)
    asyncio.run(run_agent(agent))
    return "Vendeur terminé"


@ray.remote
def run_buyer_ray(name, budget):
    # En mode Ray automatique "all", les acheteurs sont en mode bot
    agent = BuyerAgent(f"{name}@{DOMAIN}", PASSWORD, budget, interactive=False)
    asyncio.run(run_agent(agent))
    return f"{name} terminé"


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python enchere.py acheteur1 300           # Mode interactif : vous saisissez vos prix en DH")
        print("  python enchere.py acheteur2 250 --auto    # Mode robot automatique")
        print("  python enchere.py vendeur                 # Lance le vendeur")
        print("  python enchere.py all                     # Simulation automatique complète avec Ray")
        print("\nOu directement par module :")
        print("  python vendeur.py")
        print("  python acheteur.py acheteur1 300")
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
        start_seller()

    else:
        # Rôle acheteur (ex: acheteur1, acheteur2, acheteur3)
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 200
        interactive = "--auto" not in sys.argv
        start_buyer(role, budget, interactive=interactive)


if __name__ == "__main__":
    main()