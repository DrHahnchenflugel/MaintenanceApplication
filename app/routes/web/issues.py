from . import bp

@bp.get("/issues", strict_slashes=False, endpoint="issues_list")
def issues_list():
    # TODO: implement real listing later
    return "Issues list placeholder"