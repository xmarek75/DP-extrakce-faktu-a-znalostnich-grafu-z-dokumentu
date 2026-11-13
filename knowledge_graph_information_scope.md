# Rozsah extrahovaných informací a granularita znalostního grafu

> **Stav dokumentu:** Pracovní analýza a návrh pro diplomovou práci „Extrakce faktů a znalostních grafů z dokumentů“. Následující rozhodnutí jsou výchozí hypotézy pro prototyp, nikoliv definitivní výsledky experimentů.
>
> **Vazba na další dokumenty:** `knowledge_graphs_analysis.md` (reprezentace znalostí), `knowledge_graph_prototype_design.md` (uvažovaná implementační architektura).

## 1. Motivace

Při konstrukci znalostního grafu (KG) z historických dokumentů nestačí vybrat technologii ukládání dat. Je nutné rozhodnout také **které informace se mají z dokumentu získat**, **které z nich budou tvořit strukturovaný graf** a **jak podrobně budou v grafu popsány**.

Příliš úzký rozsah extrakce vede ke ztrátě relevantních faktů a omezuje budoucí dotazy a explorativní analýzu. Příliš široký rozsah naopak zvyšuje cenu zpracování, množství duplicit, složitost normalizace a riziko chybných nebo nepodložených tvrzení. Cílem je najít **kompromis mezi úplností, správností, použitelností a náklady**.

Uvažovaným scénářem je sbírka historických dokumentů (například archiv o desítkách tisíc dokumentů podobný semANTu), včetně textů z 15. a 16. století a textů získaných pomocí OCR/HTR. Přesný rozsah a charakter dat je nutné upřesnit po výběru testovací kolekce.

### Tři různá rozhodnutí, která se nesmějí zaměňovat

1. **Šířka extrakce (*extraction scope*):** Kolik různých typů faktů se systém pokusí v textu najít?
2. **Šířka uložení (*storage scope*):** Které kandidátní informace se dostanou do hlavního KG, které zůstanou ve vedlejší vrstvě a které se nebudou strukturovat?
3. **Granularita reprezentace (*modeling granularity*):** Bude informace uložena jako vlastnost, přímý vztah, samostatná událost nebo tvrzení s vlastní identitou a důkazem?

Všechny tři dimenze lze měnit nezávisle. Například je možné extrahovat širokou množinu kandidátních faktů, ale do hlavního grafu ukládat jen ověřené typy, a přitom modelovat významné historické události podrobně.

---

## 2. Krajní strategie a jejich kompromisy

| Strategie | Princip | Výhody | Rizika |
|---|---|---|---|
| **Úzká, schématem řízená extrakce** | Extrahují se jen předem určené entity, události a vztahy. | Konzistence, snadnější validace a evaluace, nižší složitost. | Nezachycení nečekaných informací, omezení budoucích use cases. |
| **Široká / otevřená extrakce** | Extrahují se i typy tvrzení bez předem vymezené ontologie. | Vyšší potenciální pokrytí, objevování nových druhů vazeb. | Nesjednocené názvy vztahů, více šumu, obtížnější kontrola správnosti. |
| **Hybridní přístup (doporučený k ověření)** | Širší extrakce kandidátů → normalizace → výběr pro hlavní KG. | Zachování možností rozšíření i konzistentního veřejného grafu. | Složitější pipeline a dvě vrstvy správy dat. |

**Pracovní volba:** Pro první prototyp zvolit **omezené doménové jádro** (osoby, místa, organizace, dokumenty, události, čas, účastníci, provenance) a zároveň **uchovávat širší výstup extrakce** pro pozdější rozšíření. Nemusí jít hned o plnohodnotnou Open Information Extraction (OpenIE) nad každou větou; šířka kandidátní extrakce se musí přizpůsobit nákladům a kvalitě modelu.

---

## 3. Jaký problém má graf řešit? (Competency questions)

Rozsah grafu je vhodné odvozovat od otázek, na které má systém umět odpovídat. Příklady jsou ilustrativní; finální seznam se musí opírat o vybrané historické dokumenty a potřeby uživatelů.

