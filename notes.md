3.1 Potenciální výhody

    Propojení informací napříč dokumenty: různé zmínky mohou odkazovat na jednu osobu nebo místo.
    Explicitní vztahy: lze vyjádřit, kdo s kým souvisí a jak.
    Dotazy přes více hran: přímé i nepřímé vazby mezi osobami, objekty a událostmi.
    Flexibilita schématu: některé grafové modely přirozeněji zachycují různorodé vztahy.
    Provenance a kvalifikátory: při správném modelování lze evidovat zdroj, čas a nejistotu tvrzení.
    Sémantická interoperabilita: zejména RDF může používat standardizované ontologie a externí identifikátory.
    Odvozování a kontrola: některé vztahy lze odvodit nebo kontrolovat podle pravidel.
    Vizualizace souvislostí: užitečná pro průzkum a interpretaci znalostí.

3.2 Potenciální nevýhody

    Složitější návrh modelu a identifikátorů.
    Nutnost řešit entity resolution, jinak vznikají izolované a duplicitní uzly.
    Riziko propagace chyb extrakce do mnoha vztahů.
    Náročnější reprezentace neúplných, nejistých či konfliktních tvrzení.
    Nová infrastruktura, indexování, údržba a integrace s pipeline.
    Možná vyšší složitost než JSON/SQL u jednoduchých výpisů faktů.
    Vizualizace sama o sobě nezaručuje lepší kvalitu výsledků.
    Specializovaná databáze nemusí přinést výkonovou výhodu u každého typu dotazu.

Hlavní otázka: Potřebuje uživatel znalosti propojovat a dotazovat se na souvislosti, nebo stačí extrahovat sadu dat z jednotlivých dokumentů?

A property graph is a type of graph model where relationships not only are connections but also carry a name (type) and some properties. A property graph excels at showing connections among data scattered across diverse Data Architectures and data schemas. They provide a richer view on how data can be modeled over many different databases as well as how different kinds of metadata relate. Property graphs also show data dependencies not seen in a relational database schema or through other tools. 
https://www.dataversity.net/data-concepts/what-is-a-property-graph/

Selecting the Right Method for Your Use Case

No single method is universally optimal. The decision depends on several practical factors:

    Data consistency and volume — rule-based methods perform well on high-volume, predictable data; ML-based methods hold up better across varied text

    Available labeled data — machine learning approaches require annotated training examples, which may not exist for specialized domains

    Supervision budget — LLM-based methods reduce the need for labeled data but introduce inference costs and output variability

    Accuracy requirements — rule-based systems produce the most deterministic output; LLM-based systems offer more flexibility but may require post-processing validation

For teams working with complex PDFs, spreadsheets, and semi-structured documents before extraction even begins, LlamaParse can help convert messy source material into cleaner structured outputs that are easier to pass into downstream entity and relation extraction steps.

For relation-heavy use cases, a property graph index can provide a more flexible representation of nodes, edges, and metadata than a minimal triple store. And when extraction becomes a multi-step system rather than a single model call, examples of building knowledge graph agents with workflows show how parsing, extraction, validation, and graph updates can be orchestrated together.
 https://www.llamaindex.ai/glossary/knowledge-graph-extraction


 reseni pri neuplne trojici 

1. Řešení v Property Graph (Neo4j apod.)

V Property Graphu je řešení velmi intuitivní. Pokud víte jen to, že se Pavel narodil, vytvoříte uzel pro Pavla a buď použijete jeho interní vlastnosti, nebo vytvoříte uzel pro událost.

Varianta A: Událost jako uzel (Nejlepší praxe pro Knowledge Graphy)

Pokud chcete k narození později přidávat další fakta (místo, datum, porodní asistentku), uděláte z Narození samostatný uzel.
• Uzly: (p:Clovek {jmeno: "Pavel"}), (u:Udalost {typ: "Narozeni"})
• Hrana: (p)-[:BYL_PREDMETEM]->(u)
Jakmile zjistíte další fakta, jednoduše je přidáte jako vlastnosti k uzlu události nebo k němu připojíte další uzly (např. (u)-[:V_MISTE]->(l:Mesto {jmeno: "Praha"})).

Varianta B: Pouhá vlastnost (Pokud detaily nepotřebujete)

Pokud vám stačí vědět, že se to stalo, uzel Pavel může mít prostě příznak: (p:Clovek {jmeno: "Pavel", narozen: true}).


Zajimava je ontologie CIDOC CRM mezinárodní standard pro popis a propojování informací o historii a kulturním dědictví.
Je to postavene na eventech, event centric model, ne  uplne ale z velke casti aspon 
https://cidoc-crm.org/html/cidoc_crm_v7.3.2.html?utm_source=chatgpt.com#E1
E21	Person	Osoba
E67	Birth	Událost narození
E53	Place	Místo
E52	Time-Span	Časový interval
P98	brought into life	Událost narození přivedla osobu na svět
P7	took place at	Událost se odehrála na určitém místě
P4	has time-span	Událost má časové vymezení


mozne reseni do budoucna vlastni ontologie ktera bude vychazet z CIDOC CRM, zapsane jako property graph