"""
Neo4j Database Driver Manager.

WHY: Maintains a single connection pool to the Neo4j graph database.
This driver is injected into the FastAPI routes similar to the SQLAlchemy Session.
"""
from neo4j import GraphDatabase, Driver
from typing import AsyncGenerator, Generator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton driver instance
try:
    _driver: Driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )
    # Validate connection on startup
    _driver.verify_connectivity()
    logger.info("Successfully connected to Neo4j Graph Database.")
except Exception as e:
    # We log but do not immediately crash the app if Neo4j is down on boot, 
    # as some environments might not have it yet during migration.
    logger.error("Failed to connect to Neo4j: %s", e)
    _driver = None


def get_graph_db() -> Generator:
    """Dependency that yields a Neo4j session."""
    if _driver is None:
        raise Exception("Neo4j Driver is not initialized.")
    with _driver.session() as session:
        yield session


def close_driver():
    """Close the connection pool on application shutdown."""
    if _driver is not None:
        _driver.close()
