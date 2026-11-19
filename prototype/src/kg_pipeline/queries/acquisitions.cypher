// Přijatá zdrojová tvrzení; přibližný rok není přesná datace.
MATCH (event:KGNode:Acquisition {import_id: $import_id})
MATCH (event)-[:TRANSFERRED_TITLE_OF]->(object:PhysicalThing)
MATCH (event)-[:SUPPORTED_BY]->(evidence:Evidence)-[:FOUND_IN]->(doc:Document)
OPTIONAL MATCH (event)-[:TRANSFERRED_TITLE_TO]->(buyer:Person)
OPTIONAL MATCH (event)-[:TRANSFERRED_TITLE_FROM]->(seller:Person)
OPTIONAL MATCH (event)-[:HAS_TIME_SPAN]->(time:TimeSpan)
RETURN doc.local_id AS document, buyer.label AS buyer, seller.label AS seller,
       object.label AS object, time.year AS year, time.precision AS precision,
       time.approximate AS approximate, time.original_text AS original_time,
       evidence.text AS evidence
ORDER BY document, evidence;
