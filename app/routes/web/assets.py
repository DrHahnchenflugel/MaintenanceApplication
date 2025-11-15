from . import bp

@bp.get("/assets", strict_slashes=False, endpoint="assets_list")
def assets_list():
    # TODO: implement real listing later
    return "Assets list placeholder"