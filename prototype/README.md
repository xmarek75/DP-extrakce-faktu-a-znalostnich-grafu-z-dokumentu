# Prototyp extrakce faktů a znalostního grafu

Prototyp podporuje automatickou lokální pipeline:
**texty → model pro entity → model pro události → modelová revize
→ návrhy identit → validace → volitelný import do Neo4j**.
Pro jednotlivé role lze nastavit různé modely přes Ollama.

**[Návod k automatické pipeline](docs/automatic_pipeline.md)** popisuje spuštění,
konfiguraci modelů, audit a omezení. Původní ruční referenční import zůstává
k dispozici pro testování a porovnání výsledků.

Modelová revize není nezávislé ověření historické pravdy. Demo dokumenty,
osoby, majetek a události jsou **fiktivní**. Modelová volání míří výhradně
na lokální Ollama, nikoli na cloudové API.

## Rychlé spuštění v připraveném workspace

Automatická pipeline po spuštění Ollama a stažení modelu:

```bash
.venv/bin/python -m kg_pipeline doctor --config pipeline.toml
.venv/bin/python -m kg_pipeline run examples/input.json --config pipeline.toml --import
```

Podrobná příprava je v [návodu](docs/automatic_pipeline.md). Následující
příkazy spouštějí původní **ruční referenční import**.

Při první implementaci bylo vytvořeno lokální prostředí `.venv/`, soukromý
konfigurační soubor `.env` s náhodným heslem a spuštěna projektová Neo4j.
Tyto lokální soubory nejsou verzovány. Následující příkazy spouštěj ze složky
`prototype/`:

```bash
.venv/bin/python -m kg_pipeline validate examples/reference.json
.venv/bin/python -m kg_pipeline import examples/reference.json
.venv/bin/python -m kg_pipeline query examples/reference.json acquisitions
```

Pokud byla databáze zastavena, spusť ji příkazem `docker compose up -d --wait`.

## Instalace v novém klonu

Požadavky: Python 3.11 nebo novější s podporou `venv` a `pip`, Docker Engine
a Docker Compose. Na Ubuntu může být potřeba doinstalovat balíček
`python3-venv`. Příkazy níže předpokládají nový klon bez připraveného `.env`.

```bash
cd prototype
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements-lock.txt -e '.[dev]'
cp .env.example .env
```

V `.env` nastav vlastní `NEO4J_PASSWORD` o délce alespoň 8 znaků. Heslo je určeno
pro nově inicializovanou databázi; jeho změna v souboru nezmění heslo již
existující databáze. Přihlašovací údaje nepatří do verzování ani do URI.

```bash
docker compose up -d --wait
.venv/bin/python -m kg_pipeline validate examples/reference.json
.venv/bin/python -m kg_pipeline import examples/reference.json
```

Neo4j naslouchá pouze na lokálních adresách. Výchozí porty jsou `7474` pro Browser
a `7687` pro Bolt. Při kolizi lze v `.env` změnit `NEO4J_HTTP_PORT`,
`NEO4J_BOLT_PORT` a odpovídající `NEO4J_URI`. Python čte `.env` v pracovním
adresáři; jiný soubor lze předat pomocí `--env-file cesta/.env` příkazům
`import` a `query`. Existující proměnné prostředí mají přednost.

## Očekávaný výsledek

Referenční dataset má **25 uzlů a 37 hran**: 3 dokumenty, 6 důkazů, 6 lokálních
osob, 3 lokální objekty, 3 tvrzené převody, 3 časová vymezení a 1 technický
záznam importu. Dvě vlastní hrany `SAME_ENTITY_AS` propojují ručně revidované
identity mezi D001 a D002, jejich lokální uzly zůstávají zachovány.

| Dokument | Nabyvatel | Převodce | Předmět | Datace |
|---|---|---|---|---|
| D001 | Matěj Kovář | Václav Svoboda | Dům U Modré hvězdy v Brně | Roku 1521 |
| D002 | Anna Malá | Matěj Kovář | Tentýž dům | Roku 1524 |
| D003 | Matěj Kovář z Olomouce | Jan Dlouhý | Zahrada | Kolem roku 1530 |

Matěj z D003 zůstává samostatný. Text nedokládá jeho totožnost s Matějem z D001.
Údajné přátelství a negovaná koupě mlýna jsou zachovány v kandidátním JSON;
nevytvářejí vztah přátelství ani další převod. Samotné textové důkazy kandidátů
jsou v grafu uloženy jako citace, ne jako přijatá historická tvrzení.

Opakované spuštění `import` se stejným vstupem vrátí `created_data_nodes: 0`
a `created_edges: 0`. Čítač datových uzlů nezahrnuje technický marker importu.