| Kód | Typická otázka | Potřebná data |
|---|---|---|
| CQ1 | Které dokumenty zmiňují konkrétní historickou osobu? | Entita, varianty jména, zmínka, dokument, pozice v textu. |
| CQ2 | Kdo byl ve vztahu k určité osobě a jak? | Identita osob, typované vztahy, důkaz. |
| CQ3 | Kdo vlastnil nemovitost v Brně v určitém období? | Osoby, nemovitosti, vlastnické události/vztahy, čas, místo. |
| CQ4 | Jaké události souvisejí s danou osobou? | Události, role účastníků, čas, místo, zdroj. |
| CQ5 | Které osoby jsou nepřímo propojeny přes jiné osoby nebo události? | Sjednocené identity, vícekrokové cesty grafem. |
| CQ6 | Které dokumenty se neshodují v datu určité události? | Samostatná tvrzení, hodnoty, zdroje a stav validace. |
| CQ7 | Jaké souvislosti lze v kolekci objevit bez předem známého konkrétního výsledku? | Dostatečně široké typované vztahy, grafová analýza, provenance. |

**Poznámka:** U otázek typu „všechny osoby…“ lze garantovat úplnost pouze **v rámci správně a úplně extrahovaných dat**, nikoliv automaticky vůči celé původní sbírce.

---

## 4. Co extrahovat: doporučené doménové jádro

### 4.1 Entity

| Kategorie | Příklady | První prototyp | Poznámka |
|---|---|---|---|
| **Osoby** | Matěj Kovář, Václav Svoboda | **Ano** | Stabilní identifikátor, různé podoby jména, nejistá identita. |
| **Skupiny a organizace** | Městská rada, cech | **Ano** | Rozlišovat instituci od jejích členů a funkcí. |
| **Místa** | Brno, konkrétní dům, městská část | **Ano** | Historické názvy a proměny správních hranic. |
| **Fyzické objekty / majetek** | Dům, pozemek, listina jako objekt | **Ano, jsou-li relevantní** | Nevytvářet falešnou identitu pro neurčitý „nějaký dům“. |
| **Dokumenty a jejich části** | Kupní smlouva, odstavec, OCR segment | **Ano** | Důležité pro provenance, vyhledávání a evaluaci. |
| **Časové údaje** | Rok 1521, „kolem roku 1520“ | **Ano** | Přesné, intervalové i nejisté datování. |
| **Obecné pojmy** | Obchodník, purkmistr, cechovní mistr | **Selektivně** | Často stačí typ/role; uzel dává smysl pro sdílený koncept nebo hierarchii. |
| **Abstraktní témata a hodnotící soudy** | Hospodářský rozkvět, významný měšťan | **Zatím ne jako tvrdé fakty** | Lze zachovat jako textové tvrzení k revizi. |

### 4.2 Vztahy a historické události

Událostně orientovaný model je vhodný, pokud má tvrzení více účastníků, rolí, časové vymezení nebo je potřeba zachovat různé zdroje.

| Kategorie | Příklad | Doporučená reprezentace |
|---|---|---|
| Příbuzenské vztahy | Otec–dcera | Typovaný vztah; pokud je datovaný, nejistý či rozporovaný, doplnit tvrzení s proveniencí. |
| Převod vlastnictví | Koupě domu | **Samostatná událost** s kupujícím, prodávajícím, objektem, datem a zdrojem. |
| Životní události | Narození, úmrtí | Událost s osobou, časem a místem. |
| Manželství | Sňatek | Událost/časově omezený vztah, účastníci a zdroj. |
| Úřady a funkce | Působení purkmistra | Časově vymezené zastávání funkce, role, instituce. |
| Obchodní a právní jednání | Smlouva, dluh, soudní spor | Událost, pokud ji podklady a ontologie umožní modelovat. |
| Pohyb a pobyt | Příjezd, cesta, bydliště | Odlišovat jednorázovou událost od dlouhodobého stavu. |
| Pouhá společná zmínka | Dvě osoby ve stejné listině | `CO_MENTIONED` pouze jako pomocná analytická vazba, **nikoliv důkaz sociálního vztahu**. |

