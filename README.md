# GamePort Finder V2 🎮

Moteur statique de jeux pour navigateur, déployable gratuitement sur GitHub Pages. **Aucun jeu, ROM, BIOS ni fichier de jeu n'est hébergé.** Les liens ne garantissent pas un jeu complet ou fonctionnel.

## Ce qui change en V2

- Agrégation quotidienne des **trois catalogues existants**, avec conservation de la base actuelle.
- **Découverte additionnelle de dépôts GitHub** par cinq requêtes d'API. Un dépôt découvert n'est **jamais** présenté comme un jeu jouable sans lien de démo issu d'une source fiable.
- Recherche instantanée, favoris, filtre par console, par source et par état (actifs, suspects, archivés).
- Description des projets, plateforme inférée **lorsque les mots-clés figurent dans la description**.
- Aperçu visuel GitHub d'un dépôt lorsque disponible, **pas nécessairement une jaquette du jeu**. Des illustrations autorisées peuvent aussi être indiquées avec la clé `image` dans `data/curated.json`.
- Vérification HTTP d'un échantillon de 120 liens par jour, rotation quotidienne. **3 réponses 404/410** déclenchent le statut « suspect » ; le HTTP ne prouve pas le fonctionnement du jeu.
- Archivage intelligent : après **3 synchronisations réussies** au cours desquelles le jeu a disparu de toutes ses sources connues, il est masqué des résultats par défaut mais reste consultable par le filtre « Archivés ». Aucun effacement définitif.
- Des sources GitHub ponctuellement indisponibles ne font jamais perdre la base précédente.

### Limites à connaître

- Pas d'API X/Twitter : les annonces X nécessitent un accès autorisé et ne sont pas collectées automatiquement.
- Les portages PSP/PS2/PS3 ne sont **pas** systématiquement jouables ; le filtrage « console » dépend des métadonnées connues ou inférées.
- Les jaquettes officielles pour tous les jeux et les vidéos ne sont **pas** fournies : utiliser des images autorisées, ajoutées au catalogue manuel.
- Le contrôle automatique de lien teste l'accessibilité HTTP, pas le lancement réel des jeux. Un serveur qui bloque les robots peut apparaître « inconnu ».
- La recherche GitHub peut renvoyer des bibliothèques et prototypes sans jeu jouable. Les fiches sans lien de démo sont marquées « projet ».
- Une limite GitHub API ou un changement de format peut réduire la synchronisation. Les logs indiquent les échecs.

## Mise à jour du dépôt existant `kazuzu92/gameport-finder`

**Important : conserver `data/games.json` sur GitHub, qui contient tes ~620 entrées.** Ce ZIP de mise à jour ne contient volontairement **pas** ce fichier. Ne supprime pas le dépôt et ne recrée pas le site.

Remplacer ou ajouter dans GitHub, en conservant les chemins :

1. `index.html`
2. `scripts/build_index.py`
3. `.github/workflows/update.yml`
4. `README.md` (facultatif)

Conserver les fichiers existants `data/games.json`, `data/curated.json` et `.github/workflows/pages.yml`.

Dans GitHub : **Settings → Pages → Source : GitHub Actions**, puis **Actions → Update game index → Run workflow**. L'index est construit et commité, ce qui déclenche normalement le workflow Pages. Si les nouvelles données ne se publient pas, inspecter les logs des deux workflows. Permissions du workflow d'index : `contents: write` et autorisation GitHub de création de commits par Actions.

Le token `secrets.GITHUB_TOKEN` utilisé par GitHub Actions est fourni automatiquement par GitHub. **Ne crée pas de Personal Access Token, ne copie jamais de secret dans le code.**

## Tester localement

```bash
python -m http.server 8000
# http://localhost:8000/
python scripts/build_index.py  # nécessite Internet pour actualiser
```

## Ajouter manuellement un jeu ou une jaquette

Modifier `data/curated.json` :

```json
{"name":"Nom du jeu","demos":["https://adresse-officielle.example/"],"platforms":["PS2"],"tags":["Combat"],"image":"https://image-autorisée.example/visuel.jpg"}
```

Ne pas intégrer de matériel protégé sans autorisation. Le site n'utilise pas de base de données payante.

