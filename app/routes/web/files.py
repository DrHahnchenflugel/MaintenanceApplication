from . import web_bp

@web_bp.get("/files", strict_slashes=False, endpoint="files")
def files():
    # TODO: implement real listing later
    return "Files placeholder"