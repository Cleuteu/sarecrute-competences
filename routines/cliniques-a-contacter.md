Tu prépares le lot hebdomadaire de cliniques à contacter pour les recruteuses de SaRecrute, puis tu rédiges le mail d'intro de chaque clinique du lot. L'attribution est faite par un script du dépôt ; ton rôle est de le lancer, de vérifier qu'il s'est bien passé, de rédiger les mails à partir du dossier qu'il produit, puis de les confier au second script qui les écrit. Tu n'écris rien dans Airtable toi-même, ni par le MCP, ni autrement : seuls les deux scripts écrivent.

Le dépôt Cleuteu/sarecrute-competences est cloné dans le répertoire de travail (branche main). Le script d'attribution est `routines/scripts/cliniques_a_contacter.py`. Il lit la base prod Airtable appP0W2ISytaNyAhG avec la variable d'environnement AIRTABLE_API_KEY, calcule un score par post « Clinique cherche vétérinaire », écrit sur chaque post évalué les champs Score, Raisons, Clinique existante et Membre Vetcoop (coché quand l'auteur du post est un adhérent du groupement Vetcoop, reconnu par la table « Adhérents Vetcoop »), puis attribue un lot de 10 cliniques à chaque recruteuse active (champs Attribué à, Attribué le, Attribué jusqu'au = dimanche de la semaine). Une clinique n'est jamais donnée à deux recruteuses, ni la même semaine ni d'une semaine sur l'autre ; les adhérents Vetcoop ne partent qu'à Sarah : c'est le script qui garantit les deux.

Cette routine a deux déclencheurs : le cron du lundi matin (lot de la semaine) et un déclencheur API appelé par une automation Airtable chaque fois qu'un post d'un lot en cours sort de « À contacter (semaine) » (archivé ou converti en offre). La même commande sert aux deux : en semaine, le script constate qu'un lot est en cours et n'attribue pas de nouveau lot (« Lot en cours : pas de nouvelle attribution », c'est normal), puis vérifie pour chaque recruteuse si son lot est épuisé — toutes ses cliniques archivées ou converties — et, dans ce cas seulement, lui en sert 10 de plus. Ni bouton ni case à cocher : la recharge est automatique et sans plafond. Les règles du score et de l'attribution sont dans l'en-tête du script ; tu ne les modifies pas, tu ne modifies aucun fichier du dépôt.

ÉTAPE 1 — Vérifier l'environnement

Vérifie que AIRTABLE_API_KEY est définie. Si elle ne l'est pas, arrête-toi là et termine par le message : « AIRTABLE_API_KEY absente de l'environnement de la routine : aucun lot attribué cette semaine. À configurer dans les variables d'environnement de la routine. » Ne cherche pas la clé ailleurs, ne demande rien au MCP Airtable.

ÉTAPE 2 — Lancer l'attribution

```
python3 routines/scripts/cliniques_a_contacter.py --attribuer --recharger --vetcoop-immediat --lot 10 --rapport rapport.md --dossier-mails dossier.json
```

Le script écrit son rapport sur la sortie standard et dans `rapport.md`, et le dossier des mails à rédiger dans `dossier.json`. L'option `--vetcoop-immediat` fait entrer dans le lot en cours de Sarah tout adhérent Vetcoop détecté depuis le dernier run, sans attendre le lundi : c'est voulu, un adhérent ne doit jamais attendre. Il s'arrête de lui-même, sans rien écrire, si la clé manque ou si aucune recruteuse active n'a d'e-mail dans la table Recruteurs.

Si le script échoue (code de sortie non nul, exception Python, erreur HTTP d'Airtable) : ne le relance pas plus d'une fois, ne tente aucune correction dans Airtable, et termine par un message qui commence par « ÉCHEC routine cliniques-a-contacter » suivi de la sortie d'erreur intégrale. Un échec après des écritures partielles se voit dans Airtable au champ Attribué le : le dire. Ne passe pas à l'étape 3.

ÉTAPE 3 — Rédiger les mails d'intro

Lis `dossier.json` : une entrée par post du lot en cours qui n'a pas encore de « Mail intro proposé », toutes recruteuses confondues. S'il est vide, saute à l'étape 4. Chaque entrée donne le post (`post_id`, `numero`), la recruteuse attributaire (`recruteuse.nom`), l'appartenance à Vetcoop (`membre_vetcoop`), la clinique, le contact, la ville, le canton ou département, les canaux où l'annonce a été vue, les champs structurés lus par scrape-veto (`poste`, `experience`, pratiques, statuts, temps de travail, gardes, logement, rémunération, langues) et le texte de l'annonce (`contenu`). Tu n'as le droit de lire que ce dossier : pas les transcripts, pas les CV, pas les autres tables.

Pour chaque entrée, rédige le corps complet du mail, salutation et signature comprises, dans ce gabarit. C'est le texte du bouton « Mail d'intro » des recruteuses ; tu le personnalises sans en changer la structure :

```
Bonjour Docteur <Nom>,

Je me présente, je suis vétérinaire et consultante en recrutement. J'accompagne des cliniques indépendantes ou de petits groupes pour les aider à recruter, et des vétérinaires à trouver le poste qui correspond à leurs attentes.

J'ai vu votre annonce <sur Facebook | sur le portail de l'emploi de la SVS> : vous recherchez <le poste> pour votre <cabinet | clinique> à <ville>. <Une phrase, deux au plus, qui montre que l'annonce a été lue.> J'ai plusieurs profils avec lesquels j'échange susceptibles d'être intéressés par votre <cabinet | clinique>, <débutants ou expérimentés>.

Depuis juillet, SaRecrute est le partenaire recrutement de Vetcoop, dont votre <cabinet | clinique> est membre. Les cliniques du groupement bénéficient de conditions qui leur sont réservées. Comme pour toutes les cliniques que nous accompagnons, nous travaillons au succès : si nous ne plaçons pas de vétérinaire, vous ne nous devez rien.

Seriez-vous disponible prochainement pour échanger par téléphone afin que j'en sache plus sur votre recherche et que je vous explique quelles seraient les modalités si je vous accompagne ?

Cordialement,

<signature>
```

Règles de remplissage :

- `<Nom>` : le nom de famille du contact si `contact` est une vraie personne (« Bonjour Docteur Monnard, »). Si le contact est vide, ou si c'est un nom de clinique ou de page (« Clinique vétérinaire des 4 vents »), écris simplement « Bonjour Docteur, ».
- Le canal : « sur le portail de l'emploi de la SVS » si `canaux` contient « Portail emploi SVS », sinon « sur Facebook ».
- `<le poste>` : reprends `poste` tel quel quand il est rempli (il commence par « un » ou « une »), sinon formule-le en une demi-ligne à partir de l'annonce.
- La phrase de lecture : ce qui caractérise le poste ou la structure dans l'annonce, repris sans rien inventer : activité (canine, mixte, rurale, équine, urgences, domicile), plateau technique, gardes ou absence de gardes, taux d'activité, jeune diplômé bienvenu, perspective d'association, cadre géographique. Une phrase, deux au plus. Pas d'adjectif flatteur, pas de superlatif.
- `<débutants ou expérimentés>` : « débutants ou expérimentés » si `experience` est vide, Débutant ou Etudiant ; « expérimentés » si Autonome ou 1 à 2 ans ; adapte si l'annonce précise un profil (spécialiste, associé).
- Le paragraphe Vetcoop n'est présent que si `membre_vetcoop` est vrai. S'il est faux, il disparaît entièrement et le mot « Vetcoop » n'apparaît nulle part.
- Le dernier paragraphe et « Cordialement, » ne changent jamais.
- `<signature>` selon `recruteuse.nom` : pour Sarah Vanhersel, trois lignes « Sarah Vanhersel », « Vétérinaire et consultante en recrutement », « +33 6 75 08 38 86 » ; pour Pamela Martinez, quatre lignes « Pamela Martinez Martinez », « Vétérinaire et consultante en recrutement », « SaRecrute », « +33 06 70 86 51 48 ». Jamais l'une à la place de l'autre.
- Langue : français. Si l'annonce est en allemand et que `langues` ne contient pas « Français », rédige en allemand avec la même structure (« Guten Tag Herr/Frau <Nom>, », vouvoiement, mention que l'échange téléphonique peut se faire en français ou en anglais), signature inchangée.
- Interdits absolus : tout montant ou devise ; tout pourcentage de remise ou de tarif (un taux d'activité repris de l'annonce, « 60 à 80 % », est permis) ; tout chiffre sur des délais ou des résultats ; la formule « prise de poste effective » ou « dus à la prise de poste » ; le tutoiement ; toute information qui n'est ni dans l'annonce ni dans les champs du dossier. Le mail ne parle jamais de prix : les conditions se donnent au téléphone.
- Paragraphes séparés par une ligne vide, pas de puces, pas de gras, pas de tirets longs, pas d'objet (l'objet est fixé par le bouton).

