"""
Neo4j-backed graph store modeling relationships between applicants, family
members, households, and shared documents/addresses. This lets the system
detect patterns a purely tabular DB misses, e.g.:
  - The same bank account or address linked across multiple "unrelated"
    applications (possible duplicate/fraudulent claims).
  - Family/household structures spanning multiple applicants, so family
    size and combined household income can be assessed holistically
    rather than per-individual.

Falls back to a no-op in-memory adjacency list if Neo4j isn't reachable.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)


class GraphStore:
    def __init__(self):
        self._driver = None
        self._local_edges = []
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
            self._driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", settings.NEO4J_URI)
        except Exception as e:  # noqa: BLE001
            logger.warning("Neo4j unavailable (%s) - using in-memory graph fallback.", e)
            self._driver = None

    def link_applicant_to_household(self, applicant_id: str, address: str, family_size: int):
        if self._driver is not None:
            with self._driver.session() as session:
                session.run(
                    "MERGE (a:Applicant {id: $aid}) "
                    "MERGE (h:Household {address: $address}) "
                    "SET h.family_size = $family_size "
                    "MERGE (a)-[:MEMBER_OF]->(h)",
                    aid=applicant_id, address=address, family_size=family_size,
                )
        else:
            self._local_edges.append(("MEMBER_OF", applicant_id, address, family_size))

    def find_shared_address_applicants(self, address: str, exclude_id: str):
        if self._driver is not None:
            with self._driver.session() as session:
                result = session.run(
                    "MATCH (a:Applicant)-[:MEMBER_OF]->(h:Household {address: $address}) "
                    "WHERE a.id <> $exclude_id RETURN a.id AS id",
                    address=address, exclude_id=exclude_id,
                )
                return [r["id"] for r in result]
        return [aid for (_, aid, addr, _) in self._local_edges if addr == address and aid != exclude_id]


graph_store = GraphStore()
