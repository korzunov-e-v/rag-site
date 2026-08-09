from backend.app.api.v1.router import v1_router


@v1_router.get("/")
def read_root():
    return {"Hello": "World"}


@v1_router.get("/healthz")
def healthz():
    return {"status": "ok"}
