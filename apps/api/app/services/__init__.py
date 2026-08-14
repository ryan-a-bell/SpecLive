"""Application services: all business logic lives here.

Services depend on the repository port and the event bus, never on FastAPI or a
concrete provider SDK. UI/API layers orchestrate services but hold no logic.
"""
