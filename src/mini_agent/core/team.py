"""Team de agentes especializados para MiniAgentG4"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from agno.agent import Agent as AgnoAgent
from agno.team.team import Team

from .config import AgentConfig


def _get_model(provider: str, model_id: str):
    """Get model based on provider."""
    if provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(id=model_id)
    elif provider == "ollama":
        from agno.models.ollama import Ollama
        return Ollama(id=model_id)
    elif provider == "openai":
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_id)
    else:  # lmstudio
        from agno.models.lmstudio import LMStudio
        return LMStudio(id=model_id)


class MiniTeam:
    """Team de agentes especializados para tareas complejas."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.members: List[AgnoAgent] = []
        self.team: Optional[Team] = None
        self._setup_members()

    def _setup_members(self):
        """Configura los agentes miembros del team."""

        # Agente de Investigación
        researcher = AgnoAgent(
            name="Researcher",
            role="Investigar y buscar información",
            model=_get_model(self.config.model_provider, self.config.model_id),
            instructions="""Eres un investigador especializado. Tu trabajo es:
1. Buscar información relevante sobre el tema
2. Analizar múltiples fuentes
3. Presentar los hallazgos de forma clara

Usa las herramientas de búsqueda web para encontrar información actualizada.""",
            markdown=True,
        )

        # Agente de Escritura
        writer = AgnoAgent(
            name="Writer",
            role="Escribir y crear contenido",
            model=_get_model(self.config.model_provider, self.config.model_id),
            instructions="""Eres un escritor especializado. Tu trabajo es:
1. Crear contenido escrito de alta calidad
2. Adaptar el estilo según el tipo de texto
3. Seguir las guías de escritura creativa, blog, o técnicas según corresponda

Tienes acceso a skills de escritura creativa y blog-writer.""",
            markdown=True,
        )

        # Agente de Análisis
        analyst = AgnoAgent(
            name="Analyst",
            role="Analizar datos e información",
            model=_get_model(self.config.model_provider, self.config.model_id),
            instructions="""Eres un analista especializado. Tu trabajo es:
1. Analizar información y datos
2. Identificar patrones y tendencias
3. Proporcionar insights basados en evidencia

Sé crítico y objetivo en tu análisis.""",
            markdown=True,
        )

        # Agente de Revisión
        reviewer = AgnoAgent(
            name="Reviewer",
            role="Revisar y validar contenido",
            model=_get_model(self.config.model_provider, self.config.model_id),
            instructions="""Eres un revisor especializado. Tu trabajo es:
1. Revisar contenido y validar calidad
2. Verificar hechos y datos
3. Sugerir mejoras y correcciones

Sé constructivo y detallado en tus comentarios.""",
            markdown=True,
        )

        self.members = [researcher, writer, analyst, reviewer]

        # Crear el team
        self.team = Team(
            name="MiniTeam",
            members=self.members,
            instructions="""Eres el líder de un equipo de agentes especializados.

## Tu Rol
Coordinas las tareas entre los miembros del equipo y produces resultados finales.

## Miembros del Equipo
- **Researcher**: Investiga y busca información
- **Writer**: Crea contenido escrito
- **Analyst**: Analiza datos e información
- **Reviewer**: Revisa y valida contenido

## Proceso
1. Analiza la solicitud del usuario
2. Determina qué miembros necesitan participar
3. Delega tareas según sus especialidades
4. Sintetiza los resultados en una respuesta coherente

## Reglas
- Delegar solo a los miembros necesarios para la tarea
- Para tareas simples, usar un solo agente
- Para tareas complejas, coordinar múltiples miembros
- Mantener la respuesta final cohesiva

Si la tarea es simple (pregunta directa, tarea única), responde directamente.""",
            model=_get_model(self.config.model_provider, self.config.model_id),
            respond_directly=True,  # Responde directamente para tareas simples
            markdown=True,
        )

    def run(self, message: str, use_team: bool = False):
        """Ejecuta la tarea, opcionalmente usando el team."""
        if use_team and self.team:
            return self.team.print_response(message, stream=True)
        else:
            # Fallback: usar solo el writer para respuestas directas
            return self.members[1].print_response(message, stream=True)

    def run_team(self, message: str):
        """Fuerza el uso del team para tareas complejas."""
        return self.run(message, use_team=True)


def create_team(config: Optional[AgentConfig] = None) -> MiniTeam:
    """Factory function para crear un MiniTeam."""
    return MiniTeam(config=config)