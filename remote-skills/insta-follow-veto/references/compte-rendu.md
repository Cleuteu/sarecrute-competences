# Compte rendu et incidents — doctrine commune aux compétences recruteur

Ce fichier est **identique dans les cinq compétences** du plugin `sarecrute-recruteur`
(`tests/compte_rendu_commun.test.py` l'exige). Le modifier, c'est le modifier dans les cinq
dossiers et monter les cinq versions.

## Deux lecteurs

Constat du 09/09/2026 : les recruteuses ne lisent pas les comptes rendus. Ils sont noyés dans les
lignes intermédiaires du run, et ce qu'ils contiennent — identité, recordIds, décisions de
tuyauterie, sortie des routines — ne leur demande rien. Alex, lui, a besoin de ce détail pour
maintenir les compétences. D'où deux niveaux de sortie, jamais mélangés.

### Mode recruteur — par défaut

**Pendant le run**, n'écrire entre deux appels d'outil que :

- une question (celles que le PROMPT.md autorise, et rien d'autre) ;
- le récapitulatif avant feu vert quand le PROMPT.md en prévoit un ;
- une erreur bloquante, traitée comme un incident (voir plus bas).

Une seule ligne au tout début : `<compétence> <version>`. Le stub l'exige, et c'est ce qui permet
de savoir ce qui a réellement tourné quand une recruteuse rapporte un problème. Rien d'autre :
ni l'origine de l'identité, ni le dossier du snapshot, ni les décisions prises seul.

**À la fin**, trois blocs, dans cet ordre, et rien avant eux :

```
**Fait**
- <ce qui existe maintenant, avec le lien Airtable ou le chemin du fichier>

**À faire par vous**
- <chaque action attendue de la recruteuse, une par ligne>

**Pas fait**
- <ce qui était prévu et n'a pas été fait, nommé précisément, avec la raison en quelques mots>
```

Règles :

- **Dix lignes** au total, hors listes d'items que la doctrine impose de nommer un par un (les
  publications écartées « offre × canal », les champs vides à compléter).
- **Liens cliquables**, pas de recordId : `https://airtable.com/appP0W2ISytaNyAhG/<tblId>/<recId>`.
  Aucun identifiant de champ (`fld…`), aucun nom d'outil, aucun nom de script.
- **Ne jamais réimprimer** ce que la recruteuse a collé (annonce, CV, transcript).
- **Un bloc vide se supprime.** Pas de « Pas fait : rien ».
- Le tri se fait entre **ce qui appelle une action de la recruteuse et ce qui n'en appelle pas**,
  jamais entre important et secondaire. Une décision de tuyauterie qui n'appelle aucune action
  n'a pas sa place ici, même en une ligne.
- Les **cas dégradés prévus par le PROMPT.md** (image manquante, groupe non rejoint, canal sans
  URL, county non résolu, doublon détecté…) vont dans *Pas fait* ou *À faire par vous*, nommés
  **un par un**. La leçon du 07/09/2026 tient toujours : un « des canaux sans URL » anonyme a
  obligé la recruteuse à demander pourquoi une annonce manquait.
- Le nom de la recruteuse au nom de qui on a travaillé figure dans la **première ligne de
  *Fait*** (« Fiche créée au nom de Sarah »). Une mauvaise attribution se voit ainsi d'un coup
  d'œil ; l'origine de l'identité, elle, est du détail technique.

### Mode détaillé — sur demande

Déclenché quand le message de lancement contient **`debug`** (ou « mode détaillé », « détail
technique »). Alors :

- pendant le run, la narration habituelle : chaque décision prise seul s'affiche en une ligne au
  moment où elle est prise, la version et l'origine de l'identité sont annoncées ;
- après les trois blocs, une section `## Détail technique` avec, au minimum : version du
  PROMPT.md, identité et son origine, recordIds et champs écrits, décisions prises seul, compte
  rendu des routines et scripts **tel qu'ils le formulent**, contrôles et leurs ⚠️, et ce que le
  PROMPT.md liste lui-même sous « Détail technique ».

Sans le mot-clé, **rien de ce détail n'apparaît**, pas même en résumé. Ce n'est pas une perte :
en cas d'incident, c'est exactement ce que le mail à Alex transporte.

## Incidents

### Ce qui est un incident

La compétence **s'arrête avant d'avoir livré son résultat**, ou **une écriture s'est faite à
moitié**. Par exemple :

- une écriture Airtable refusée (422, valeur de select inconnue, collaborateur inconnu) ;
- un connecteur indisponible ou qui répond en erreur (Airtable, Gmail, Drive, Chrome) ;
- un garde-fou du PROMPT.md déclenché (`MAUVAIS_COMPTE`, versions différentes…) ;
- un script du snapshot qui plante ;
- un état que le PROMPT.md ne prévoit pas, et devant lequel on improviserait.

Le snapshot qui ne se télécharge pas est aussi un incident, mais il survient avant la lecture de
ce fichier : c'est le stub `SKILL.md` qui le traite, avec la même procédure en version courte.

### Ce qui n'en est pas

Les cas dégradés que le PROMPT.md prévoit et pour lesquels il dit « continuer et le dire » : image
manquante, groupe non rejoint, canal sans URL, mur de profil hors périmètre, county non résolu,
champ laissé vide faute d'information, doublon ou homonyme détecté, profil Instagram
indisponible, blocage Instagram (c'est une limite à ne pas franchir, pas une panne). Ils vont dans
*Pas fait* ou *À faire par vous*, et le run continue.

**Dans le doute, c'est un incident.** Un mail de trop coûte une minute à Alex ; un incident passé
sous silence coûte une fiche fausse en base que personne ne cherchera.

### Procédure

1. **S'arrêter.** Aucun retour arrière : ne rien supprimer de ce qui a été créé, c'est Alex qui
   décidera, avec le mail sous les yeux. Aucune nouvelle tentative au-delà de ce que le PROMPT.md
   prévoit explicitement.

2. **Dire à la recruteuse**, deux lignes, sans jargon et sans l'erreur brute :

   > La compétence n'a pas pu aller au bout. Un mail pour Alex est prêt dans vos brouillons
   > Gmail : envoyez-le tel quel, il contient tout ce dont il a besoin.

   Si quelque chose a été écrit avant l'arrêt, ajouter le bloc *Fait* réduit à ce qui existe
   réellement (« La fiche de <Nom> a été créée mais pas enrichie : <lien> »). Ne rien lui
   demander de diagnostiquer.

3. **Préparer le mail** : brouillon via `create_draft` du connecteur Gmail, **jamais envoyé**.
   - `to` : `alex@botyglot.com` — adresse fixe, écrite ici et non lue dans Airtable, puisque
     Airtable est parfois ce qui tombe.
   - `subject` : `[SaRecrute] Échec <compétence> <version> — <Prénom de la recruteuse> — <JJ/MM/AAAA HH:MM>`.
     Le préfixe est constant : Alex filtre dessus.
   - Corps : le modèle ci-dessous, rempli. Il **remplace** le détail technique qu'on ne montre pas
     à la recruteuse ; tout ce que le mode détaillé aurait affiché y va.

4. **Sans connecteur Gmail** (absent, ou lui-même en erreur) : afficher le corps du mail dans un
   bloc de code, précédé de « À envoyer à alex@botyglot.com ». Ne pas chercher un autre canal.

5. **Un seul mail par run.** Si un second incident survient pendant la préparation du premier,
   il s'ajoute au corps.

6. **En mode détaillé, pas de mail** : le contenu s'affiche directement dans la conversation, le
   lecteur est déjà Alex.

### Modèle du corps

```
Compétence : <nom> <version>
Date : <JJ/MM/AAAA HH:MM>, heure de Paris
Recruteuse : <Prénom Nom> — identité : <fichier local | compte Claude reconnu dans Recruteurs | seule recruteuse active | choisie>
Environnement : <ce que l'on sait : Cowork ou poste local, système>

Étape atteinte : <numéro et titre de l'étape du PROMPT.md>

Ce qui a échoué (texte exact, sans reformulation) :
<erreur brute, sortie de l'outil ou du script>

Écrit dans Airtable avant l'arrêt :
- <table> — <lien> — <ce qui a été écrit>
(ou : rien)

Fourni par la recruteuse :
<le lien de la fiche si elle existe, sinon le texte tel quel>

Décisions prises seul pendant le run :
- <une par ligne>
```
