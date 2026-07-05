# Checklist obligatoire avant mise en production

> Règle d'or : aucune promotion en production sans validation explicite de Ludovic.

## 1. Préparer le déploiement

- [ ] Se positionner sur la branche correcte (`feature/...`).
- [ ] Vérifier le SHA du commit :
  ```bash
  git rev-parse HEAD
  ```
- [ ] Vérifier que le working directory est propre :
  ```bash
  git status --short
  ```
  Doit être vide ou ne contenir que des fichiers non trackés hors périmètre.

## 2. Vérifier les modifications

- [ ] Relire le diff :
  ```bash
  git diff --stat
  ```
- [ ] S'assurer que seuls les fichiers prévus sont modifiés.
- [ ] S'assurer qu'aucune modification backend ou APK n'est incluse par inadvertance.

## 3. Lancer la vérification anti-régression frontend

```bash
python3 tools/frontend_regression_check.py --strict
```

- [ ] Le script retourne `✅ Aucune différence inattendue détectée`.
- [ ] Si des différences apparaissent, elles doivent correspondre exactement aux modifications intentionnelles.

## 4. Déployer sur une trace (0 % trafic)

```bash
./deploy.sh --tag=trace --no-traffic
```

- [ ] La révision est créée avec succès.
- [ ] L'URL trace est obtenue (ex: `https://trace---luna-beta-gly3g647na-ew.a.run.app`).

## 5. Comparer trace ↔ production

```bash
python3 tools/frontend_regression_check.py --trace https://trace---....a.run.app
```

- [ ] La trace est identique à la production, sauf pour les modifications intentionnelles.

Comparaison manuelle des routes critiques :
- [ ] `/`
- [ ] `/guardian`
- [ ] `/static/index.html`
- [ ] `/static/guardian.html`
- [ ] `/static/salon.html`
- [ ] `/static/simli.html`
- [ ] `/static/manifest.json`
- [ ] `/static/sw.js`

## 6. Tester sur téléphone

- [ ] Navigation générale fluide.
- [ ] Guardian s'affiche correctement.
- [ ] Installation PWA possible (icône, splash screen, plein écran).
- [ ] Micro activé et écoute fonctionnelle.
- [ ] Déclenchement vocal "à l'aide" / "au secours".
- [ ] Contexte vocal complet conservé.
- [ ] Pas de régression graphique (Android + iPhone).
- [ ] Pas de boucle de redirection.

## 7. Validation humaine

- [ ] Codex a audité les fichiers modifiés.
- [ ] Ludovic a validé le comportement terrain.

## 8. Promotion en production

Seulement après les étapes 1 à 7 :

- [ ] Ludovic donne l'ordre explicite de promotion.
- [ ] La promotion se fait via une procédure documentée (merge PR ou redéploiement avec trafic).
- [ ] Vérifier que 100 % du trafic est sur la nouvelle révision.
- [ ] Vérifier à nouveau les routes critiques en production.

## 9. En cas de problème après production

- [ ] Ne pas paniquer.
- [ ] Ne pas déployer un autre correctif immédiatement sans audit.
- [ ] Revenir à la branche de référence si nécessaire :
  ```bash
  git checkout stable/frontend-reference-2026-07-05
  ```
- [ ] Prévenir Ludovic et Codex.

---

## Références

- Branche stable frontend : `stable/frontend-reference-2026-07-05`
- Script anti-régression : `tools/frontend_regression_check.py`
- Production : `https://luna-beta-674304336025.europe-west1.run.app`
- Documentation état : `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md`

Dernière mise à jour : 2026-07-05