Názvy v tabulce jsou **pracovní kategorií extrakce**, nikoliv automaticky přesnými třídami CIDOC CRM. Mapování je nutné ověřit vůči konkrétní verzi ontologie.

### 4.3 Co většinou nemodelovat jako samostatný uzel

Běžný letopočet, číselnou hodnotu, měnu uvedenou v jediném kontextu, přídavné jméno nebo sloveso není nutné automaticky měnit v samostatnou entitu. Často se hodí jako **atribut** konkrétní události či tvrzení. Samostatný uzel má smysl zejména tehdy, když objekt potřebuje **identitu, více atributů, vlastní vztahy nebo opakované sdílení**.

Rozhodnutí není globální: `150 zlatých` může být jednoduchá vlastnost transakce; v detailním ekonomickém modelu může být potřebná normalizovaná peněžní částka, měnová jednotka, způsob přepočtu a provenance.

---

## 5. Praktický příklad: jeden dokument, několik úrovní reprezentace

**Ilustrační vstupní text:**

> Roku 1521 koupil Matěj Kovář od Václava Svobody dům v Brně za 150 zlatých. Při uzavření smlouvy byl přítomen Jan Novák jako svědek. Matěj Kovář byl podle kronikáře významným obchodníkem. V té době město údajně hospodářsky vzkvétalo.

### 5.1 Výběr informací

| Informace | Extrahovat? | Uložit do hlavního KG? | Jak? |
|---|---|---|---|
| Matěj, Václav, Jan | Ano | Ano | Uzly osob. |
| Brno | Ano | Ano | Uzel místa. |
| Dům | Ano | Ano, pokud lze rozlišit konkrétní objekt | Uzel objektu; jinak kandidát s neurčitou identitou. |
| Koupě domu v roce 1521 | Ano | Ano | Uzel události a typované vazby. |
| Kupující, prodávající, svědek | Ano | Ano | Role účastníků události, doložené textem. |
| Cena 150 zlatých | Ano | Ano | Atribut/tvrzení události s měnou a důkazem. |
| „Významný obchodník“ | Ano | **Jen podmíněně** | Oddělit doložené označení povolání od hodnotícího slova „významný“. |
| „Město údajně vzkvétalo“ | Volitelně jako kandidát | Ne jako jednoznačný fakt | Zachovat doslovné tvrzení a jeho modalitu. |

### 5.2 Nedostatečná reprezentace

```text
(Matěj Kovář)-[:BOUGHT]->(Dům)
```

Ztrácí se prodejce, svědek, rok, cena, zdroj i možnost popsat rozdílné interpretace události.

### 5.3 Doporučená reprezentace

```text
                   (Koupě domu #E001)
                /        |        |        \
       kupující       prodávající předmět  svědek
           |              |        |         |
      Matěj Kovář   Václav Svoboda Dům    Jan Novák
                \
                 [čas: 1521]
                 [cena: 150 zlatých]
                 [místo: Brno]
                 [doloženo: tvrzení #A001]
                                       |
                                (Dokument #D001)
                                [textový úsek]
```

Textové schéma je zjednodušení. Pro striktnější mapování na CIDOC CRM se čas, místo a typ převodu zapíší pomocí odpovídajících tříd a vlastností. Například událost převodu vlastnictví lze modelovat třídou `E8 Acquisition`; role kupujícího, prodávajícího a předmětu převodu odpovídají vlastnostem `P22`, `P23` a `P24`. Detailní zápis je potřeba ověřit proti zvolené verzi CIDOC CRM.

### 5.4 Příklad mezivýstupu extrakce (vlastní JSON, nikoliv oficiální CIDOC CRM)

