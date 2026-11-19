RETURN COUNT {
  MATCH (n:KGNode {import_id: $import_id})
} AS nodes,
COUNT {
  MATCH (:KGNode {import_id: $import_id})-[r]->(:KGNode {import_id: $import_id})
} AS edges;
