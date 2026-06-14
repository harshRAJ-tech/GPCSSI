"""
Graph Synchronization Service.

WHY: Maps relational entities from PostgreSQL into a rich property graph in Neo4j.
This dual-database approach gives us ACID compliance for evidence (Postgres)
and hyper-fast correlation/traversal for fraud clusters (Neo4j).
"""
import logging
from neo4j import Session
from app.models.entity import Entity
from app.models.enums import EntityType

logger = logging.getLogger(__name__)

def sync_entities_for_case(session: Session, case_id: int, entities_with_mentions: list[tuple[Entity, int]], evidence_id: int | None = None):
    """
    Synchronizes a batch of extracted entities into Neo4j.
    
    Creates or updates the Case (Complaint) node, the Entity nodes, 
    and the MENTIONS relationship between them.
    """
    if not entities_with_mentions:
        return
        
    try:
        # 1. Ensure the Case node exists
        session.run(
            "MERGE (c:Complaint {id: $case_id})",
            case_id=case_id
        )
        
        # 2. Merge entities and relationships
        # We process each one. A better optimization is UNWIND, but for MVP this is clear.
        for entity, mentions in entities_with_mentions:
            # We map our enum type to a specific node label for fast traversal
            label = str(entity.entity_type.value).upper() # e.g. 'UPI', 'PHONE'
            
            # Using apoc.create.node or f-strings for dynamic labels since cypher 
            # doesn't allow parameters for Labels.
            cypher = f"""
            MERGE (e:{label} {{normalized_value: $norm_val}})
            ON CREATE SET e.id = $entity_id, e.type = $entity_type, e.raw_value = $raw_val
            WITH e
            MATCH (c:Complaint {{id: $case_id}})
            MERGE (c)-[r:MENTIONS]->(e)
            SET r.mention_count = $mentions
            """
            
            # If there's an evidence ID, we store it on the edge to track provenance
            if evidence_id:
                cypher += " SET r.evidence_id = $evidence_id"
            
            session.run(
                cypher,
                norm_val=entity.normalized_value,
                entity_id=entity.id,
                entity_type=entity.entity_type.value,
                raw_val=entity.raw_value,
                case_id=case_id,
                mentions=mentions,
                evidence_id=evidence_id
            )
            
    except Exception as e:
        logger.error("Failed to sync entities to Neo4j for case %d: %s", case_id, e)


def remove_evidence_links(session: Session, evidence_id: int):
    """
    When OCR text is manually corrected, old entities are deleted from Postgres.
    We must also remove the edges in Neo4j that originated from this specific evidence file.
    """
    try:
        session.run(
            "MATCH ()-[r:MENTIONS {evidence_id: $evidence_id}]->() DELETE r",
            evidence_id=evidence_id
        )
        # Optional: Clean up orphaned nodes (Entities with no MENTIONS)
        session.run(
            "MATCH (e) WHERE not((e)<-[:MENTIONS]-()) AND not(e:Complaint) DELETE e"
        )
    except Exception as e:
        logger.error("Failed to remove Neo4j links for evidence %d: %s", evidence_id, e)