```json
{
  "document_id": "doc_001",
  "entities": [
    {"local_id": "p1", "type": "Person", "label": "Matěj Kovář"},
    {"local_id": "p2", "type": "Person", "label": "Václav Svoboda"},
    {"local_id": "p3", "type": "Person", "label": "Jan Novák"},
    {"local_id": "place1", "type": "Place", "label": "Brno"},
    {"local_id": "obj1", "type": "PhysicalObject", "label": "dům v Brně", "identity_status": "unresolved"}
  ],
  "events": [
    {
      "local_id": "e1",
      "type": "Acquisition",
      "participants": [
        {"entity": "p1", "role": "buyer"},
        {"entity": "p2", "role": "seller"},
        {"entity": "p3", "role": "witness"}
      ],
      "object": "obj1",
      "place": "place1",
      "time": {"original": "Roku 1521", "year": 1521, "precision": "year"},
      "price": {"amount": 150, "currency_text": "zlatých"},
      "evidence": {
        "document_id": "doc_001",
        "text": "Roku 1521 koupil Matěj Kovář od Václava Svobody dům v Brně za 150 zlatých. Při uzavření smlouvy byl přítomen Jan Novák jako svědek."
      }
    }
  ],
  "candidate_claims": [
    {
      "text": "Matěj Kovář byl podle kronikáře významným obchodníkem.",
      "kind": "attributed_description",
      "status": "requires_review"
    },
    {
      "text": "V té době město údajně hospodářsky vzkvétalo.",
      "kind": "uncertain_general_claim",
      "status": "requires_review"
    }
  ]
}
```

**Pozor:** Ve výstupu musí být rozlišeno, co je v textu skutečně uvedeno a co z něj model pouze odvozuje. Role „svědek“ je v tomto příkladu uvedena explicitně; existence rodinného vztahu mezi účastníky by už byla nepodloženou spekulací.

---

## 6. Návrh dvou vrstev uložení

```text
Původní dokument / OCR text
         |
         v
LLM + případně pravidla / NER
         |
         v
KANDIDÁTNÍ INFORMACE (JSON; auditovatelný výstup)
         |
         +--> nejisté / neznámé / nepodporované typy
         |          |
         |          v
         |      Revize či pozdější rozšíření ontologie
         |
         v
Normalizace + Entity Resolution + validace
         |
         v
HLAVNÍ ZNALOSTNÍ GRAF (Property Graph / Neo4j)
         |
         +--> Dotazování, analýza, vizualizace, GraphRAG
         +--> Odkazy zpět na konkrétní důkazy a dokumenty
```

### Vrstva A – kandidátní extrakce

- Uchovávat výstupy modelu odděleně od schválené grafové reprezentace (např. JSON/JSONL).
- Zachovat originální formulaci, identifikátor dokumentu, lokalizaci důkazu, verzi extrakčního schématu a modelu.
- Ponechat nejistá a neklasifikovaná tvrzení označená `requires_review` nebo `unsupported_type`.
- Rozlišit chybu extrakce, nedostatečné schéma a chybějící důkaz.

### Vrstva B – hlavní KG

- Ukládat normalizované entity a typované vztahy/události v definovaném rozsahu.
- Pro každé historické tvrzení umožnit dohledat podklad: konkrétní dokument a textový úsek.
- Udržovat stabilní interní identifikátory (nepoužívat samotné jméno jako primární klíč).
- Zaznamenat, zda byla identita osoby ověřena, navržena nebo zůstává nerozlišená.
- Oddělit doložená tvrzení od odvozených hypotéz a konfliktních tvrzení.

Není nutné vytvářet nový uzel pro **každou zmínku**: zmínky lze modelovat úsporněji a propojit s kanonickou entitou. Pokud však záleží na přesných pozicích v textu, revizi anotací a auditu, je vhodné mít vlastní záznam zmínky nebo tvrzení.

---

## 7. Pravidla pro rozhodnutí, zda informaci strukturovat a uložit

Každý kandidát by měl projít alespoň následujícími kontrolami:

