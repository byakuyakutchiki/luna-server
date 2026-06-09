# BRIEF DE CORRECTION V3 — Iris Workspace
**Date** : 2026-06-09  
**Source** : Décision architecture produit (ChatGPT) + validation terrain (Kimi)  
**Destinataire** : Claude (Implémentation)  
**Priorité** : HAUTE  
**Scope** : Suppression du brief manuel → remplacement par brief auto-généré par Iris

---

## CONTEXTE

L'audit terrain #3 a révélé que le bouton **"BRIEF MISSION" persistant après validation** n'est pas un bug CSS mais un symptôme de friction produit. ChatGPT (architecte produit) a analysé le problème et tranché.

**Principe directeur** : *Ne pas créer du travail pour créer du travail.*  
L'utilisateur crée déjà : le titre, les propositions, les sources. Un quatrième formulaire (brief manuel) est une étape administrative inutile.

---

## DÉCISION PRODUIT

**Option retenue** : **Option 2 — BRIEF généré automatiquement par Iris**

### Workflow cible

```
Titre de session (saisi par owner)
    ↓
Iris génère automatiquement le brief à partir du titre
    ↓
Brief verrouillé (lecture seule)
    ↓
Propositions
    ↓
Travail (Dossier actif)
```

### Comportement attendu

1. **L'utilisateur ne remplit PLUS de brief manuellement.**
2. **Iris génère le brief automatiquement** à partir du titre de la session.
3. **Le brief est affiché en lecture seule** comme contexte de la session.
4. **Le bouton "BRIEF MISSION" est supprimé** du header.

### Exemple

- **Titre saisi** : "Comment rendre Luna rentable ?"
- **Brief auto-généré par Iris** :  
  "Cette session vise à identifier le modèle économique le plus pertinent pour assurer la rentabilité de Luna avant son lancement."

---

## CORRECTIONS À APPORTER

### 1. Supprimer le bouton "BRIEF MISSION"
- **Élément** : `#twBriefBtn` (ou équivalent dans le header)
- **Action** : Suppression complète du DOM, pas juste `display: none`
- **Raison** : L'utilisateur ne doit plus avoir la possibilité de remplir un brief manuellement

### 2. Supprimer le modal de saisie du brief
- **Élément** : Modal/actuellement déclenché par `#twBriefBtn`
- **Action** : Supprimer le HTML, le CSS et le JS lié à la saisie manuelle du brief
- **Raison** : Éliminer la friction administrative

### 3. Générer le brief automatiquement
- **Déclencheur** : Validation du titre de session (étape setup / landing)
- **Source** : Titre de la session uniquement (phase 1)
- **Cible** : Le brief est stocké comme propriété de la session et affiché en lecture seule

**Note technique** : En phase 1, la génération peut être côté frontend (template simple) ou côté backend (appel LLM).  
**Recommandation** : Côté frontend avec template pour éviter la latence et le coût API. Exemple de template :

```
"Cette session vise à [titre de la session]."
→ "Cette session vise à Comment rendre Luna rentable ?"
→ "Cette session vise à identifier les leviers de rentabilité pour Luna."
```

Si le backend dispose déjà d'un mécanisme de génération (Iris), l'utiliser. Sinon, template frontend acceptable pour l'instant.

### 4. Afficher le brief en lecture seule
- **Zone** : Remplacer l'ancien emplacement du bouton "BRIEF MISSION" par un affichage statique du brief généré, ou l'intégrer dans la zone "QUESTION" du header L2
- **Style** : Texte informatif, non éditable, visuellement distinct mais discret

### 5. Mettre à jour le stepper si nécessaire
- Si le stepper actuel incluait une étape "BRIEF" comme action utilisateur, la transformer en étape système (Iris génère le brief automatiquement entre l'étape setup et l'étape collecte).

---

## NON-RÉGRESSIONS À VÉRIFIER

| Élément | État attendu après correctif |
|---|---|
| Stepper 5 phases | ✅ Conservé (BRIEF · COLLECTE · ANALYSE · DECISION · LIVRABLE) |
| Canvas mode exploration | ✅ Conservé (cartes propositions) |
| Canvas mode travail | ✅ Conservé (Dossier actif) |
| Empty state | ✅ Conservé |
| twActiveCard | ✅ Toujours absent |
| IRIS AUDIO | ✅ Toujours masqué |

---

## DÉFINITION DE FAIT

- [ ] `#twBriefBtn` supprimé du header
- [ ] Modal de saisie brief supprimé
- [ ] Brief généré automatiquement à partir du titre
- [ ] Brief affiché en lecture seule dans l'interface
- [ ] Audit terrain Kimi relancé et validé

---

## LIENS

- Rapport audit #3 : `docs/audit_ux/2026-06-09-post-fix-v2/audit_report_v3.md`
- Décision produit complète : Section "Ce que je ferais pour Luna" du fil de discussion ChatGPT
