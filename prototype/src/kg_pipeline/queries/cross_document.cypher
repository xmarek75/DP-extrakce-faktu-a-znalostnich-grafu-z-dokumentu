// SAME_ENTITY_AS je vlastní, ručně revidovaný symetrický vztah.
MATCH (left:KGNode {import_id: $import_id})-[link:SAME_ENTITY_AS]-(right:KGNode)
WHERE left.id < right.id
RETURN left.document_id AS document_a, left.label AS label_a,
       right.document_id AS document_b, right.label AS label_b,
       link.reason AS reason, link.reviewed_by AS reviewed_by,
       link.evidence_ids AS evidence_ids
ORDER BY label_a;