## Dotazování a zobrazení grafu

```bash
.venv/bin/python -m kg_pipeline query examples/reference.json acquisitions
.venv/bin/python -m kg_pipeline query examples/reference.json cross_document
.venv/bin/python -m kg_pipeline query examples/reference.json provenance
.venv/bin/python -m kg_pipeline query examples/reference.json counts
```

`acquisitions` vrací účastníky, předmět, čas a citaci. `cross_document` ukazuje
revidované identity, důvod a odkazy na důkazy. `provenance` vrací také offsety
a úsek z uloženého textu pro kontrolu citace. `counts` umožňuje ověřit počty
před opakovaným importem a po něm. Dotazy jsou součástí balíčku
v [src/kg_pipeline/queries/](src/kg_pipeline/queries/).

V [Neo4j Browseru](http://localhost:7474) se přihlas jako `neo4j` heslem z `.env`.
Pro zobrazení výchozího referenčního grafu spusť:

```cypher
MATCH (n:KGNode {import_id: '582874b4-3a73-57ab-a273-fcc217da44f6'})
OPTIONAL MATCH (n)-[r]->(m:KGNode {import_id: '582874b4-3a73-57ab-a273-fcc217da44f6'})
RETURN n, r, m;
```

ID odpovídá datasetu `synthetic-acquisitions`, verzi `1.0.0`. Pro jiný dataset
použij `import_id` vypsané příkazem `import` nebo `plan`. Filtr oddělí demo
od jiných verzí i od integračních testů. Databázi lze zastavit bez mazání dat:

```bash
docker compose stop
```

## Schéma, důkazy a identity

- [examples/reference.json](examples/reference.json) je vlastní meziformát,
  nikoli RDF nebo JSON-LD. `source_file` se vyhodnocuje vůči složce tohoto JSON;
  zdroje nesmějí ležet mimo ni. Textové vstupy jsou UTF-8.
- Pydantic odmítá nepovolené typy, neznámá pole, duplicitní ID, chybějící důkazy
  a neplatné reference. Přijaté události smějí odkazovat jen na přijaté entity.
  Výchozí stav entit a událostí je `requires_review`.
- Důkaz musí doslova existovat ve zdrojovém textu. Chybějící offsety aplikace
  dopočítá jen pro jednoznačný výskyt. Dodané offsety ověří. Jde o indexy
  Unicode znaků od nuly, s koncem mimo citovaný úsek; text včetně CRLF se nemění.
- Normalizovaná jména jsou v referenčních datech připravena ručně. Jméno není
  identifikátor; stabilní UUID vychází z datasetu, verze, dokumentu, druhu
  záznamu a lokálního ID. Pipeline normalizuje mezery a Unicode v názvech;
  pokročilá normalizace a automatické schvalování identit nejsou implementovány.
- Ruční propojení vyžaduje stav `accepted`, identifikaci revidujícího, důvod
  a platné důkazy z obou dokumentů. Podobnost jmen propojení nevytváří.
- `precision: year` popisuje granularitu, `approximate: true` přibližnost.
  `precision: unknown` nepovolí normalizovaný rok. Den ani měsíc se nedoplňují.
- `accepted` znamená přijetí zdrojového tvrzení podle referenční anotace,
  nikoli nezávislé ověření historické pravdy. Validátor neumí sám posoudit
  správnost rolí, negaci v libovolném textu ani kalibrovat jistotu modelu.
- Graf událostí má `epistemic_status: source_assertion`. Výpovědi různých
  dokumentů zůstávají samostatné, aby se navzájem nepřepisovaly.

Schéma a aktuální registr lze vypsat bez databáze:

```bash
.venv/bin/python -m kg_pipeline schema
.venv/bin/python -m kg_pipeline registry
.venv/bin/python -m kg_pipeline plan examples/reference.json
.venv/bin/python -m kg_pipeline plan examples/reference.json --output runs/reference-plan.json
```

Původní export schématu je v [schemas/extraction-v1.schema.json](schemas/extraction-v1.schema.json).
Schéma [1.1](schemas/extraction-v1.1.schema.json) navíc podporuje provenienci
automatického běhu; importér přijímá obě verze. Původní fingerprinty zůstávají zachovány.
JSON Schema kontroluje strukturu; kontroly referencí a důkazů provádí Python
navíc. Volba `--output` u příkazů `schema`, `registry` a `plan` odmítá přepsat
existující soubor. Složka `runs/` není verzována.

## Ontologické mapování a zjednodušení

Ruční schválený registr je v [ontology.py](src/kg_pipeline/ontology.py),
verze `1.0.0`. Vychází z definic [CIDOC CRM 7.1.3](https://cidoc-crm.org/html/cidoc_crm_v7.1.3.html).
Není to úplná implementace CIDOC CRM ani RDF úložiště.

| Aplikační typ | Mapování |
|---|---|
| `Person`, `PhysicalThing`, `Acquisition`, `TimeSpan` | E21, E18, E8, E52 |
| `TRANSFERRED_TITLE_TO` | P22: událost → nabyvatel |
| `TRANSFERRED_TITLE_FROM` | P23: událost → převodce |
| `TRANSFERRED_TITLE_OF` | P24: událost → fyzická věc |
| `HAS_TIME_SPAN` | P4: událost → čas |
| `Document`, `Evidence`, `KGImport` | Vlastní aplikační pojmy v `urn:dp:` |
| `SUPPORTED_BY`, `FOUND_IN`, `SAME_ENTITY_AS` | Vlastní aplikační vztahy v `urn:dp:` |

P22 a P23 v ontologii směřují na E39 Actor; MVP podporuje jen jeho podtyp
E21 Person. Podobně používáme P4 pouze pro převody, ačkoli oficiální doména
je širší. Registr zachycuje lokální doménu i obor hodnot, původ, URI, verzi,
směr a případnou symetrii/inverzi. `SAME_ENTITY_AS` se dotazuje obousměrně,
fyzicky se ukládá jednou. Nejedná se o standardní vlastnost CIDOC CRM.

Kandidátní návrhy typů nejsou registrací. Schvalovací UI a automatické hledání
v celé ontologii nejsou implementovány; rozšíření registru vyžaduje ruční
sémantickou revizi, změnu verze registru a navazujícího schématu/importu.

## Neměnné verze a reprodukovatelnost

Import používá parametrizovaný Cypher, unikátní omezení na `KGNode.id`
a jednu datovou transakci. Názvy labelů a hran pocházejí pouze ze schváleného
registru. Způsob transakčního zápisu vychází z
[oficiálního Neo4j driveru](https://neo4j.com/docs/python-manual/current/transactions/).

SHA-256 zahrnuje celý validovaný JSON i skutečné texty. Změna dat pod stejným
`dataset_id` a `dataset_version` import odmítne bez přepsání dat. Při úpravě
anotace nebo textu zvyš `dataset_version`; vznikne samostatný snapshot.
ID dokumentů je proto stabilní uvnitř verze datasetu, nikoli automaticky
napříč různými verzemi nebo extrakčními běhy. Mazání a migrace nejsou součástí
tohoto prototypu.

`requirements-lock.txt` zaznamenává ověřené verze knihoven, Compose připíná
Neo4j na `5.26.0-community`, volitelná Ollama na `0.40.16`. Referenční dataset
má verzi `1.0.0` a metodu `manual_reference`. Automatické běhy používají schéma
`1.1.0`, metodu `ollama_pipeline` a vlastní verzi snapshotu. Modely, prompty,
kontrolní součty, tokeny a časy jsou v auditu jednotlivého běhu.

## Testy

Lokální testy nevyžadují Neo4j ani placené API:

```bash
.venv/bin/python -m pytest -q
```

Integrační testy je nutné explicitně zapnout při běžící databázi a nastaveném
`.env`. Ověřují skutečné dotazy, důkazy, idempotenci a odmítnutí změněných dat:

```bash
KG_RUN_INTEGRATION=1 .venv/bin/python -m pytest -q
```

Testy vytvářejí vlastní náhodné verze datasetu. Nic nemažou; jejich malé
fiktivní grafy zůstávají v databázi a lze je odfiltrovat podle `import_id`.
Po opravě citací a revize prošlo **94 testů včetně 3 integračních**.
Bez explicitního zapnutí integrace prošlo 91 testů a 3 byly přeskočeny.
Modelové odpovědi jsou v automatických testech nahrazené; integrační testy
ověřují skutečnou Neo4j. Ověřené prostředí:
Python 3.12.3, Neo4j 5.26.0 Community, Docker Engine 29.7.2, Compose 5.5.0.

## Další kroky

Vyhodnotit kvalitu různých konfigurací modelů proti referenční sadě, doplnit
chunkování dlouhých dokumentů a lidskou revizi návrhů identit a nových typů.
Současný graf zachovává dokumentové lokální identity; kanonické sjednocování
uzlů osob a objektů je samostatná další změna modelu.

Návrhové podklady: [AGENTS.md](../AGENTS.md),
[návrh prototypu](../knowledge_graph_prototype_design.md),
[rozsah informací](../knowledge_graph_information_scope.md)
a [modely a serializace](../docs/knowledge_graph_serialization.md).
