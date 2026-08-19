"""Uvicorn-factory die secrets pas tijdens serverstart leest."""

from fastapi import FastAPI

from broker_ai.server.app import create_app


def create_runtime_app() -> FastAPI:
    return create_app()
