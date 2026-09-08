# agente-formacion

Repo plantilla con la estructura base sobre la que se construyen agentes: validación, tests, logging estructurado y base de datos. Reutilizable en cualquier proyecto nuevo.

## Requisitos

Python 3.12, uv, Docker, make

## Puesta en marcha

```bash
cp .env.example .env
make install 
make up
make check
```

## Comandos

| Comando | Qué hace |
|---|---|
| `make check` | Formatea, pasa el linter, comprueba tipos y ejecuta los tests |
| `make up` / `make down` | Levanta y para el contenedor de Postgres |
| `make db` | Abre una consola psql en la base de datos |
| `make test-cov` | Ejecuta los tests mostrando qué líneas no cubre ninguno |

## Decisiones

- **uv**: es el gestor de paquetes y entornos
- **mypy strict**:activado desde el primer día porque en un proyecto vacío no cuesta nada, y con el proyecto ya crecido sería inviable.
- **Pydantic**: valida los datos en ejecución. Mypy comprueba el código antes de correr, pero no puede saber qué llega de fuera; Pydantic para lo que no encaja en la frontera del sistema.
- **.env fuera de Git**: queda fuera porque es el archivo que lleva las credenciales y no debe subirse al repositorio. Por eso existe `.env.example`, que documenta qué variables hacen falta sin revelar sus valores.