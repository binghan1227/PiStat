import tomllib
from dataclasses import dataclass


@dataclass
class CollectionConfig:
    interval_seconds: int
    retention_days: int


@dataclass
class ServerConfig:
    host: str
    port: int


@dataclass
class MetricsConfig:
    network_interface: str
    disk_path: str


@dataclass
class DatabaseConfig:
    path: str


@dataclass
class Config:
    collection: CollectionConfig
    server: ServerConfig
    metrics: MetricsConfig
    database: DatabaseConfig


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    return Config(
        collection=CollectionConfig(**data["collection"]),
        server=ServerConfig(**data["server"]),
        metrics=MetricsConfig(**data["metrics"]),
        database=DatabaseConfig(**data["database"]),
    )
