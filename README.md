# 🏛️ Système Multi-Agents d'Enchères (SPADE + XMPP Prosody Docker)

Projet de **Système Multi-Agents (SMA)** simulant une salle des ventes aux **enchères anglaises (montantes)**. Les agents communiquent via le protocole **XMPP** grâce à un serveur **Prosody** déployé sous **Docker**.

La devise utilisée pour les transactions est le **Dirham (DH)**.

---

## 📋 Table des matières

1. [Architecture & Fonctionnement](#architecture--fonctionnement)
2. [Prérequis](#prérequis)
3. [Démarrage du Serveur XMPP (Docker)](#démarrage-du-serveur-xmpp-docker)
4. [Exécution des Agents](#exécution-des-agents)
   - [Scénario 1 : Simulation interactive au clavier](#scénario-1--simulation-interactive-au-clavier-recommandé)
   - [Scénario 2 : Concurrencer un robot automatique](#scénario-2--concurrencer-un-robot-automatique)
   - [Scénario 3 : Simulation automatique globale (Ray)](#scénario-3--simulation-automatique-globale-ray)
5. [Règles de l'Enchère](#règles-de-lenchère)
6. [Commandes utiles Docker](#commandes-utiles-docker)

---

## 🏗️ Architecture & Fonctionnement

- **Serveur XMPP (Prosody)** : Exécuté dans un conteneur Docker, il gère l'authentification et le routage des messages FIPA-ACL entre les agents sur le port `5222`.
- **Agent Vendeur (`SellerAgent`)** :
  - Met un article en vente à un prix initial (ex: `Tableau ancien` à `100 DH`).
  - Envoie un appel à propositions (`cfp`) à tous les acheteurs.
  - Collecte les offres pendant un tour chronométré (15 secondes).
  - Détermine la meilleure offre, actualise le prix et recommence jusqu'à épuisement des enchères.
  - Proclame le gagnant avec un message d'information (`inform`).
- **Agents Acheteurs (`BuyerAgent`)** :
  - **Mode Interactif (par défaut)** : Affiche l'annonce dans le terminal et invite l'utilisateur à saisir manuellement son enchère en DH.
  - **Mode Automatique (`--auto`)** : Enchérit automatiquement avec une stratégie aléatoire dans la limite de son budget.

---

## ⚙️ Prérequis

1. **Docker Desktop** installé et démarré.
2. **Python 3.9+** avec votre environnement virtuel (ex: `sma_env`) contenant :
   ```bash
   pip install spade slixmpp ray
   ```

---

## 🐳 Démarrage du Serveur XMPP (Docker)

Avant de lancer les agents Python, démarrez le conteneur Prosody :

```bash
docker compose up -d
```

Pour vérifier que le serveur fonctionne correctement :
```bash
docker ps
```
*(Le conteneur `prosody` doit avoir le statut `Up` et mapper le port `5222:5222`).*

---

## 🚀 Exécution des Agents

Activez votre environnement virtuel dans vos terminaux (ex: `conda activate sma_env` ou `.\sma_env\Scripts\activate`).

### Scénario 1 : Simulation interactive au clavier (Recommandé)

Ouvrez **deux fenêtres de terminal** :

1. **Terminal 1 — Lancer le Vendeur :**
   ```bash
   python enchere.py vendeur
   ```
   Le vendeur vous demande le nom de l'article puis son prix de départ en DH.

2. **Terminal 2 — Lancer votre Acheteur (avec un budget de 300 DH) :**
   ```bash
   python enchere.py acheteur1 300
   ```

> 💡 **Déroulement dans votre terminal :**
> Dès que le vendeur annonce un prix, votre terminal affiche :
> ```text
> --------------------------------------------------
> [ANNONCE] [acheteur1] NOUVELLE ANNONCE DU VENDEUR
>    Objet           : (article saisi par le vendeur)
>    Prix actuel     : (prix de départ choisi par le vendeur)
>    Leader actuel   : Aucun
>    Votre budget    : 300 DH
> --------------------------------------------------
> [acheteur1] Entrez votre enchère en DH (> 100 DH, ou 'p' pour passer) : 
> ```
> Tapez simplement votre montant (ex: `125`), puis validez avec **Entrée**.

---

### Scénario 2 : Concurrencer un robot automatique

Vous pouvez ouvrir un troisième terminal pour faire participer un robot automatique :

- **Terminal 1 :** `python enchere.py vendeur`
- **Terminal 2 (Vous - Humain) :** `python enchere.py acheteur1 300`
- **Terminal 3 (Robot automatique) :** `python enchere.py acheteur2 250 --auto`

---

### Scénario 3 : Simulation automatique globale (Ray)

Pour exécuter une démonstration complète où tous les agents (1 vendeur + 3 acheteurs robots) s'exécutent en parallèle dans une seule commande :

```bash
python enchere.py all
```

---

## 📜 Règles de l'Enchère

- **Offre minimale** : Toute offre doit être strictement supérieure au prix actuel retenu par le vendeur.
- **Plafond budgétaire** : Une offre ne peut pas dépasser le budget alloué à l'acheteur.
- **Passer son tour** : Tapez `p`, `pass` ou appuyez directement sur **Entrée** sans saisir de montant.
- **Fin de l'enchère** : Lorsqu'aucun acheteur ne surenchérit pendant le tour, l'objet est adjugé au dernier meilleur enchérisseur au prix convenu.

---

## 🛠️ Commandes utiles Docker

- **Afficher les logs du serveur XMPP :**
  ```bash
  docker logs -f prosody
  ```
- **Arrêter le conteneur Prosody :**
  ```bash
  docker compose down
  ```
- **Redémarrer le conteneur :**
  ```bash
  docker compose restart
  ```
- **Créer manuellement un compte XMPP supplémentaire :**
  ```bash
  docker exec -it prosody prosodyctl register <nom_utilisateur> localhost <mot_de_passe>
  ```