1. **Relevance:** Pomáhá alespoň některé cílové otázce nebo realistickému použití grafu? Pokud ne, zachovat nanejvýš v kandidátní vrstvě.
2. **Doložitelnost:** Je tvrzení explicitní, nebo jde o odvození? Je k dispozici dohledatelný úsek dokumentu?
3. **Identita:** Je jasné, které konkrétní osoby, objekty či události tvrzení popisuje? Pokud ne, nevytvářet neověřené globální propojení.
4. **Sémantika:** Lze informaci namapovat na podporovaný typ vztahu nebo události? Pokud ne, nepřidávat bez kontroly libovolný nový typ hrany.
5. **Kontext:** Byl zachován čas, negace, modalita („údajně“), nejistota, citace či role mluvčího?
6. **Duplicity a konflikty:** Nejde o opakování téhož tvrzení z překrývajících se chunků? Neexistují různá tvrzení, která se nemají přepsat jednou hodnotou?
7. **Užitečnost struktury:** Potřebuje informace samostatný uzel, nebo stačí vlastnost události/relace?

### Navržené stavy kandidátů

| Stav | Význam | Akce |
|---|---|---|
| `accepted` | Odpovídá schématu a splňuje kontrolní kritéria. | Přidat do hlavního grafu spolu s proveniencí. |
| `requires_review` | Nejasná identita, význam, kontext nebo opora. | Uchovat kandidát a předat k validaci. |
| `unsupported_type` | Informace je rozpoznaná, ale není pro ni zvolený model. | Uchovat pro revizi a případné rozšíření schématu. |
| `rejected` | Neprokázané, chybné či nevyhovující tvrzení. | Neimportovat; ponechat auditní stopu dle potřeby. |

Validace schématu (např. Pydantic) zaručuje **správný formát**, ne pravdivost tvrzení. Ani výstup modelu se zdánlivě vysokou „confidence“ nemusí být spolehlivý, pokud pravděpodobnosti nebyly kalibrovány.

---

## 8. Technologická návaznost

Předběžně uvažovaná architektura:

| Vrstva | Možná technologie | Úloha |
|---|---|---|
| Předzpracování | Python, OCR/HTR dle vstupních dat | Text, chunking, zachování pozic a ID dokumentů. |
| Extrakce | LLM + volitelně NER/pravidla | Entity, kandidátní vztahy, události, důkazy. |
| Mezisoubor | JSON/JSONL + Pydantic/JSON Schema | Reprodukovatelný a validovatelný extrakční výstup. |
| Normalizace | Python, slovníky, případně LLM | Identity, názvy, typy, čas, jednotky, deduplikace. |
| Ontologické mapování | **Vybraná podmnožina CIDOC CRM** | Konzistentní význam entit, rolí a událostí. |
| Graf | **Property Graph** | Uzly, typované vztahy a vlastnosti. |
| Databáze | **Neo4j + Cypher** | Ukládání, dotazování, procházení vazeb. |
| Interoperabilita | Případně RDF/JSON-LD | Volitelný budoucí export, ne povinný vstup LLM. |

**CIDOC CRM je ontologie, Property Graph je datový model, JSON je formát mezivýstupu a Neo4j je databázový systém.** Jejich kombinace je možná, ale mapování na CIDOC CRM musí být explicitní a zdokumentované. Prototyp „inspirovaný CIDOC CRM“ nemusí automaticky splňovat všechny sémantické požadavky této ontologie.

---

## 9. Jak zjistit, jestli extrahujeme příliš málo, nebo příliš mnoho?

V praktické části lze porovnat několik experimentálních konfigurací nad stejnými dokumenty:

| Varianta | Extrakce | Graf |
|---|---|---|
| **A – úzká** | Jen osoby, místa, jednoduché předem vybrané vztahy. | Malý, snadno ověřitelný graf. |
| **B – událostní jádro** | Entity + vybrané historické události, role, čas a provenance. | Podrobnější událostně orientovaný graf. |
| **C – hybridní široká** | Jako B + další kandidátní tvrzení mimo pevné schéma. | Hlavní graf jako B, širší auditovatelná kandidátní vrstva. |

### Co měřit

