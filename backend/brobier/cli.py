import click
import uvicorn

from brobier.core.security import generate_encryption_key


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option('--host', default='0.0.0.0', show_default=True, help='Host to bind to.')
@click.option('--port', default=8000, show_default=True, help='Port to bind to.')
@click.option('--reload', is_flag=True, default=False, help='Enable auto-reload (dev only).')
def serve(host: str, port: int, reload: bool) -> None:
    """Start the Brobier FastAPI server."""
    uvicorn.run('brobier.main:app', host=host, port=port, reload=reload)


@cli.command()
def generate_key() -> None:
    """Generate a Fernet encryption key and append it to .env as BEER_ENCRYPTION_KEY."""
    key = generate_encryption_key()
    click.echo(f'Key written to .env: {key}')
