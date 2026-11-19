MATCH (event:KGNode:Acquisition {import_id: $import_id})
MATCH (event)-[:SUPPORTED_BY]->(evidence:Evidence)-[:FOUND_IN]->(doc:Document)
RETURN event.local_id AS event, doc.local_id AS document,
       doc.source_file AS source_file, doc.synthetic AS synthetic,
       evidence.text AS evidence, evidence.start AS start, evidence.end AS end,
       substring(doc.text, evidence.start, evidence.end - evidence.start) AS verified_text
ORDER BY document, event;