- **Pokrytí:** Kolik relevantních faktů z ručně anotovaného vzorku bylo extrahováno? (Recall.)
- **Správnost:** Kolik extrahovaných faktů je správných? (Precision, případně F1.)
- **Správnost identit:** Jak často systém správně slučuje a neslučuje entity?
- **Kvalita provenance:** Je u tvrzení správně dohledatelný původní text?
- **Dostatečnost pro dotazy:** Na kolik competency questions lze odpovědět správně a úplně?
- **Strukturální cena:** Počet uzlů/hran/tvrzení, počet nevyřešených kandidátů, náročnost revize.
- **Výpočetní cena:** Tokeny a volání LLM, cena zpracování dokumentu, případně čas dotazování.
- **Robustnost:** Dopad OCR/HTR chyb a dobových variant jmen.

Je vhodné vyhodnocovat zvlášť **extrakci správných informací** a **dostupnost těchto informací ve výsledném grafu**. Jestliže informace chybí už v extrakci, není to stejná chyba jako v případě, kdy byla extrahována, ale při mapování nebyla uložena.

### Návrh experimentu

1. Vybrat menší reprezentativní sadu dokumentů s různými typy historických faktů.
2. Definovat cílové otázky a ručně anotovat entity, události, vztahy a jejich zdroje.
3. Spustit stejný model na variantách A, B a C za srovnatelných podmínek.
4. Porovnat správnost, pokrytí, náklady a schopnost odpovědět na připravené otázky.
5. Z chyb zjistit, zda problém způsobila extrakce, identifikace entit, omezení schématu nebo uložení do grafu.

---

## 10. Otevřené otázky pro konzultaci a další práci

- **Jaké konkrétní typy historických dokumentů budou ve vyhodnocení?** Matriky, majetkové knihy, kroniky a úřední listiny mají rozdílnou strukturu faktů.
- **Jak širokou ontologii chceme podporovat v první verzi?** Jen událostní jádro, nebo i složitější právní a majetkové vztahy?
- **Mají být všechny extrahované informace dostupné pro hledání, nebo jen validovaný podgraf?**
- **Jak pracovat s nejistými a rozpornými tvrzeními?** Oddělit jednotlivá tvrzení podle zdroje, ne je bez odůvodnění slévat do jediného faktu.
- **Kdy vytvořit samostatnou událost nebo tvrzení?** Stanovit konvence pro vlastnosti, hrany a uzly.
- **Jaké náklady a míru chyb považujeme za přijatelné?** Rozhodnutí opřít o měření, ne jen o velikost grafu.
- **Jak znovu zpracovat staré dokumenty po změně schématu?** Uchovávat původní text, identifikátory, kandidátní výstupy i verze modelu a promptu.

---

## 11. Předběžné rozhodnutí pro první prototyp

1. **Neukládat automaticky každou větu jako uzel nebo vztah.**
2. **Definovat základní repertoár entit a událostí podle konkrétních dotazů.**
3. **Zachovat širší extrakční výstup odděleně od hlavního grafu**, zejména nepodporované a nejisté kandidáty.
4. **Modelovat vícestranné historické děje jako události** s účastníky, rolemi, časem a místem.
5. **U každého významného tvrzení uchovávat provenance**, ideálně odkaz na dokument a úsek transkribovaného textu.
6. **Sjednocování identit řešit explicitně**; nejasné případy nespojovat bez důkazu.
7. **Vědomě ponechat některé informace jen v původním textu nebo kandidátní vrstvě** a vyhodnotit, jak to ovlivňuje pozdější otázky.
8. **Experimentálně porovnat rozsahy extrakce**, nejen jednotlivé LLM nebo databázové technologie.

### Výzkumná otázka

> **Jaký rozsah extrakce a granularita reprezentace historických faktů poskytují nejlepší kompromis mezi úplností, správností, náklady na konstrukci a použitelností výsledného znalostního grafu?**

### Hlavní závěr

Úkolem není převést celý dokument beze zbytku na graf, ale vytvořit **dostatečně bohatou, správnou, rozšiřitelnou a dohledatelnou strukturu znalostí** pro zvolené výzkumné a aplikační scénáře. Rozsah grafu je proto vhodné navrhovat podle konkrétních otázek, a jeho přínosy i omezení následně ověřit na reálných historických dokumentech.
