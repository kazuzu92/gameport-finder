# GamePort Finder 🎮

Site statique autonome : recherche instantanée de ports de jeux pour navigateur, fusion de catalogues, favoris, filtres, lien de démo et lien GitHub. **Les liens répertoriés ne sont pas une garantie de jeu complet ou fonctionnel.** Aucun jeu ni ROM n'est hébergé.

## Sources (agrégation quotidienne)

- [Ultimate Catalog of Web Game Ports](https://github.com/Carter54git/Ultimate-Catalog-Of-Web-Game-Ports)
- [Awesome Decomp Games](https://github.com/SubmitGame/awesome-decomp-games)
- [Awesome Browser Game Ports](https://github.com/bitburner/Awesome-Browser-Game-Ports)
- `data/curated.json` : compléments manuels

Le script `scripts/build_index.py` utilise la bibliothèque standard Python, importe les tableaux Markdown, rapproche les noms et conserve les différents liens par jeu. Il préserve les données déjà disponibles lorsque certains catalogues sont temporairement inaccessibles. Plusieurs noms d'une même franchise peuvent rester distincts ; inversement les titres réellement différents portant le même nom peuvent être fusionnés. Les liens externes ne sont **pas testés en lançant les jeux**. Option facultative `CHECK_LINKS=1` : contrôle HTTP limité (qui ne prouve pas le bon fonctionnement du jeu).

## Publication sur GitHub Pages

1. Créer un dépôt GitHub **public** nommé `gameport-finder` et y transférer le contenu du dossier (fichiers à la racine du dépôt).
2. Dans **Settings → Pages → Build and deployment**, sélectionner **Source: GitHub Actions**.
3. Dans **Actions**, lancer une fois **Update game index → Run workflow** pour actualiser les données.
4. Lancer **Deploy GitHub Pages** si nécessaire (le workflow se déclenche aussi à chaque commit sur la branche `main`).
5. Le site sera accessible à `https://VOTRE-PSEUDO.github.io/gameport-finder/` lorsque GitHub aura confirmé le déploiement.

> Le workflow quotidien a besoin de `Settings → Actions → General → Workflow permissions → Read and write permissions` pour publier les nouveaux JSON sur la branche, ou d'une configuration de permissions équivalente autorisée par le dépôt. Il n'utilise aucun jeton personnel ni secret.

## Tester sur son PC

Depuis la racine du dossier : `python -m http.server 8000` puis ouvrir `http://localhost:8000/`. Ou lancer `python scripts/build_index.py` pour renouveler le fichier `data/games.json` si l'accès réseau est autorisé. Ouvrir `index.html` en double-cliquant peut bloquer le chargement du JSON selon le navigateur ; un serveur local est recommandé.

## Sécurité et limites

- Liens HTTPS externes en nouveaux onglets avec `noopener noreferrer` ; aucune exécution de code des catalogues dans la page.
- Pas de téléchargement de ROM, pas de scraping massif de GitHub, pas d'API X/Twitter.
- La construction n'interroge que les sources configurées, **pas l'ensemble d'Internet**. Pour agrandir réellement la base, ajouter d'autres sources à `SOURCES` avec un parseur adapté, ou améliorer l'import de dépôts GitHub.
- Vérifier les droits d'utilisation, les fichiers originaux requis et la fiabilité des liens avant de jouer.
- Site compatible avec hébergement statique ; les favoris sont locaux à chaque navigateur.