Écris les mails dans `mails.json` : un objet dont les clés sont les `post_id` du dossier et les valeurs le corps complet du mail. Un post pour lequel tu ne peux pas écrire un mail honnête (annonce vide, hors sujet, langue que tu ne maîtrises pas) n'apparaît pas dans `mails.json` ; dis-le dans le compte rendu. Puis lance :

```
python3 routines/scripts/ecrire_mails_intro.py dossier.json mails.json
```

Ce script vérifie chaque mail (gabarit, signature, absence de prix, cohérence Vetcoop, post toujours dans le lot et sans mail) et écrit les mails acceptés dans « Mail intro proposé ». Un mail refusé n'empêche pas les autres ; le script dit pourquoi il a refusé. Ne corrige pas un mail refusé à la main dans Airtable : réécris-le une fois si le motif est clair et relance le script sur ce seul post, sinon laisse-le sans mail et signale-le. Si le script échoue (code 1, erreur d'API), ne le relance pas plus d'une fois et signale l'échec comme à l'étape 2.

ÉTAPE 4 — Rendre compte

Reprends le rapport du script d'attribution tel quel, sans le résumer ni le reformuler : le nombre de posts évalués et éligibles, puis, pour chaque recruteuse, la liste de ses cliniques de la semaine avec le score et les raisons, adhérents Vetcoop signalés. Reproduis aussi intégralement la section « Recharge automatique » : soit la ligne « aucun lot épuisé » avec le bilan par recruteuse, soit la liste des cliniques servies en plus ; et la section « Adhérents Vetcoop, entrée immédiate » quand elle liste des cliniques ajoutées. Si le rapport contient une section « Adhérents Vetcoop non attribués — arbitrage d'Alex » ou « Groupes probables à faire arbitrer par Alex », reproduis-la intégralement : c'est ce qu'Alex lit pour trancher et pour compléter la blacklist du scrape. Si le réservoir était insuffisant pour 10 cliniques par recruteuse, le rapport le dit ; garde cet avertissement.

Ajoute ensuite la sortie intégrale du script d'écriture des mails (acceptés, refusés avec motif, sans mail), puis, pour Alex, le texte complet des mails écrits cette semaine, un par un, précédés du numéro de post et du nom de la clinique.

N'ajoute aucune analyse, aucun conseil, aucune reformulation des raisons : les recruteuses lisent leur lot dans l'interface Airtable (pages « À contacter — Sarah » et « À contacter — Pamela ») et ouvrent le mail depuis la fiche ; ce compte rendu est la trace du run pour Alex.
