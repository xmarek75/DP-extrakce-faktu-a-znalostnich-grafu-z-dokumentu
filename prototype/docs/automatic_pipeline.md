# Automatická pipeline s lokální Ollama

Vstupem je [manifest dokumentů](../examples/input.json), nikoli anotovaný
referenční JSON. Výstup vzniká z textů skutečnými modelovými voláními.
`reference.json` se při běhu pipeline nečte. Slouží pouze jako ručně známá
reference pro testy a budoucí evaluaci.

## Příprava a spuštění

Všechny příkazy spouštěj ze složky `prototype/`, s nainstalovaným Python
balíčkem podle [hlavního návodu](../README.md).

Pokud již Ollama běží na `http://127.0.0.1:11434`, není potřeba spouštět další
server. Modely stáhni běžným `ollama pull qwen2.5:3b`. Alternativně lze použít
projektový Docker profil:

```bash
docker compose --profile llm up -d --wait ollama
docker compose exec ollama ollama pull qwen2.5:3b
.venv/bin/python -m kg_pipeline doctor --config pipeline.toml
```

Při prvním použití se stahuje Docker image a model, což vyžaduje několik GB
disku a odpovídající čas. Projektová služba používá CPU a vypíná Ollama cloud.
Případné použití NVIDIA GPU vyžaduje odpovídající konfiguraci hostitele
a kontejneru podle [oficiálního návodu](https://docs.ollama.com/docker).
Pipeline může používat i nativní lokální Ollama s již funkční GPU podporou.

Příprava grafové databáze, pokud neběží:

```bash
docker compose up -d --wait neo4j
```

Automatický průchod všemi modelovými kroky a import přijatých informací:

```bash
.venv/bin/python -m kg_pipeline run examples/input.json --config pipeline.toml --import
```

Bez `--import` vzniknou všechny JSON výstupy a plán grafu bez zápisu do databáze.
Příkaz vypisuje průběh na stderr, souhrnný JSON na stdout. Výstupní složka
je standardně `runs/<UTC-čas>-<náhodné-ID>/`. Lze ji zadat přes `--output`;
již existující složku příkaz odmítne, aby nepřepsal audit nebo data.

Pokud není přijata žádná událost, `--import` zápis přeskočí a uvede
`skipped_no_accepted_events`. Není vhodné kvůli tomu automaticky oslabovat
kontroly; podrobnosti rozhodnutí jsou v `reviews.json`.

## Kroky a rozdělení modelů

| Krok | Vstup | Výstup | Konfigurace |
|---|---|---|---|
| Načtení | Manifest a UTF-8 texty | Neměnné kopie a SHA-256 | Python |
| Entity | Text a schválený registr | Osoby, fyzické věci, citace | `models.entities` |
| Události | Text, entity a důkazy | Převody, role, čas, kandidáti | `models.events` |
| Revize | Původní text a extrakce | Rozhodnutí pro každou entitu a událost | `models.review` |
| Identity | Dokumenty, entity a důkazy | Návrhy totožnosti mezi dokumenty | `models.identity` |
| Přijetí a graf | Revize a validované záznamy | Typované uzly a hrany | Python + Neo4j |

Modely **vracejí data**, nemají nástroje pro spouštění kódu, změnu registru
nebo přímý zápis do databáze. Je to jednoduchá sekvenční orchestrace funkcí;
nevyžaduje agentní framework ani další databázi.

Role lze v [pipeline.toml](../pipeline.toml) nastavit jednotlivě. Například
po stažení dalšího modelu může revize používat jiné váhy než extrakce:

```toml
[models.entities]
model = "qwen2.5:3b"

[models.events]
model = "qwen2.5:3b"

[models.review]
model = "qwen2.5:7b"

[models.identity]
model = "qwen2.5:7b"
```

Jde o příklad konfigurace, nikoli experimentálně ověřenou nejlepší kombinaci.
Výchozí soubor používá jeden menší model pro všechny role, aby pro první
spuštění stačilo stáhnout jeden model. Oddělené prompty umožňují odlišné úkoly;
chyby stejného modelu mohou být mezi extrakcí a revizí korelované.

Pro každou roli lze nastavit `temperature`, `seed`, `num_ctx`, `num_predict`
a případně `think`. Podpora `think` záleží na zvoleném modelu; výchozí nastavení
pole neposílá. Klient používá Ollama `/api/chat`, `stream=false` a JSON Schema
v poli `format` podle [oficiální dokumentace](https://docs.ollama.com/capabilities/structured-outputs).

## Přijetí, nejistota a ontologie

Výchozí politika `acceptance = "model_review"` automaticky přijme podporované
zdrojové tvrzení pouze po následujících kontrolách:

1. Výstup odpovídá Pydantic schématu; model sám nesmí vyplnit stav `accepted`.
2. Reference, typy entit a doslovné důkazy jsou validní vůči původnímu textu.
3. Model revize posoudí každou entitu a událost právě jednou.
4. U události musí být podpořeny role, čas i modalita a přijati její účastníci.
5. Negovaná, údajná nebo připsaná událost se automaticky nepřijme.
6. Normalizovaný rok musí být číselně uveden v původní dataci. Základní kontrola
   navíc blokuje ztrátu přibližnosti u výrazů „kolem“, „asi“, „přibližně“, „cca“.
7. Shodné lokální ID nabyvatele a převodce vyžaduje v tomto MVP revizi;
   nejde o obecné omezení CIDOC CRM. Souhlas modelu tuto kontrolu nepřepíše.

`acceptance = "manual"` ponechá všechny neodmítnuté záznamy k lidské revizi.
Aktuální verze nemá schvalovací UI. `accepted` znamená přijaté **tvrzení zdroje**,
nikoli nezávisle ověřený historický fakt. Modelová revize může chybovat;
deterministické kontroly neprokazují správnost všech rolí a významů.

Revizní model dostává původní text a extrahovaný obsah bez dosavadních
aplikačních stavů `accepted`/`requires_review`. Ověřuje pouze shodu s dokumentem,
včetně fiktivního testovacího textu. Ověřování historické pravdivosti,
skutečné existence osob a totožnosti mezi dokumenty jsou odlišné úlohy.

Důkazy pro extrakci entit i událostí se vybírají z celých neprázdných řádků
zdrojového textu. Jejich doslovná znění jsou v `enum` pole `Quote.text`
generovacího schématu, které je uložené i v auditu požadavku. Model tak
nemusí citaci vytvářet zpaměti a nemůže při generování zkrátit časový nebo
negovaný kontext uvnitř řádku. Python nezávisle kontroluje výběr celého
povoleného úseku i přesnou shodu se zdrojem;
nepoužívá se oprava velikosti písmen ani přibližné párování citací.

Schéma předané reviznímu modelu omezuje počty záznamů a jejich ID podle
konkrétní extrakce; důvody mají nejvýše 200 znaků. U generovacího schématu
se vynechává pomocný neukotvený regex `\S`, který používaná Ollama nepodporuje.
Neprázdnost, délku i další omezení nadále nezávisle kontroluje Pydantic.

Návrhy identit **vždy** dostanou `requires_review`, i když model tvrdí, že
totožnost je jistá. Stejné jméno nestačí. Model nesmí schválit nové vztahy;
nepodporované informace zůstanou v `candidates`. Existující malý schválený
registr a parametrizovaný import se používají společně s referenčním demem.

## Výstupy, audit a další import

Každá složka běhu obsahuje:

```text
run.json                     # Stav, verze, hash vstupů, tokeny a časy
input.json                   # Původní vstupní manifest
config.json                  # Skutečně použitá nastavení rolí
registry.json                # Snapshot schváleného registru
ollama.json                  # Verze serveru, modely a jejich digesty
documents/*.txt              # Přesné kopie původních textů
documents/*.extracted.json   # Validovaná extrakce před revizí
stages/.../*.request.json    # Přesné modelové požadavky včetně promptu a schématu
stages/.../*.response.json   # Syrové odpovědi, včetně nevalidních pokusů
stages/.../*.validation.json # Kontroly a důvody neúspěchu jednotlivých pokusů
candidates.json              # Kandidáti před přijetím
reviews.json                 # Modelová rozhodnutí a aplikační kontroly
dataset.json                 # Finální dataset se stavy; import filtruje accepted
graph-plan.json              # Deterministický plán uzlů a hran
import.json                  # Výsledek volitelného importu
```

Generovací kontrakt vyžaduje u každého nenulového `time` pole `original_text`,
`year`, `precision` a `approximate`. Původní formulace je povinná citace;
aplikace ji za model nedoplňuje. Při chybějícím časovém údaji model vrací
`time=null`, při doložené neurčité formulaci může použít `year=null` a `precision=unknown`.
Ukládací schéma zůstává zpětně kompatibilní se staršími daty.

Nevalidní výstup se může nejvýše `max_attempts`krát opravit. Opravný pokus
dostane původní zadání, nevalidní odpověď i konkrétní validační chyby včetně
cesty k poli. Každý pokus zůstane uložený. Po vyčerpání limitu konzole vypíše
poslední důvod odmítnutí, běh skončí s chybou, `run.json` obsahuje
`failed` a nepřipraví se finální dataset pro import. Aplikace nedělá tichý
fallback na ruční referenční fakta.

Při chybě HTTP spojení nebo timeoutu se opakuje stejný modelový požadavek.
Diagnostika spojení zůstává v auditu a nevkládá se modelu jako chyba
extrahovaných dat. Počet všech pokusů je stále omezený `max_attempts`.

`dataset.json` je samostatně načitatelný stávajícími příkazy; cesty k textům
vedou na snapshoty uvnitř složky běhu:

```bash
.venv/bin/python -m kg_pipeline validate runs/ID/dataset.json
.venv/bin/python -m kg_pipeline import runs/ID/dataset.json
.venv/bin/python -m kg_pipeline query runs/ID/dataset.json acquisitions
.venv/bin/python -m kg_pipeline query runs/ID/dataset.json provenance
```

Každý nový extrakční běh dostane vlastní verzi datasetu, aby se výsledky
různých modelů nebo promptů nepřepisovaly. Opakovaný import téhož výsledku
je idempotentní. V Neo4j Browseru použij vypsané `import_id`:

```cypher
MATCH (n:KGNode {import_id: 'SEM_VLOZ_IMPORT_ID_Z_VYSTUPU'})
OPTIONAL MATCH (n)-[r]->(m:KGNode)
RETURN n, r, m;
```

## Omezení první verze

- Vstupy jsou UTF-8 texty; PDF, OCR a HTR zatím nemají vlastní načítací krok.
- Výběr důkazů používá celé řádky; tvrzení přes více řádků může potřebovat
  několik důkazů. Opakovaný totožný úsek bez rozlišené pozice zůstává
  nejednoznačný a validátor ho odmítne. Segmentace složitějších dokumentů
  a výběr konkrétního výskytu jsou další krok.
- Automatické chunkování není implementováno. Delší dokument se odmítne podle
  `max_document_chars`; text se tiše nezkracuje. Při velké kolekci se přeskočí
  návrhy identit s výslovným stavem `deferred_context_limit` v auditu.
- Kvalitu odpovědí, úplnost extrakce a vhodnost modelů je potřeba vyhodnotit.
  Průchod JSON validací ani souhlas dvou modelových kroků nezaručuje správnost.
- Normalizují se jen mezery a Unicode v zobrazovaných názvech. Citace i
  originální texty zůstávají zachované. Pokročilá normalizace není hotová.
- Časový model podporuje rok, přibližnost a neznámou dataci; další granularity
  a alternativní historické kalendáře vyžadují rozšíření schématu.
- Úplná automatická ontologická revize a kanonické slučování entit nejsou hotové.
- Audit počítá tokeny a časy všech pokusů. Cena cloudového API je nula;
  náklady na hardware a elektřinu se neměří.
- Aplikace akceptuje jen lokální HTTP endpoint, vypíná proxy a odmítá
  přesměrování i modely odkazující na vzdálenou Ollama.

Unit testy používají náhrady modelů. Integrační testy s `KG_RUN_INTEGRATION=1`
ověřují také skutečný import výstupu pipeline do Neo4j; samotné LLM volání
v těchto automatických testech je záměrně nahrazené. Skutečný modelový běh
se provádí příkazem `run` a má vlastní audit v `runs/`.
