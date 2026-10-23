# Architecture

Browser / React + Vite
        |
        | HTTP JSON
        v
FastAPI backend
        |
        +-- current resource state
        +-- alerts + risk score
        +-- Hindsight similarity
        +-- forecast service
        +-- CascadeFlow
        +-- What-if simulation
        +-- decision recording
        |
        v
Synthetic data (MVP)

Later:
FastAPI -> PostgreSQL
