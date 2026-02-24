from pistat.config import load_config
from pistat.db import init_db
from pistat.server import create_app

config = load_config("config.toml")
init_db(config.database.path)
app = create_app(config)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host=config.server.host, port=config.server.port)
