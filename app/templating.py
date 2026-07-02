from pathlib import Path

from fastapi import Request, status
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.models import BookStatus


APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

STATUS_LABELS: dict[str, str] = {
    BookStatus.want_to_read.value: "Хочу прочитать",
    BookStatus.reading.value: "Читаю",
    BookStatus.read.value: "Прочитано",
    BookStatus.abandoned.value: "Брошено",
}
templates.env.globals["STATUS_LABELS"] = STATUS_LABELS


def render(
    request: Request,
    name: str,
    context: dict | None = None,
    status_code: int = 200,
) -> Response:
    return templates.TemplateResponse(
        request, name, context or {}, status_code=status_code
    )


def not_found(request: Request) -> Response:
    return render(request, "not_found.html", {}, status.HTTP_404_NOT_FOUND)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
